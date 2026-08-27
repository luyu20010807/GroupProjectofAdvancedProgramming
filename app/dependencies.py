from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import ApiToken, User, utcnow


bearer = HTTPBearer(auto_error=False)
ADMIN_ROLES = {"super_admin", "customer_service", "business_admin", "tech_admin"}


def current_web_user(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        request.session.clear()
        return None
    return user


def require_web_role(request: Request, db: Session, roles: set[str]) -> User:
    user = current_web_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    if user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权执行该操作")
    return user


def get_api_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="缺少访问令牌")
    row = db.scalar(select(ApiToken).where(ApiToken.token == credentials.credentials))
    if not row or (row.expires_at and row.expires_at < utcnow()):
        raise HTTPException(status_code=401, detail="访问令牌无效或已过期")
    if not row.user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用")
    return row.user


def require_api_roles(*roles: str):
    def dependency(user: User = Depends(get_api_user)) -> User:
        if user.role not in set(roles):
            raise HTTPException(status_code=403, detail="无权执行该操作")
        return user

    return dependency
