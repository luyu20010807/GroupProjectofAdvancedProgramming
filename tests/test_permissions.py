import pytest
from fastapi import HTTPException

from app.services.order_service import add_to_cart, checkout, transition_order
from app.services.refund_service import admin_resolve, apply_refund, escalate_to_admin, merchant_decide


def test_other_merchant_cannot_ship(db, actors):
    add_to_cart(db, actors["user"], actors["p1"].id, 1)
    order = checkout(db, actors["user"], "张三", "13800000000", "测试地址")[0]
    transition_order(db, order, actors["user"], "paid", "支付")
    with pytest.raises(HTTPException) as exc:
        transition_order(db, order, actors["merchant2"], "shipped", "越权发货", "BAD")
    assert exc.value.status_code == 403


def test_tech_admin_cannot_arbitrate(db, actors):
    add_to_cart(db, actors["user"], actors["p1"].id, 1)
    order = checkout(db, actors["user"], "张三", "13800000000", "测试地址")[0]
    transition_order(db, order, actors["user"], "paid", "支付")
    refund = apply_refund(db, actors["user"], order, "refund_only", "未发货", "")
    merchant_decide(db, actors["merchant1"], refund, False, "拒绝")
    escalate_to_admin(db, actors["user"], refund, "申请平台处理")
    with pytest.raises(HTTPException) as exc:
        admin_resolve(db, actors["tech"], refund, True, "技术管理员越权")
    assert exc.value.status_code == 403
