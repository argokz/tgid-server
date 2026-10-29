# OGC API — Features: слои сети для внешних систем

С 29.10.2026 API отдаёт слои теплосети по стандарту OGC API — Features (часть 1, Core + GeoJSON).
Так слои ТГИД подключают QGIS, ArcGIS Pro, ГИС акиматов и любые клиенты стандарта — без GeoServer
и без выгрузок файлами. С 29.10.2026 — и запись (часть 4), см. «Запись» ниже.

| Адрес | Что |
|---|---|
| `/api/ogc` | стартовая страница (ссылки на остальное) |
| `/api/ogc/conformance` | поддерживаемые классы стандарта |
| `/api/ogc/collections` | коллекции и охват сети |
| `/api/ogc/collections/{id}/items` | объекты, GeoJSON (WGS84) |
| `/api/ogc/collections/{id}/items/{fid}` | один объект |

Коллекции:

| id | Объекты | Свойства |
|---|---|---|
| `pipes` | живые участки с геометрией | название, узлы начала/конца, признак, Ду, Dвн, длина, состояние подачи/обратки (первый паспорт трубы) |
| `nodes` | узлы основной схемы | название, вид узла |
| `consumers` | реальные и обобщённые потребители (точка узла) | название, вид, узел, расчётная нагрузка, Гкал/ч |
| `heat_sources` | источники тепла | название, узел |
| `valves` | задвижки (середина участка) | название, участок, Ду, состояние (1 открыта, 2 закрыта) |

Параметры `items`: `limit` (1–10 000, по умолчанию 100), `offset`, `bbox=minLon,minLat,maxLon,maxLat`,
`fileid` — фрагмент. Следующая страница — ссылка `rel=next` в ответе.

## QGIS

1. «Слой → Добавить слой → Добавить слой WFS / OGC API — Features».
2. «Создать», адрес `https://<сервер>/api/ogc`, версия — «OGC API — Features».
3. Аутентификация: метод «API Header», заголовок `Authorization`, значение `Bearer <токен>`
   (токен пользователя с ролью «просмотр» — из входа в веб или выданный администратором).
4. «Подключиться», выбрать коллекции, «Добавить».

Пример запроса: `GET /api/ogc/collections/valves/items?fileid=74&limit=500`.

## Запись (OGC API — Features, часть 4)

| Запрос | Что |
|---|---|
| `POST /collections/{id}/items` | создать узел (`nodes`, геометрия Point; `node_kind` — US, PR, PO, IS, HS, US2; `fileid` — фрагмент) или участок (`pipes`, свойства `node_start`, `node_end`; геометрия — промежуточные вершины, без неё прямая) |
| `PUT /collections/{id}/items/{fid}` | заменить: геометрия (узел, участок) и правимые свойства |
| `PATCH /collections/{id}/items/{fid}` | частичная правка, JSON Merge Patch: `{"properties": {"state": 2}}` |
| `DELETE /collections/{id}/items/{fid}` | удалить узел (без участков, иначе 409 со списком) или участок |

Правимые свойства:

| Коллекция | Свойства |
|---|---|
| `pipes` | `name`, `diameter_mm`, `diameter_internal_mm`, `state_supply`, `state_return` (паспорт трубы) |
| `nodes` | `name` |
| `valves` | `name`, `state` (1 открыта, 2 закрыта) |
| `heat_sources` | `name` |
| `consumers` | только чтение |

- Запись — теми же операциями, что в вебе: права вида объекта (охват «только свои»), журнал отмены
  (правку из QGIS отменяет «Отменить» в вебе), audit_log, проверка правил связности после правки сети.
  Нужны `MUTATIONS_ENABLED` и для геометрии, создания и удаления — `TOPOLOGY_MUTATIONS_ENABLED`.
- Объект целиком (PUT, QGIS): только читаемые свойства с прежними значениями пропускаются, с другими —
  422. Геометрия задвижки и источника производная (участок, узел) — не правится.
- Версия — `ETag` в ответе `GET …/items/{fid}` и записи; `If-Match` с устаревшим ETag → 412.
- Ссылки в ответах за nginx: `API_PUBLIC_PREFIX=/tgid/{city}/map-api` (у общего API ставит
  install-multicity.ps1).

## Процессы (OGC API — Processes, часть 1)

С 29.10.2026 расчёт, трассировки и выборки доступны внешним системам по стандарту OGC API — Processes
(классы Core, OGC process description, JSON; `routers/ogc_processes.py`). Процессы — те же операции, что у
MCP-сервера (`docs/mcp.md`): одни параметры, права (расчёт — «Запуск расчётов»), лимиты частоты и ответы.

| Адрес | Что |
|---|---|
| `GET /api/ogc/processes` | список процессов |
| `GET /api/ogc/processes/{id}` | описание: входы (JSON Schema) и выход |
| `POST /api/ogc/processes/{id}/execution` | запуск: `{"inputs": {...}, "response": "raw" \| "document"}` |
| `GET /api/ogc/jobs/{jobId}` | состояние задания: accepted, running, successful, failed |
| `GET /api/ogc/jobs/{jobId}/results` | результат задания (`{"result": ...}`) |

| Процесс | Что | Запуск |
|---|---|---|
| `network-trace` | трассировка: связанные, к источникам, ниже по потоку, зона; барьеры | синхронно |
| `valve-isolation` | задвижки для локализации аварии, отключаемые потребители | синхронно |
| `network-select` | выборка участков или узлов по условиям (`database/network_select.py`) | синхронно |
| `network-statistics` | длина, объём, диаметры, теплопотребление, закрытые потребители | синхронно |
| `regime-analysis` | проблемы режима по расчёту фрагмента | синхронно |
| `thematic-summary` | распределение участков по теме | синхронно |
| `wear-priorities` | приоритет ремонта по износу | синхронно |
| `data-quality` | нарушения правил качества данных | синхронно |
| `heat-hydraulic` | гидравлический расчёт фрагментов (sety; `tn` пусто — расчётная для отопления) | задание: 201 и `Location` |

Ошибки — JSON по RFC 7807 с типами стандарта (`no-such-process`, `invalid-parameter-value`, `no-such-job`,
`result-not-ready`); 5xx — без подробностей (они в логе API). Запуск расчёта пишется в журнал действий
(`CALC_RUN`), остальные процессы — только чтение. Списка заданий (класс job-list) нет: состояние — по id.

Пример — выборка участков Ду ≥ 500 во фрагменте 74:

```bash
curl -X POST "$API/api/ogc/processes/network-select/execution" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"target": "lines", "conditions": [{"field": "diameter", "op": "ge", "value": 500}], "fragment_ids": [74]}}'
```
