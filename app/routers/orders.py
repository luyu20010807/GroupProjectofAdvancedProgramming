from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_web_role
from ..models import Order, RefundRequest
from ..services.order_service import transition_order
from ..services.refund_service import apply_refund, escalate_to_admin, remind_merchant, submit_return
from .shop import _ctx


router = APIRouter(prefix="/orders")


@router.get("")
def order_list(request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    orders = list(db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())))
    return request.app.state.templates.TemplateResponse(
        request,
        "user/orders.html",
        _ctx(request, db, orders=orders, created=request.query_params.get("created", "")),
    )


@router.get("/{order_id}")
def order_detail(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    order = db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "订单不存在")
    refunds = list(db.scalars(select(RefundRequest).where(RefundRequest.order_id == order.id).order_by(RefundRequest.created_at.desc())))
    return request.app.state.templates.TemplateResponse(
        request, "user/order_detail.html", _ctx(request, db, order=order, refunds=refunds)
    )


@router.post("/{order_id}/pay")
def pay(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    order = db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "订单不存在")
    transition_order(db, order, user, "paid", "模拟支付成功")
    return RedirectResponse(f"/orders/{order_id}", status_code=303)


@router.post("/{order_id}/cancel")
def cancel(order_id: int, request: Request, reason: str = Form("用户取消"), db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    order = db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "订单不存在")
    transition_order(db, order, user, "canceled", reason)
    return RedirectResponse(f"/orders/{order_id}", status_code=303)


@router.post("/{order_id}/confirm")
def confirm(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    order = db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "订单不存在")
    transition_order(db, order, user, "completed", "用户确认收货")
    return RedirectResponse(f"/orders/{order_id}", status_code=303)


@router.post("/{order_id}/refund")
def refund_apply_route(
    order_id: int,
    request: Request,
    refund_type: str = Form(...),
    reason: str = Form(...),
    description: str = Form(""),
    evidence: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_web_role(request, db, {"user"})
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    apply_refund(db, user, order, refund_type, reason, description, evidence)
    return RedirectResponse(f"/orders/{order_id}", status_code=303)


@router.post("/refunds/{refund_id}/remind")
def refund_remind(refund_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    refund = db.get(RefundRequest, refund_id)
    if not refund:
        raise HTTPException(404, "售后单不存在")
    remind_merchant(db, user, refund)
    return RedirectResponse(f"/orders/{refund.order_id}", status_code=303)


@router.post("/refunds/{refund_id}/return")
def refund_return(refund_id: int, request: Request, tracking_no: str = Form(...), db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    refund = db.get(RefundRequest, refund_id)
    if not refund:
        raise HTTPException(404, "售后单不存在")
    submit_return(db, user, refund, tracking_no)
    return RedirectResponse(f"/orders/{refund.order_id}", status_code=303)


@router.post("/refunds/{refund_id}/escalate")
def refund_escalate(refund_id: int, request: Request, reason: str = Form(...), db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    refund = db.get(RefundRequest, refund_id)
    if not refund:
        raise HTTPException(404, "售后单不存在")
    escalate_to_admin(db, user, refund, reason)
    return RedirectResponse(f"/orders/{refund.order_id}", status_code=303)
