from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_web_role
from ..models import Order, Product, RefundRequest
from ..services.order_service import transition_order
from ..services.refund_service import merchant_confirm_receipt, merchant_decide
from .shop import _ctx


router = APIRouter(prefix="/merchant")

ORDER_STATUS_OPTIONS = (
    ("pending_payment", "待付款"),
    ("paid", "已付款"),
    ("shipped", "已发货"),
    ("completed", "已完成"),
    ("canceled", "已取消"),
)
ORDER_STATUSES = {value for value, _ in ORDER_STATUS_OPTIONS}

REFUND_STATUS_OPTIONS = (
    ("pending_merchant", "待商家处理"),
    ("waiting_return", "等待用户寄回"),
    ("returned", "用户已寄回"),
    ("merchant_rejected", "商家已拒绝"),
    ("admin_intervening", "平台介入中"),
    ("refunded", "退款已完成"),
    ("admin_rejected", "平台已拒绝"),
    ("closed_return_timeout", "退回超时关闭"),
)
REFUND_STATUSES = {value for value, _ in REFUND_STATUS_OPTIONS}


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"merchant"})
    counts = {
        "products": db.scalar(select(func.count(Product.id)).where(Product.merchant_id == user.id)) or 0,
        "paid_orders": db.scalar(select(func.count(Order.id)).where(Order.merchant_id == user.id, Order.status == "paid")) or 0,
        "pending_refunds": db.scalar(select(func.count(RefundRequest.id)).where(RefundRequest.merchant_id == user.id, RefundRequest.status.in_(["pending_merchant", "returned"]))) or 0,
    }
    recent_orders = list(db.scalars(select(Order).where(Order.merchant_id == user.id).order_by(Order.created_at.desc()).limit(8)))
    return request.app.state.templates.TemplateResponse(
        request, "merchant/dashboard.html", _ctx(request, db, counts=counts, recent_orders=recent_orders)
    )


@router.get("/products")
def products(request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"merchant"})
    rows = list(db.scalars(select(Product).where(Product.merchant_id == user.id).order_by(Product.created_at.desc())))
    return request.app.state.templates.TemplateResponse(
        request, "merchant/products.html", _ctx(request, db, products=rows)
    )


@router.post("/products/create")
def product_create(
    request: Request,
    name: str = Form(...),
    category: str = Form("综合"),
    description: str = Form(""),
    price: float = Form(...),
    stock: int = Form(...),
    image_url: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_web_role(request, db, {"merchant"})
    if price <= 0 or stock < 0:
        raise HTTPException(400, "价格或库存不合法")
    db.add(Product(merchant_id=user.id, name=name, category=category, description=description, price_cents=int(round(price * 100)), stock=stock, image_url=image_url))
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
        raise HTTPException(404, "商品不存在")
    if price <= 0 or stock < 0:
        raise HTTPException(400, "价格或库存不合法")
    product.price_cents = int(round(price * 100))
    product.stock = stock
    product.is_active = is_active
    db.commit()
    return RedirectResponse("/merchant/products", status_code=303)


@router.get("/orders")
def orders(request: Request, status: str = "", q: str = "", db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"merchant"})
    status = status.strip()
    q = q.strip()
    if status and status not in ORDER_STATUSES:
        raise HTTPException(400, "订单状态不合法")
    stmt = select(Order).where(Order.merchant_id == user.id)
    if status:
        stmt = stmt.where(Order.status == status)
    if q:
        stmt = stmt.where(Order.order_no.contains(q))
    rows = list(db.scalars(stmt.order_by(Order.created_at.desc())))
    return request.app.state.templates.TemplateResponse(
        request,
        "merchant/orders.html",
        _ctx(request, db, orders=rows, status=status, q=q, status_options=ORDER_STATUS_OPTIONS),
    )


@router.post("/orders/{order_id}/ship")
def ship(order_id: int, request: Request, tracking_no: str = Form(...), db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"merchant"})
    order = db.get(Order, order_id)
    if not order or order.merchant_id != user.id:
        raise HTTPException(404, "订单不存在")
    transition_order(db, order, user, "shipped", "商家发货", tracking_no)
    return RedirectResponse("/merchant/orders", status_code=303)


@router.get("/refunds")
def refunds(request: Request, status: str = "", q: str = "", db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"merchant"})
    status = status.strip()
    q = q.strip()
    if status and status not in REFUND_STATUSES:
        raise HTTPException(400, "售后状态不合法")
    stmt = select(RefundRequest).where(RefundRequest.merchant_id == user.id)
    if status:
        stmt = stmt.where(RefundRequest.status == status)
    if q:
        stmt = stmt.where(RefundRequest.refund_no.contains(q))
    rows = list(db.scalars(stmt.order_by(RefundRequest.created_at.desc())))
    return request.app.state.templates.TemplateResponse(
        request,
        "merchant/refunds.html",
        _ctx(request, db, refunds=rows, status=status, q=q, status_options=REFUND_STATUS_OPTIONS),
    )


@router.post("/refunds/{refund_id}/decision")
def refund_decision(
    refund_id: int,
    request: Request,
    decision: str = Form(...),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_web_role(request, db, {"merchant"})
    refund = db.get(RefundRequest, refund_id)
    if not refund:
        raise HTTPException(404, "售后单不存在")
    if decision not in {"approve", "reject"}:
        raise HTTPException(400, "售后决策不合法")
    comment = comment.strip()
    if decision == "reject" and not comment:
        raise HTTPException(400, "拒绝售后必须填写审核意见")
    merchant_decide(db, user, refund, decision == "approve", comment)
    return RedirectResponse("/merchant/refunds", status_code=303)


@router.post("/refunds/{refund_id}/confirm-receipt")
def confirm_receipt(refund_id: int, request: Request, comment: str = Form(""), db: Session = Depends(get_db)):
    user = require_web_role(request, db, {"merchant"})
    refund = db.get(RefundRequest, refund_id)
    if not refund:
        raise HTTPException(404, "售后单不存在")
    merchant_confirm_receipt(db, user, refund, comment.strip())
    return RedirectResponse("/merchant/refunds", status_code=303)
