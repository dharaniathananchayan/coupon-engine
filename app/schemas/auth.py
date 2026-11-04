from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Staff email address")
    password: str = Field(..., min_length=1, description="Staff account password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff_email: str
