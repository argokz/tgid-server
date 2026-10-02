"""Смоук-проверка всех маршрутов API.

Проходит по таблице маршрутов приложения, подставляет реальные ID из БД
и печатает статус каждого эндпоинта. Возвращает ненулевой код, если есть
5xx или неожиданные ошибки.

Запуск:
    python scripts/smoke_all.py [--base http://127.0.0.1:8000]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

# Маршруты, которые не проверяем автоматически:
# мутации (нужен токен и включённые флаги), долгие выгрузки и служебные.
SKIP_PATH_PREFIXES = (
    "/openapi.json", "/docs", "/redoc",
    "/api/export/shp",           # тяжёлый zip всей сети
    "/api/db/object",            # паспорт: отдельная проверка
    "/api/reports/excel",        # ведомости: отдельная проверка (медленно)
)
SKIP_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# Значения для path-параметров, если не удалось получить реальный ID
FALLBACK_PARAMS = {
    # /line/{table} требует линейную таблицу, /node/{table} — точечную;
    # для линейного маршрута подменяется ниже
    "table": "nodes",
    "id": "1",
    "column": "nodename",
    "task_id": "smoke-none",
    "consumer_type": "generalized",
    "equipment_type": "damper",
    "regulator_type": "pressure",
    "catalog_type": "pressure",
    "object_type": "source",
    "form_id": "f11_defect",
    "doc_type": "ut",
}

# Значения для обязательных query-параметров (FastAPI отвечает 422 «Field required», если их
# не передать — это ложный FAIL). Реальные ID (fragment_id, season_id) подставляются из БД.
QUERY_DEFAULTS = {
    "fragment_id": "74",
    "season_id": "1",
    "kind": "unassigned_buildings",
}

# Маршруты, где обязателен «один из» необязательных параметров (FastAPI их не помечает required)
EXTRA_QUERY = {
    "/api/topology/line-ref": "line_id={line_id}",
    "/api/v1/topology/line-ref": "line_id={line_id}",
    "/api/fragments/extent": "fragment_id={fragment_id}",
    "/api/v1/fragments/extent": "fragment_id={fragment_id}",
}

# 503 «зависимость не установлена» — маршрут исправен, на хосте нет опционального пакета
DEPENDENCY_MARKERS = ("is not installed",)


def http_get(url: str, timeout: float = 120.0, max_bytes: int = 4096):
    started = time.monotonic()
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(max_bytes)
            return resp.status, body, time.monotonic() - started
    except urllib.error.HTTPError as e:
        return e.code, e.read(2048), time.monotonic() - started
    except Exception as e:  # network / timeout
        return 0, str(e).encode(), time.monotonic() - started


def discover_ids(base: str) -> dict:
    """Реальные ID из журналов — чтобы карточки проверялись на живых данных."""
    ids = {}
    probes = {
        "defect_id": "/api/defects?page=1&page_size=1",
        "shurf_id": "/api/shurfs?page=1&page_size=1",
        "inspection_id": "/api/inspections?page=1&page_size=1",
        "repair_id": "/api/repairs?page=1&page_size=1",
        "test_id": "/api/pressure-tests?page=1&page_size=1",
        "condition_id": "/api/technical-conditions?page=1&page_size=1",
        "indicator_id": "/api/corrosion-indicators?page=1&page_size=1",
        "load_id": "/api/alseko/loads?page=1&page_size=1",
        "building_id": "/api/alseko/buildings/unassigned?page=1&page_size=1",
        "object_id": "/api/electrical-network/objects?page=1&page_size=1",
        "season_id": "/api/heat-losses/seasons?page=1&page_size=1",
        "source_id": "/api/heat-losses/sources?page=1&page_size=1",
        "consumer_id": "/api/consumer-load-diagnostics/consumers?page=1&page_size=1",
        "pump_id": "/api/pump-equipment/pumps?page=1&page_size=1",
        "standard_pump_id": "/api/pump-equipment/catalog?page=1&page_size=1",
        "armature_id": "/api/network-armatures/items?page=1&page_size=1",
        "standard_id": "/api/network-armatures/catalog?page=1&page_size=1",
        "regulator_id": "/api/network-regulators/items?page=1&page_size=1",
        "catalog_id": "/api/network-regulators/catalog?page=1&page_size=1",
        "bypass_id": "/api/network-bypasses/items?page=1&page_size=1",
        "standard_tube_id": "/api/network-bypasses/tubes?page=1&page_size=1",
        "diaphragm_id": "/api/network-diaphragms/items?page=1&page_size=1",
        "elevator_id": "/api/elevators?page=1&page_size=1",
    }
    # фрагмент и участок сети — из справочника фрагментов и топологии
    status, body, _ = http_get(base + "/fragments", timeout=60, max_bytes=1 << 20)
    if status == 200:
        try:
            frags = json.loads(body.decode("utf-8", "replace")).get("data") or []
            frag_ids = [str(f["id"]) for f in frags if f.get("id") is not None]
            if frag_ids:
                ids["fragment_id"] = "74" if "74" in frag_ids else frag_ids[0]
        except Exception:
            pass
    if "fragment_id" in ids:
        status, body, _ = http_get(f"{base}/api/v1/topology/diagnostics?fragment_id={ids['fragment_id']}", timeout=90,
                                   max_bytes=1 << 22)
        if status == 200:
            try:
                faults = json.loads(body.decode("utf-8", "replace")).get("faults") or []
                line = next((f for f in faults if f.get("object_type") == "line"), None)
                if line:
                    ids["line_id"] = str(line["object_id"])
            except Exception:
                pass
    for key, path in probes.items():
        status, body, _ = http_get(base + path, timeout=90)
        if status != 200:
            continue
        try:
            payload = json.loads(body.decode("utf-8", "replace"))
        except Exception:
            continue
        items = payload.get("items") if isinstance(payload, dict) else None
        if items:
            ids[key] = str(items[0].get("id", ""))
    return ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    sys.path.insert(0, ".")
    import main as app_main  # noqa: E402

    print(f"Смоук-проверка {base}\n")
    print("Ищу реальные ID в журналах…")
    real_ids = discover_ids(base)
    print(f"  найдено ID: {len(real_ids)} ({', '.join(sorted(real_ids)) or '—'})\n")

    params = dict(FALLBACK_PARAMS)
    params.update({k: v for k, v in real_ids.items() if v})
    query_values = dict(QUERY_DEFAULTS)
    query_values.update({k: v for k, v in real_ids.items() if v and k in QUERY_DEFAULTS})
    query_values["line_id"] = params.get("line_id", "1")
    try:
        from database.alseko_binding import ISSUE_KINDS
        query_values["kind"] = next(iter(ISSUE_KINDS))
    except Exception:
        pass

    def required_query(route) -> list[str]:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            return []
        names = []
        stack = [dependant]
        while stack:
            dep = stack.pop()
            names += [p.alias for p in dep.query_params if p.required]
            stack.extend(dep.dependencies)
        return names

    routes = []
    route_query: dict[str, list[str]] = {}
    for route in app_main.app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if not path or path.startswith(SKIP_PATH_PREFIXES):
            continue
        for method in methods:
            if method in SKIP_METHODS or method == "HEAD":
                continue
            routes.append((method, path))
            route_query[path] = required_query(route)
    routes = sorted(set(routes))

    ok, empty_data, failed, skipped, unavailable = [], [], [], [], []

    for method, path in routes:
        url_path = path
        missing_param = None
        while "{" in url_path:
            start = url_path.index("{")
            end = url_path.index("}", start)
            name = url_path[start + 1:end]
            value = params.get(name)
            if value is None:
                missing_param = name
                break
            url_path = url_path[:start] + value + url_path[end + 1:]
        if missing_param:
            skipped.append((path, f"нет значения для {{{missing_param}}}"))
            continue

        query = []
        missing_query = None
        for name in route_query.get(path, []):
            if name not in query_values:
                missing_query = name
                break
            query.append(f"{name}={query_values[name]}")
        if missing_query:
            skipped.append((path, f"нет значения для ?{missing_query}"))
            continue
        if path in EXTRA_QUERY:
            query.append(EXTRA_QUERY[path].format(**query_values))
        if query:
            url_path = f"{url_path}?{'&'.join(query)}"

        sep = "&" if "?" in url_path else "?"
        probe = url_path
        if url_path.rstrip("/").endswith("/lookup"):
            probe = f"{url_path}{sep}table=fragments&id_col=id&name_col=name"
        elif url_path.endswith("/piezometer/path"):
            probe = f"{url_path}{sep}start=1&end=2"
        elif url_path.rstrip("/").endswith("/line/nodes/1"):
            # линейный маршрут проверяем на линейной таблице
            probe = "/line/heatpipesections/1"

        status, body, elapsed = http_get(base + probe)
        text = body.decode("utf-8", "replace")[:160].replace("\n", " ")

        if status == 200:
            is_empty = '"items":[]' in text.replace(" ", "") or '"features":[]' in text.replace(" ", "")
            (empty_data if is_empty else ok).append((path, elapsed))
            mark = "ПУСТО" if is_empty else "OK   "
            print(f"  {mark} {status} {elapsed:6.2f}s {method:4} {path}")
        elif status == 503 and any(m in text for m in DEPENDENCY_MARKERS):
            unavailable.append((path, text))
            print(f"  НЕТ   {status} {elapsed:6.2f}s {method:4} {path}  :: {text}")
        elif status in (404, 422) and "{" in path:
            # Ожидаемо для несуществующих ID/некорректных значений
            ok.append((path, elapsed))
            print(f"  OK    {status} {elapsed:6.2f}s {method:4} {path}  (ожидаемо)")
        else:
            failed.append((method, path, status, text))
            print(f"  FAIL  {status} {elapsed:6.2f}s {method:4} {path}  :: {text}")

    print(f"\nИтог: OK {len(ok)}, пустых данных {len(empty_data)}, "
          f"ошибок {len(failed)}, пропущено {len(skipped)}, без зависимости {len(unavailable)}")

    if unavailable:
        print("\nНе установлен опциональный пакет на хосте API (pip install -r requirements.txt):")
        for path, text in unavailable:
            print(f"  - {path}: {text}")

    if empty_data:
        print("\nПустые (маршрут работает, данных в БД нет):")
        for path, _ in empty_data:
            print(f"  - {path}")

    if skipped:
        print("\nПропущено:")
        for path, reason in skipped:
            print(f"  - {path}: {reason}")

    if failed:
        print("\nОШИБКИ:")
        for method, path, status, text in failed:
            print(f"  {status} {method} {path}\n      {text}")
        return 1

    slow = sorted([r for r in ok + empty_data if r[1] > 3.0], key=lambda r: -r[1])[:10]
    if slow:
        print("\nМедленные (>3s) — кандидаты на индексы/кэш:")
        for path, elapsed in slow:
            print(f"  {elapsed:6.2f}s {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
