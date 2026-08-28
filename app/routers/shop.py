from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import current_web_user, require_web_role
from ..models import CartItem, Notification, Product
from ..services.order_service import add_to_cart, checkout


router = APIRouter()


def _ctx(request: Request, db: Session, **kwargs):
    user = current_web_user(request, db)
    unread = 0
    cart_count = 0
    if user:
        unread = db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id, Notification.is_read.is_(False)
            )
        ) or 0
        if user.role == "user":
            cart_count = db.scalar(
                select(func.coalesce(func.sum(CartItem.quantity), 0)).where(CartItem.user_id == user.id)
            ) or 0
    return {"user": user, "unread": unread, "cart_count": cart_count, **kwargs}


@router.get("/")
def home(request: Request, q: str = "", category: str = "", db: Session = Depends(get_db)):
    stmt = select(Product).where(Product.is_active.is_(True))
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Product.name.like(like), Product.description.like(like)))
    if category.strip():
        stmt = stmt.where(Product.category == category.strip())
    products = list(db.scalars(stmt.order_by(Product.created_at.desc())))
    categories = list(db.scalars(select(Product.category).distinct().order_by(Product.category)))
    return request.app.state.templates.TemplateResponse(
        request,
        "user/home.html",
        _ctx(request, db, products=products, categories=categories, q=q, category=category),
    )


@router.get("/products/{product_id}")
def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(404, "商品不存在")
    return request.app.state.templates.TemplateResponse(
        request, "user/product_detail.html", _ctx(request, db, product=product)
    )


@router.post("/cart/add")
def cart_add(
    request: Request,
    product_id: int = Form(...),
    quantity: int = Form(1),
    db: Session = Depends(get_db),
):
    user = require_web_role(request, db, {"user"})
    add_to_cart(db, user, product_id, quantity)
    return RedirectResponse("/cart?message=已加入购物车", status_code=303)


@router.get("/cart")
def cart_page(request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    items = list(db.scalars(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.id)))
    total = sum(item.product.price_cents * item.quantity for item in items)
    return request.app.state.templates.TemplateResponse(
        request,
        "user/cart.html",
        _ctx(request, db, items=items, total=total, message=request.query_params.get("message", "")),
    )


@router.post("/cart/{item_id}/update")
def cart_update(item_id: int, request: Request, quantity: int = Form(...), db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    item = db.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "购物车条目不存在")
    if quantity <= 0:
        db.delete(item)
    else:
        if quantity > item.product.stock:
            raise HTTPException(400, "库存不足")
        item.quantity = min(quantity, 99)
    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/{item_id}/delete")
def cart_delete(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"user"})
    item = db.get(CartItem, item_id)
    if item and item.user_id == user.id:
        db.delete(item)
        db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/checkout")
def checkout_route(
    request: Request,
    receiver_name: str = Form(...),
    receiver_phone: str = Form(...),
    receiver_address: str = Form(...),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_web_role(request, db, {"user"})
    orders = checkout(db, user, receiver_name, receiver_phone, receiver_address, remark)
    order_ids = ",".join(str(o.id) for o in orders)
    return RedirectResponse(f"/orders?created={order_ids}", status_code=303)


@router.get("/notifications")
def notifications_page(request: Request, db: Session = Depends(get_db)):
    user = current_web_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    rows = list(
        db.scalars(
            select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())
        )
    )
    for row in rows:
        row.is_read = True
    db.commit()
    return request.app.state.templates.TemplateResponse(
        request, "shared/notifications.html", _ctx(request, db, notifications=rows)
    )
