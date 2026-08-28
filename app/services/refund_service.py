from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Order, RefundRequest, User, utcnow
from .audit import write_audit
from .notification import notify


ACTIVE_REFUND_STATUSES = {
    "pending_merchant",
    "waiting_return",
    "returned",
    "merchant_rejected",
    "admin_intervening",
}


def _refund_no() -> str:
    return "R" + utcnow().strftime("%Y%m%d%H%M%S") + uuid4().hex[:5].upper()


def apply_refund(
    db: Session,
    user: User,
    order: Order,
    refund_type: str,
    reason: str,
    description: str = "",
    evidence: str = "",
) -> RefundRequest:
    if order.user_id != user.id:
        raise HTTPException(403, "只能为自己的订单申请售后")
    if order.status not in {"paid", "shipped", "completed"}:
        raise HTTPException(400, "当前订单状态不支持售后")
    if refund_type == "refund_only" and order.status == "shipped":
        raise HTTPException(400, "商品已发货，不能仅退款，请选择退货退款")
    existing = db.scalar(
        select(RefundRequest).where(
            RefundRequest.order_id == order.id,
            RefundRequest.status.in_(ACTIVE_REFUND_STATUSES),
        )
    )
    if existing:
        raise HTTPException(400, "该订单已有进行中的售后申请")

    refund = RefundRequest(
        refund_no=_refund_no(),
        order_id=order.id,
        user_id=user.id,
        merchant_id=order.merchant_id,
        refund_type=refund_type,
        reason=reason,
        description=description,
        amount_cents=order.total_cents,
        user_evidence=evidence,
        merchant_deadline=utcnow() + timedelta(hours=settings.merchant_review_hours),
    )
    db.add(refund)
    db.flush()
    write_audit(db, user, "apply_refund", "refund", refund.id, "", refund.status, reason)
    notify(db, order.merchant_id, "收到售后申请", f"售后单 {refund.refund_no} 请在截止时间前处理")
    notify(db, user.id, "售后申请已提交", f"售后单 {refund.refund_no} 正等待商家审核")
    db.commit()
    db.refresh(refund)
    return refund


def remind_merchant(db: Session, user: User, refund: RefundRequest) -> None:
    if refund.user_id != user.id or refund.status != "pending_merchant":
        raise HTTPException(400, "当前售后单不能催办")
    now = utcnow()
    if refund.last_reminded_at and now - refund.last_reminded_at < timedelta(hours=6):
        raise HTTPException(400, "每 6 小时最多催办一次")
    refund.reminder_count += 1
    refund.last_reminded_at = now
    notify(db, refund.merchant_id, "用户催办售后", f"售后单 {refund.refund_no} 已被用户催办")
    write_audit(db, user, "remind_refund", "refund", refund.id, refund.status, refund.status, f"第 {refund.reminder_count} 次催办")
    db.commit()


def merchant_decide(db: Session, merchant: User, refund: RefundRequest, approve: bool, comment: str) -> None:
    if refund.merchant_id != merchant.id:
        raise HTTPException(403, "只能处理本店售后")
    if refund.status != "pending_merchant":
        raise HTTPException(400, "售后单已被处理或已升级平台")
    before = refund.status
    refund.merchant_comment = comment
    if approve:
        if refund.refund_type == "refund_only":
            refund.status = "refunded"
            refund.resolved_at = utcnow()
        else:
            refund.status = "waiting_return"
            refund.return_deadline = utcnow() + timedelta(days=settings.return_deadline_days)
    else:
        refund.status = "merchant_rejected"
    write_audit(db, merchant, "merchant_review_refund", "refund", refund.id, before, refund.status, comment)
    notify(db, refund.user_id, "商家已处理售后", f"售后单 {refund.refund_no} 当前状态：{refund.status}")
    db.commit()


def submit_return(db: Session, user: User, refund: RefundRequest, tracking_no: str) -> None:
    if refund.user_id != user.id or refund.status != "waiting_return":
        raise HTTPException(400, "当前售后单不能填写退货物流")
    if not tracking_no.strip():
        raise HTTPException(400, "请填写退货物流单号")
    before = refund.status
    refund.return_tracking_no = tracking_no.strip()
    refund.returned_at = utcnow()
    refund.status = "returned"
    write_audit(db, user, "submit_return", "refund", refund.id, before, refund.status, tracking_no)
    notify(db, refund.merchant_id, "用户已寄回商品", f"售后单 {refund.refund_no}，物流单号：{tracking_no}")
    db.commit()


def merchant_confirm_receipt(db: Session, merchant: User, refund: RefundRequest, comment: str = "") -> None:
    if refund.merchant_id != merchant.id or refund.status != "returned":
        raise HTTPException(400, "当前售后单不能确认收货")
    before = refund.status
    refund.status = "refunded"
    refund.merchant_comment = comment or refund.merchant_comment
    refund.resolved_at = utcnow()
    write_audit(db, merchant, "confirm_return_receipt", "refund", refund.id, before, refund.status, comment)
    notify(db, refund.user_id, "退款已完成", f"售后单 {refund.refund_no} 已模拟原路退款")
    db.commit()


def escalate_to_admin(db: Session, user: User, refund: RefundRequest, reason: str) -> None:
    if refund.user_id != user.id:
        raise HTTPException(403, "只能升级自己的售后单")
    now = utcnow()
    overdue = refund.status == "pending_merchant" and refund.merchant_deadline and now > refund.merchant_deadline
    if refund.status != "merchant_rejected" and not overdue:
        raise HTTPException(400, "仅商家拒绝或处理超时后可申请平台介入")
    before = refund.status
    refund.status = "admin_intervening"
    refund.admin_comment = f"用户申请介入：{reason}"
    refund.escalated_at = now
    write_audit(db, user, "escalate_refund", "refund", refund.id, before, refund.status, reason)
    notify(db, refund.merchant_id, "平台已介入售后", f"售后单 {refund.refund_no} 已进入平台仲裁")
    db.commit()


def admin_resolve(db: Session, admin: User, refund: RefundRequest, approve: bool, comment: str) -> None:
    if admin.role not in {"super_admin", "customer_service", "business_admin"}:
        raise HTTPException(403, "该管理员角色没有售后仲裁权限")
    if refund.status not in {"admin_intervening", "merchant_rejected", "pending_merchant"}:
        raise HTTPException(400, "当前售后单不能由平台裁决")
    before = refund.status
    refund.status = "admin_approved" if approve else "admin_rejected"
    if approve:
        refund.status = "refunded"
    refund.admin_comment = comment
    refund.resolved_at = utcnow()
    write_audit(db, admin, "admin_resolve_refund", "refund", refund.id, before, refund.status, comment)
    notify(db, refund.user_id, "平台仲裁完成", f"售后单 {refund.refund_no} 裁决结果：{refund.status}")
    notify(db, refund.merchant_id, "平台仲裁完成", f"售后单 {refund.refund_no} 裁决结果：{refund.status}")
    db.commit()


def process_timeouts(db: Session) -> dict[str, int]:
    now = utcnow()
    stats = {"merchant_overdue": 0, "return_overdue": 0, "auto_refunded": 0}

    pending = list(db.scalars(select(RefundRequest).where(RefundRequest.status == "pending_merchant")))
    for refund in pending:
        if refund.merchant_deadline and refund.merchant_deadline < now:
            before = refund.status
            refund.status = "admin_intervening"
            refund.escalated_at = now
            refund.admin_comment = "商家审核超时，系统自动升级平台介入"
            write_audit(db, None, "auto_escalate_refund", "refund", refund.id, before, refund.status, refund.admin_comment)
            notify(db, refund.user_id, "售后已自动升级", f"售后单 {refund.refund_no} 因商家超时已转平台处理")
            stats["merchant_overdue"] += 1

    waiting = list(db.scalars(select(RefundRequest).where(RefundRequest.status == "waiting_return")))
    for refund in waiting:
        if refund.return_deadline and refund.return_deadline < now:
            before = refund.status
            refund.status = "closed_return_timeout"
            refund.resolved_at = now
            write_audit(db, None, "close_return_timeout", "refund", refund.id, before, refund.status, "用户未在期限内寄回")
            notify(db, refund.user_id, "售后已关闭", f"售后单 {refund.refund_no} 因超期未寄回而关闭")
            stats["return_overdue"] += 1

    returned = list(db.scalars(select(RefundRequest).where(RefundRequest.status == "returned")))
    for refund in returned:
        if refund.returned_at and refund.returned_at + timedelta(hours=settings.receipt_confirm_hours) < now:
            before = refund.status
            refund.status = "refunded"
            refund.resolved_at = now
            refund.admin_comment = "商家收货确认超时，系统自动退款"
            write_audit(db, None, "auto_refund_returned", "refund", refund.id, before, refund.status, refund.admin_comment)
            notify(db, refund.user_id, "系统自动退款", f"售后单 {refund.refund_no} 已自动退款")
            stats["auto_refunded"] += 1

    db.commit()
    return stats
