from app.services.order_service import add_to_cart, checkout, transition_order
from app.services.refund_service import (
    admin_resolve,
    apply_refund,
    escalate_to_admin,
    merchant_confirm_receipt,
    merchant_decide,
    submit_return,
)


def make_paid_order(db, actors, shipped=False):
    add_to_cart(db, actors["user"], actors["p1"].id, 1)
    order = checkout(db, actors["user"], "张三", "13800000000", "测试地址")[0]
    transition_order(db, order, actors["user"], "paid", "支付")
    if shipped:
        transition_order(db, order, actors["merchant1"], "shipped", "发货", "SF20001")
    return order


def test_refund_only_approved(db, actors):
    order = make_paid_order(db, actors)
    refund = apply_refund(db, actors["user"], order, "refund_only", "商家未发货", "不再需要")
    merchant_decide(db, actors["merchant1"], refund, True, "同意仅退款")
    db.refresh(refund)
    assert refund.status == "refunded"
    assert refund.resolved_at is not None


def test_return_refund_complete(db, actors):
    order = make_paid_order(db, actors, shipped=True)
    refund = apply_refund(db, actors["user"], order, "return_refund", "质量问题", "无法正常使用")
    merchant_decide(db, actors["merchant1"], refund, True, "同意退货")
    assert refund.status == "waiting_return"
    submit_return(db, actors["user"], refund, "YT888888")
    assert refund.status == "returned"
    merchant_confirm_receipt(db, actors["merchant1"], refund, "验收完成")
    assert refund.status == "refunded"


def test_reject_escalate_and_admin_approve(db, actors):
    order = make_paid_order(db, actors, shipped=True)
    refund = apply_refund(db, actors["user"], order, "return_refund", "质量问题", "屏幕闪烁")
    merchant_decide(db, actors["merchant1"], refund, False, "未发现问题")
    escalate_to_admin(db, actors["user"], refund, "附有故障视频")
    assert refund.status == "admin_intervening"
    admin_resolve(db, actors["service"], refund, True, "证据充分，支持用户")
    assert refund.status == "refunded"
