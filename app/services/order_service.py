from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CartItem, Order, OrderItem, Product, User, utcnow
from .audit import write_audit
from .notification import notify


ORDER_TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"paid", "canceled"},
    "paid": {"shipped", "canceled"},
    "shipped": {"completed"},
    "completed": set(),
    "canceled": set(),
}


def _order_no() -> str:
    return utcnow().strftime("%Y%m%d%H%M%S") + uuid4().hex[:6].upper()


def add_to_cart(db: Session, user: User, product_id: int, quantity: int) -> CartItem:
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(404, "商品不存在或已下架")
    if product.stock < quantity:
        raise HTTPException(400, "库存不足")
    item = db.scalar(
        select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id)
    )
    if item:
        if item.quantity + quantity > product.stock:
            raise HTTPException(400, "加入后的数量超过库存")
        item.quantity += quantity
    else:
        item = CartItem(user_id=user.id, product_id=product_id, quantity=quantity)
        db.add(item)
    db.commit()
    db.refresh(item)
    return item


def checkout(
    db: Session,
    user: User,
    receiver_name: str,
    receiver_phone: str,
    receiver_address: str,
    remark: str = "",
) -> list[Order]:
    items = list(
        db.scalars(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.id))
    )
    if not items:
        raise HTTPException(400, "购物车为空")

    grouped: dict[int, list[CartItem]] = defaultdict(list)
    for item in items:
        product = item.product
        if not product.is_active:
            raise HTTPException(400, f"商品“{product.name}”已下架")
        if item.quantity > product.stock:
            raise HTTPException(400, f"商品“{product.name}”库存不足")
        grouped[product.merchant_id].append(item)

    orders: list[Order] = []
    for merchant_id, merchant_items in grouped.items():
        total = sum(i.product.price_cents * i.quantity for i in merchant_items)
        order = Order(
            order_no=_order_no(),
            user_id=user.id,
            merchant_id=merchant_id,
            total_cents=total,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            receiver_address=receiver_address,
            remark=remark,
        )
        db.add(order)
        db.flush()
        for cart_item in merchant_items:
            product = cart_item.product
            product.stock -= cart_item.quantity
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=cart_item.quantity,
                    unit_price_cents=product.price_cents,
                    subtotal_cents=product.price_cents * cart_item.quantity,
                )
            )
            db.delete(cart_item)
        write_audit(db, user, "create_order", "order", order.id, "", order.status, "购物车按商家自动拆单")
        notify(db, merchant_id, "收到新订单", f"订单 {order.order_no} 等待用户付款")
        orders.append(order)
    db.commit()
    return orders


def transition_order(
    db: Session,
    order: Order,
    actor: User,
    new_status: str,
    detail: str = "",
    tracking_no: str = "",
) -> Order:
    before = order.status
    if new_status not in ORDER_TRANSITIONS.get(before, set()):
        raise HTTPException(400, f"订单不能从 {before} 变更为 {new_status}")

    if new_status == "paid":
        if actor.id != order.user_id:
            raise HTTPException(403, "只能由下单用户支付")
        order.paid_at = utcnow()
    elif new_status == "shipped":
        if actor.id != order.merchant_id:
            raise HTTPException(403, "只能由所属商家发货")
        if not tracking_no.strip():
            raise HTTPException(400, "发货必须填写物流单号")
        order.tracking_no = tracking_no.strip()
        order.shipped_at = utcnow()
    elif new_status == "completed":
        if actor.id != order.user_id:
            raise HTTPException(403, "只能由下单用户确认收货")
        order.completed_at = utcnow()
    elif new_status == "canceled":
        if actor.id not in {order.user_id, order.merchant_id}:
            raise HTTPException(403, "无权取消订单")
        if before == "paid" and actor.id == order.merchant_id:
            detail = detail or "商家取消，系统模拟原路退款"
        order.cancel_reason = detail
        order.canceled_at = utcnow()
        for item in order.items:
            item.product.stock += item.quantity

    order.status = new_status
    write_audit(db, actor, "transition_order", "order", order.id, before, new_status, detail)
    notify(db, order.user_id, "订单状态更新", f"订单 {order.order_no}：{before} → {new_status}")
    notify(db, order.merchant_id, "订单状态更新", f"订单 {order.order_no}：{before} → {new_status}")
    db.commit()
    db.refresh(order)
    return order
