from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_api_user, require_api_roles
from ..models import ApiToken, CartItem, Order, Product, RefundRequest, User, utcnow
from ..schemas import CartAddRequest, CheckoutRequest, LoginRequest, RefundApplyRequest
from ..security import generate_api_token, verify_password
from ..services.order_service import add_to_cart, checkout, transition_order
from ..services.refund_service import apply_refund


router = APIRouter(prefix="/api/v1", tags=["mini-program-api"])


def money(cents: int) -> float:
    return round(cents / 100, 2)


@router.post("/login")
def api_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = ApiToken(token=generate_api_token(), user_id=user.id, expires_at=utcnow() + timedelta(days=7))
    db.add(token)
    db.commit()
    return {"token": token.token, "user": {"id": user.id, "name": user.display_name, "role": user.role}}


@router.get("/products")
def api_products(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.created_at.desc())))
    return [{"id": p.id, "name": p.name, "category": p.category, "description": p.description, "price": money(p.price_cents), "stock": p.stock, "image_url": p.image_url, "merchant": p.merchant.display_name} for p in rows]


@router.get("/products/{product_id}")
def api_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p or not p.is_active:
        raise HTTPException(404, "商品不存在")
    return {"id": p.id, "name": p.name, "category": p.category, "description": p.description, "price": money(p.price_cents), "stock": p.stock, "image_url": p.image_url, "merchant": p.merchant.display_name}


@router.get("/cart")
def api_cart(user: User = Depends(require_api_roles("user")), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(CartItem).where(CartItem.user_id == user.id)))
    return [{"id": x.id, "quantity": x.quantity, "product": {"id": x.product.id, "name": x.product.name, "price": money(x.product.price_cents), "stock": x.product.stock}} for x in rows]


@router.post("/cart")
def api_cart_add(payload: CartAddRequest, user: User = Depends(require_api_roles("user")), db: Session = Depends(get_db)):
    item = add_to_cart(db, user, payload.product_id, payload.quantity)
    return {"id": item.id, "quantity": item.quantity}


@router.delete("/cart/{item_id}")
def api_cart_delete(item_id: int, user: User = Depends(require_api_roles("user")), db: Session = Depends(get_db)):
    item = db.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "购物车条目不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/checkout")
def api_checkout(payload: CheckoutRequest, user: User = Depends(require_api_roles("user")), db: Session = Depends(get_db)):
    orders = checkout(db, user, payload.receiver_name, payload.receiver_phone, payload.receiver_address, payload.remark)
    return [{"id": o.id, "order_no": o.order_no, "status": o.status, "total": money(o.total_cents)} for o in orders]


@router.get("/orders")
def api_orders(user: User = Depends(require_api_roles("user")), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())))
    return [{"id": o.id, "order_no": o.order_no, "status": o.status, "total": money(o.total_cents), "merchant": o.merchant.display_name, "created_at": o.created_at.isoformat()} for o in rows]


@router.get("/orders/{order_id}")
def api_order(order_id: int, user: User = Depends(require_api_roles("user")), db: Session = Depends(get_db)):
    o = db.get(Order, order_id)
    if not o or o.user_id != user.id:
        raise HTTPException(404, "订单不存在")
    return {"id": o.id, "order_no": o.order_no, "status": o.status, "total": money(o.total_cents), "merchant": o.merchant.display_name, "tracking_no": o.tracking_no, "items": [{"name": i.product_name, "quantity": i.quantity, "unit_price": money(i.unit_price_cents)} for i in o.items], "refunds": [{"id": r.id, "refund_no": r.refund_no, "status": r.status, "reason": r.reason} for r in o.refunds]}


@router.post("/orders/{order_id}/pay")
def api_pay(order_id: int, user: User = Depends(require_api_roles("user")), db: Session = Depends(get_db)):
    o = db.get(Order, order_id)
    if not o or o.user_id != user.id:
        raise HTTPException(404, "订单不存在")
    transition_order(db, o, user, "paid", "小程序模拟支付")
    return {"status": o.status}


@router.post("/orders/{order_id}/confirm")
def api_confirm(order_id: int, user: User = Depends(require_api_roles("user")), db: Session = Depends(get_db)):
    o = db.get(Order, order_id)
    if not o or o.user_id != user.id:
        raise HTTPException(404, "订单不存在")
    transition_order(db, o, user, "completed", "小程序确认收货")
    return {"status": o.status}


@router.post("/orders/{order_id}/refund")
def api_refund(order_id: int, payload: RefundApplyRequest, user: User = Depends(require_api_roles("user")), db: Session = Depends(get_db)):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "订单不存在")
    r = apply_refund(db, user, o, payload.refund_type, payload.reason, payload.description)
    return {"id": r.id, "refund_no": r.refund_no, "status": r.status}


@router.get("/me")
def api_me(user: User = Depends(get_api_user)):
    return {"id": user.id, "name": user.display_name, "role": user.role}
