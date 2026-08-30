"""临时验证：商家端订单/售后搜索与状态校验（验证后删除）。"""
from app.services.order_service import add_to_cart, checkout, transition_order
from app.services.refund_service import apply_refund


def _login(client, username):
    resp = client.post("/login", data={"username": username, "password": "123456"}, follow_redirects=False)
    assert resp.status_code in (303, 302), resp.status_code


def _make_order(db, actors, shipped=False):
    add_to_cart(db, actors["user"], actors["p1"].id, 1)
    order = checkout(db, actors["user"], "张三", "13800000000", "测试地址")[0]
    transition_order(db, order, actors["user"], "paid", "支付")
    if shipped:
        transition_order(db, order, actors["merchant1"], "shipped", "发货", "SF20001")
    return order


def test_order_search_by_no(db, actors, client):
    order = _make_order(db, actors)
    _login(client, "merchant1")
    html = client.get("/merchant/orders", params={"q": order.order_no[-6:]}).text
    assert order.order_no in html
    html = client.get("/merchant/orders", params={"q": "不存在的单号"}).text
    assert order.order_no not in html


def test_order_status_options_and_bad_status(db, actors, client):
    _make_order(db, actors)
    _login(client, "merchant1")
    html = client.get("/merchant/orders").text
    assert "待付款" in html and "待商家处理" not in html  # 下拉用订单状态中文标签
    assert client.get("/merchant/orders", params={"status": "hacked"}).status_code == 400


def test_refund_search_and_filter(db, actors, client):
    order = _make_order(db, actors)
    refund = apply_refund(db, actors["user"], order, "refund_only", "商家未发货", "不再需要")
    _login(client, "merchant1")
    html = client.get("/merchant/refunds", params={"q": refund.refund_no[-6:]}).text
    assert refund.refund_no in html
    html = client.get("/merchant/refunds", params={"status": "pending_merchant"}).text
    assert refund.refund_no in html
    html = client.get("/merchant/refunds", params={"status": "refunded"}).text
    assert refund.refund_no not in html
    assert client.get("/merchant/refunds", params={"status": "hacked"}).status_code == 400


def test_refund_decision_validation(db, actors, client):
    order = _make_order(db, actors)
    refund = apply_refund(db, actors["user"], order, "refund_only", "商家未发货", "不再需要")
    _login(client, "merchant1")
    bad = client.post(f"/merchant/refunds/{refund.id}/decision", data={"decision": "maybe", "comment": ""})
    assert bad.status_code == 400
    empty_reject = client.post(f"/merchant/refunds/{refund.id}/decision", data={"decision": "reject", "comment": "  "})
    assert empty_reject.status_code == 400
