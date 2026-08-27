from sqlalchemy import func, select

from app.models import AuditLog, CartItem, Order
from app.services.order_service import add_to_cart, checkout, transition_order


def test_cross_merchant_checkout_and_fulfillment(db, actors):
    user = actors["user"]
    add_to_cart(db, user, actors["p1"].id, 2)
    add_to_cart(db, user, actors["p2"].id, 1)

    orders = checkout(db, user, "张三", "13800000000", "测试地址 1 号", "请尽快发货")
    assert len(orders) == 2
    assert {o.merchant_id for o in orders} == {actors["merchant1"].id, actors["merchant2"].id}
    assert db.scalar(select(func.count(CartItem.id))) == 0

    first = next(o for o in orders if o.merchant_id == actors["merchant1"].id)
    transition_order(db, first, user, "paid", "模拟支付")
    transition_order(db, first, actors["merchant1"], "shipped", "已发货", "SF10001")
    transition_order(db, first, user, "completed", "确认收货")

    db.refresh(first)
    assert first.status == "completed"
    assert first.tracking_no == "SF10001"
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.entity_type == "order")) >= 5


def test_web_login_cart_checkout(client, db, actors):
    response = client.post("/login", data={"username": "user", "password": "123456"}, follow_redirects=False)
    assert response.status_code == 303

    response = client.post("/cart/add", data={"product_id": actors["p1"].id, "quantity": 1}, follow_redirects=False)
    assert response.status_code == 303

    response = client.post(
        "/checkout",
        data={
            "receiver_name": "张三",
            "receiver_phone": "13800000000",
            "receiver_address": "某某大学 1 号楼",
            "remark": "集成测试",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/orders?created=")
    assert db.scalar(select(func.count(Order.id))) == 1
