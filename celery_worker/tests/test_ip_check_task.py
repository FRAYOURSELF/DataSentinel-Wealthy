from worker.tasks import ip_check


class FakeQueryResult:
    def __init__(self, rows):
        self.result_rows = rows


class FakeClickhouseClient:
    def __init__(self, rows):
        self.rows = rows
        self.update_calls = []
        self.audit_inserts = []

    def query(self, _sql, parameters):
        _ = parameters
        return FakeQueryResult(self.rows)

    def command(self, sql, parameters):
        self.update_calls.append({"sql": sql, "parameters": parameters})

    def insert(self, table, data, column_names):
        self.audit_inserts.append({"table": table, "data": data, "column_names": column_names})


def test_check_login_ip_marks_first_login(monkeypatch):
    fake_client = FakeClickhouseClient(rows=[])
    monkeypatch.setattr(ip_check, "_clickhouse_client", lambda: fake_client)

    status = ip_check.check_login_ip.run(
        event_id="00000000-0000-0000-0000-000000000001",
        user_id=1,
        username="alice",
        ip_address="1.1.1.1",
    )

    assert status == "first_login"
    assert fake_client.update_calls
    assert fake_client.audit_inserts
