import uuid

from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)

    def authenticate(self, username: str, password: str):
        user = self.user_repo.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def new_event_id() -> str:
        return str(uuid.uuid4())
