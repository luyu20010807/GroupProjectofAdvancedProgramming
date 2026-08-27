from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import ADMIN_ROLES, require_web_role
from ..models import AuditLog, Order, Product, RefundRequest, User
from ..services.refund_service import admin_resolve, process_timeouts
from .shop import _ctx


router = APIRouter(prefix="/admin")


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_web_role(request, db, ADMIN_ROLES)
    counts = {
        "users": db.scalar(select(func.count(User.id)).where(User.role == "user")) or 0,
        "merchants": db.scalar(select(func.count(User.id)).where(User.role == "merchant")) or 0,
        "orders": db.scalar(select(func.count(Order.id))) or 0,
        "interventions": db.scalar(select(func.count(RefundRequest.id)).where(RefundRequest.status == "admin_intervening")) or 0,
    }
    recent_logs = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)))
    return request.app.state.templates.TemplateResponse(
        request, "admin/dashboard.html", _ctx(request, db, counts=counts, recent_logs=recent_logs)
    )


@router.get("/refunds")
def refunds(request: Request, status: str = "", db: Session = Depends(get_db)):
    require_web_role(request, db, {"super_admin", "customer_service", "business_admin"})
    stmt = select(RefundRequest)
    if status:
        stmt = stmt.where(RefundRequest.status == status)
    rows = list(db.scalars(stmt.order_by(RefundRequest.created_at.desc())))
    return request.app.state.templates.TemplateResponse(
        request, "admin/refunds.html", _ctx(request, db, refunds=rows, status=status)
    )


@router.post("/refunds/{refund_id}/resolve")
def resolve_refund(
    refund_id: int,
    request: Request,
    decision: str = Form(...),
    comment: str = Form(...),
    db: Session = Depends(get_db),
):
    user = require_web_role(request, db, {"super_admin", "customer_service", "business_admin"})
    refund = db.get(RefundRequest, refund_id)
    if not refund:
        raise HTTPException(404, "售后单不存在")
    admin_resolve(db, user, refund, decision == "approve", comment)
    return RedirectResponse("/admin/refunds", status_code=303)


@router.post("/run-timeouts")
def run_timeouts(request: Request, db: Session = Depends(get_db)):
    require_web_role(request, db, {"super_admin", "customer_service", "business_admin"})
    stats = process_timeouts(db)
    msg = f"商家超时{stats['merchant_overdue']}，退货超时{stats['return_overdue']}，自动退款{stats['auto_refunded']}"
    return RedirectResponse(f"/admin?message={msg}", status_code=303)


@router.get("/users")
def users(request: Request, db: Session = Depends(get_db)):
    require_web_role(request, db, {"super_admin", "business_admin"})
    rows = list(db.scalars(select(User).order_by(User.created_at.desc())))
    return request.app.state.templates.TemplateResponse(
        request, "admin/users.html", _ctx(request, db, users=rows)
    )


@router.post("/users/{user_id}/toggle")
def toggle_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    actor = require_web_role(request, db, {"super_admin", "business_admin"})
    user = db.get(User, user_id)
    if not user or user.id == actor.id:
        raise HTTPException(400, "不能修改该账号")
    user.is_active = not user.is_active
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/audit")
def audit(request: Request, action: str = "", db: Session = Depends(get_db)):
    require_web_role(request, db, {"super_admin", "tech_admin", "business_admin"})
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = list(db.scalars(stmt.order_by(AuditLog.created_at.desc()).limit(300)))
    return request.app.state.templates.TemplateResponse(
        request, "admin/audit.html", _ctx(request, db, logs=rows, action=action)
    )


@router.get("/products")
def products(request: Request, db: Session = Depends(get_db)):
    require_web_role(request, db, {"super_admin", "business_admin"})
    rows = list(db.scalars(select(Product).order_by(Product.created_at.desc())))
    return request.app.state.templates.TemplateResponse(
        request, "admin/products.html", _ctx(request, db, products=rows)
    )
