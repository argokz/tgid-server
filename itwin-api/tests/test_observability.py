"""Метрики Prometheus: доступ по токену, шаблон маршрута вместо пути, очередь расчётов."""
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import observability


def _client(monkeypatch, queue_length=3):
    monkeypatch.setattr(observability, "_celery_queue_length", lambda: queue_length)
    app = FastAPI()

    @app.get("/api/node/{node_id}")
    async def node(node_id: int):
        if node_id == 0:
            raise HTTPException(status_code=404, detail="нет")
        return {"id": node_id}

    app.add_middleware(observability.MetricsMiddleware)
    app.include_router(observability.router)
    return TestClient(app)


def _scrape(client, token="t0ken"):
    return client.get("/metrics", headers={"Authorization": f"Bearer {token}"})


def _sample(text, name, **labels):
    want = ",".join(f'{k}="{v}"' for k, v in labels.items())
    prefix = f"{name}{{{want}}} " if want else f"{name} "
    for line in text.splitlines():
        if line.startswith(prefix):
            return float(line.rsplit(" ", 1)[1])
    return None


def test_metrics_hidden_without_token_env(monkeypatch):
    monkeypatch.delenv("METRICS_TOKEN", raising=False)
    assert _scrape(_client(monkeypatch)).status_code == 404


def test_metrics_reject_wrong_token(monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", "t0ken")
    client = _client(monkeypatch)
    assert _scrape(client, "wrong").status_code == 401
    assert client.get("/metrics").status_code == 401


def test_requests_counted_by_route_template(monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", "t0ken")
    client = _client(monkeypatch)
    before = _scrape(client).text
    labels_ok = dict(method="GET", route="/api/node/{node_id}", status="200")
    labels_404 = dict(method="GET", route="/api/node/{node_id}", status="404")
    ok_before = _sample(before, "tgid_http_requests_total", **labels_ok) or 0
    nf_before = _sample(before, "tgid_http_requests_total", **labels_404) or 0

    client.get("/api/node/5")
    client.get("/api/node/6")
    client.get("/api/node/0")
    client.get("/no/such/path")
    text = _scrape(client).text

    assert _sample(text, "tgid_http_requests_total", **labels_ok) == ok_before + 2
    assert _sample(text, "tgid_http_requests_total", **labels_404) == nf_before + 1
    assert "/api/node/5" not in text  # путь с id не попадает в метки
    assert 'route="<unmatched>"' in text
    assert 'route="/metrics"' not in text  # сам опрос не считается


def test_state_metrics(monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", "t0ken")
    monkeypatch.setenv("DB_NAME", "almatygid_copy")
    monkeypatch.delenv("TGID_CITY", raising=False)
    text = _scrape(_client(monkeypatch, queue_length=4)).text
    assert _sample(text, "tgid_info", city="almaty", database="almatygid_copy") == 1
    assert _sample(text, "tgid_celery_queue_up") == 1
    assert _sample(text, "tgid_celery_queue_length") == 4


def test_queue_unavailable_still_serves_metrics(monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", "t0ken")
    client = _client(monkeypatch)

    def broken():
        raise ConnectionError("redis down")

    monkeypatch.setattr(observability, "_celery_queue_length", broken)
    resp = _scrape(client)
    assert resp.status_code == 200
    assert _sample(resp.text, "tgid_celery_queue_up") == 0
    assert _sample(resp.text, "tgid_celery_queue_length") is None
