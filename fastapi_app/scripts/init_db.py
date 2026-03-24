from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.sqlite import Base, SessionLocal, engine
from app.models.user import User


def seed_users(session: Session):
    users = [
        ("alice", "alice_password"),
        ("bob", "bob_password"),
        ("charlie", "charlie_password"),
    ]
    for username, password in users:
        exists = session.query(User).filter(User.username == username).first()
        if exists:
            continue
        session.add(User(username=username, password_hash=hash_password(password)))
    session.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()
    print("SQLite initialized with seed users")
