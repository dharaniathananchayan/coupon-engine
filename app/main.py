from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.coupons import router as coupons_router
from app.database import engine, Base, get_db
from app.models.staff import Staff
from app.services.auth_service import decode_access_token

BASE_DIR = Path(__file__).resolve().parent

# Ensure tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ArchintX Coupon Engine",
    description="Full-stack coupon system with server-side validation, atomic concurrency control, and staff management.",
    version="1.0.0",
)

# Mount static files and templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount API Routers
app.include_router(auth_router)
app.include_router(coupons_router)


def get_current_user_email(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    payload = decode_access_token(token)
    if payload and "sub" in payload:
        return payload["sub"]
    return None


@app.get("/", response_class=RedirectResponse)
def index():
    return RedirectResponse(url="/apply")


@app.get("/apply", response_class=HTMLResponse)
def page_apply(request: Request):
    user_email = get_current_user_email(request)
    return templates.TemplateResponse(
        request=request,
        name="apply.html",
        context={
            "active_page": "apply",
            "is_authenticated": user_email is not None,
            "staff_email": user_email,
        },
    )


@app.get("/login", response_class=HTMLResponse)
def page_login(request: Request):
    user_email = get_current_user_email(request)
    if user_email:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "active_page": "login",
            "is_authenticated": False,
        },
    )


@app.get("/dashboard", response_class=HTMLResponse)
def page_dashboard(request: Request, db: Session = Depends(get_db)):
    user_email = get_current_user_email(request)
    if not user_email:
        return RedirectResponse(url="/login")

    staff = db.query(Staff).filter(Staff.email == user_email).first()
    if not staff:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "is_authenticated": True,
            "staff_email": user_email,
        },
    )
