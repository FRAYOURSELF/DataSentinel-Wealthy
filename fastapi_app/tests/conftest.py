from collections.abc import Generator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import auth as auth_route
from app.core.security import hash_password
from app.db.sqlite import Base, get_db_session
from app.main import app
from app import main as app_main
from app.models.user import User


class FakeClickhouseClient:
    def __init__(self):
        self.insert_calls = []
        self.command_calls = []

    def insert(self, table, data, column_names):
        self.insert_calls.append({"table": table, "data": data, "column_names": column_names})

    def command(self, sql, parameters=None):
        self.command_calls.append({"sql": sql, "parameters": parameters})

    def query(self, sql, parameters=None):
        _ = sql
        user_id = (parameters or {}).get("user_id")
        if user_id is None:
            return type("Result", (), {"result_rows": []})()

        matching = []
        for call in self.insert_calls:
            if call["table"] != "login_events":
                continue
            row = call["data"][0]
            if int(row[1]) == int(user_id) and int(row[5]) == 200:
                matching.append(row)
        if not matching:
            return type("Result", (), {"result_rows": []})()
        return type("Result", (), {"result_rows": [[matching[-1][3]]]})()


@pytest.fixture
def test_engine(tmp_path):
    db_path = tmp_path / "test_users.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_db(test_engine) -> Generator[Session, None, None]:
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def client(test_db: Session, redis_client):
    fake_clickhouse = FakeClickhouseClient()

    def override_get_db():
        yield test_db

    def override_get_redis():
        return redis_client

    def fake_get_clickhouse_client():
        return fake_clickhouse

    dispatched_tasks = []

    def fake_send_task(task_name, *args, **kwargs):
        dispatched_tasks.append({"task_name": task_name, "args": args, "kwargs": kwargs})

    original_auth_clickhouse = auth_route.get_clickhouse_client
    original_main_clickhouse = app_main.get_clickhouse_client
    original_send_task = auth_route.celery_app.send_task
    original_engine = app_main.engine

    auth_route.get_clickhouse_client = fake_get_clickhouse_client
    app_main.get_clickhouse_client = fake_get_clickhouse_client
    auth_route.celery_app.send_task = fake_send_task
    app_main.engine = test_db.get_bind()
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[auth_route.get_redis_client] = override_get_redis

    user = User(username="alice", password_hash=hash_password("alice_password"))
    test_db.add(user)
    test_db.commit()

    with TestClient(app) as test_client:
        test_client.fake_clickhouse = fake_clickhouse
        test_client.dispatched_tasks = dispatched_tasks
        yield test_client

    auth_route.get_clickhouse_client = original_auth_clickhouse
    app_main.get_clickhouse_client = original_main_clickhouse
    auth_route.celery_app.send_task = original_send_task
    app_main.engine = original_engine
    app.dependency_overrides = {}
