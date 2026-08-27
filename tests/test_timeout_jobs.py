from datetime import timedelta

from app.models import RefundRequest, utcnow
from app.services.order_service import add_to_cart, checkout, transition_order
from app.services.refund_service import apply_refund, merchant_decide, process_timeouts, submit_return


def make_paid(db, actors, product_key="p1"):
    add_to_cart(db, actors["user"], actors[product_key].id, 1)
    order = checkout(db, actors["user"], "张三", "13800000000", "测试地址")[0]
    transition_order(db, order, actors["user"], "paid", "支付")
    return order


def test_merchant_review_timeout_auto_escalates(db, actors):
    order = make_paid(db, actors)
    refund = apply_refund(db, actors["user"], order, "refund_only", "未发货", "")
    refund.merchant_deadline = utcnow() - timedelta(minutes=1)
    db.commit()
    stats = process_timeouts(db)
    db.refresh(refund)
    assert stats["merchant_overdue"] == 1
    assert refund.status == "admin_intervening"


def test_return_deadline_timeout_closes_case(db, actors):
    order = make_paid(db, actors)
    refund = apply_refund(db, actors["user"], order, "return_refund", "不想要", "")
    merchant_decide(db, actors["merchant1"], refund, True, "同意")
    refund.return_deadline = utcnow() - timedelta(minutes=1)
    db.commit()
    stats = process_timeouts(db)
    db.refresh(refund)
    assert stats["return_overdue"] == 1
    assert refund.status == "closed_return_timeout"


def test_merchant_receipt_timeout_auto_refunds(db, actors):
    order = make_paid(db, actors)
    refund = apply_refund(db, actors["user"], order, "return_refund", "质量问题", "")
    merchant_decide(db, actors["merchant1"], refund, True, "同意")
    submit_return(db, actors["user"], refund, "SFRET001")
    refund.returned_at = utcnow() - timedelta(hours=80)
    db.commit()
    stats = process_timeouts(db)
    db.refresh(refund)
    assert stats["auto_refunded"] == 1
    assert refund.status == "refunded"
