from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_web_role
from ..models import Order, Product, RefundRequest
from .shop import _ctx


router = APIRouter(prefix="/merchant")


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"merchant"})
    counts = {
        "products": db.scalar(select(func.count(Product.id)).where(Product.merchant_id == user.id)) or 0,
        "paid_orders": db.scalar(
            select(func.count(Order.id)).where(Order.merchant_id == user.id, Order.status == "paid")
        )
        or 0,
        "pending_refunds": db.scalar(
            select(func.count(RefundRequest.id)).where(
                RefundRequest.merchant_id == user.id,
                RefundRequest.status.in_(["pending_merchant", "returned"]),
            )
        )
        or 0,
    }
    recent_orders = list(
        db.scalars(
            select(Order)
            .where(Order.merchant_id == user.id)
            .order_by(Order.created_at.desc())
            .limit(8)
        )
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "merchant/dashboard.html",
        _ctx(request, db, counts=counts, recent_orders=recent_orders),
    )


@router.get("/products")
def products(request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"merchant"})
    rows = list(
        db.scalars(
            select(Product)
            .where(Product.merchant_id == user.id)
            .order_by(Product.created_at.desc())
        )
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "merchant/products.html",
        _ctx(request, db, products=rows),
    )


@router.post("/products/create")
def product_create(
    request: Request,
    name: str = Form(...),
    category: str = Form("??"),
    description: str = Form(""),
    price: float = Form(...),
    stock: int = Form(...),
    image_url: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_web_role(request, db, {"merchant"})
    if price <= 0 or stock < 0:
        raise HTTPException(400, "????????")
    db.add(
        Product(
            merchant_id=user.id,
            name=name,
            category=category,
            description=description,
            price_cents=int(round(price * 100)),
            stock=stock,
            image_url=image_url,
        )
    )
    db.commit()
    return RedirectResponse("/merchant/products", status_code=303)


@router.post("/products/{product_id}/update")
def product_update(
    product_id: int,
    request: Request,
    price: float = Form(...),
    stock: int = Form(...),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
):
    user = require_web_role(request, db, {"merchant"})
    product = db.get(Product, product_id)
    if not product or product.merchant_id != user.id:
        raise HTTPException(404, "?????")
    if price <= 0 or stock < 0:
        raise HTTPException(400, "????????")
    product.price_cents = int(round(price * 100))
    product.stock = stock
    product.is_active = is_active
    db.commit()
    return RedirectResponse("/merchant/products", status_code=303)
