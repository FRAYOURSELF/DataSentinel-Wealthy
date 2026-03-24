from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6, max_length=255)


class LoginResponse(BaseModel):
    success: bool
    message: str
    user_id: int | None = None
    event_id: str | None = None
    access_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    different_device: bool = False