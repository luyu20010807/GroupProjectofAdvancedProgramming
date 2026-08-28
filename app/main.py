from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .database import init_db
from .routers import admin, api, auth, merchant, orders, shop


APP_DIR = Path(__file__).resolve().parent


def money_filter(cents: int | None) -> str:
    return f"¥{(cents or 0) / 100:.2f}"


def datetime_filter(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "-"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site="lax", https_only=False)
    app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

    templates = Jinja2Templates(directory=APP_DIR / "templates")
    templates.env.filters["money"] = money_filter
    templates.env.filters["dt"] = datetime_filter
    app.state.templates = templates

    app.include_router(auth.router)
    app.include_router(shop.router)
    app.include_router(orders.router)
    app.include_router(merchant.router)
    app.include_router(admin.router)
    app.include_router(api.router)

    @app.get("/health")
    def health():
        return {"status": "ok", "app": settings.app_name}

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        return templates.TemplateResponse(
            request,
            "error.html",
            {"status_code": exc.status_code, "message": exc.detail, "user": None, "unread": 0, "cart_count": 0},
            status_code=exc.status_code,
        )

    return app


app = create_app()
