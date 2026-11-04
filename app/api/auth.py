from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.staff import Staff
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    Staff login endpoint.
    Validates credentials and returns JWT token in JSON and HTTP-only cookie.
    """
    email_clean = credentials.email.strip().lower()
    staff = db.query(Staff).filter(Staff.email == email_clean).first()

    if not staff or not verify_password(credentials.password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(data={"sub": staff.email})

    # Set secure cookie for browser sessions
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        staff_email=staff.email,
    )


@router.post("/logout")
def logout(response: Response):
    """Logs out the staff session by removing the cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}
