from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import verify_password


router = APIRouter()


@router.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return request.app.state.templates.TemplateResponse(
        request, "login.html", {"error": request.query_params.get("error", "")}
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.username == username.strip()))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return RedirectResponse("/login?error=用户名或密码错误", status_code=303)
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    if user.role == "merchant":
        target = "/merchant"
    elif user.role in {"super_admin", "customer_service", "business_admin", "tech_admin"}:
        target = "/admin"
    else:
        target = "/"
    return RedirectResponse(target, status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
