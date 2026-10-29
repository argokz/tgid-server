"""JSON-RPC 2.0 и методы MCP (спецификация 2025-06-18, транспорт Streamable HTTP без потоков SSE).

Сервер без состояния: сессии (Mcp-Session-Id) не выдаются, каждый POST — самостоятельный запрос;
ответ — application/json. Возможности — только инструменты (tools), список не меняется на лету.
"""
from __future__ import annotations

from typing import Any, Optional

from auth import AuthUser
from tgid_mcp import tools as mcp_tools

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
LATEST_VERSION = PROTOCOL_VERSIONS[0]
SERVER_INFO = {"name": "tgid", "title": "ТГИД — ГИС тепловых сетей", "version": "1.0.0"}
INSTRUCTIONS = (
    "Инструменты ГИС тепловых сетей ТГИД одного города: фрагменты сети, поиск узлов и участков, трассировки, "
    "изоляция аварии задвижками, запросы по сети, анализ режима и тематические сводки по последним расчётам, "
    "износ, качество данных, запуск гидравлического расчёта. Сначала найдите фрагмент (list_fragments) и "
    "объекты (search_network); id узлов и участков — из их ответов. Права — как у пользователя токена."
)

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def error_response(msg_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def negotiate_version(requested: Any) -> str:
    """Версия клиента, если сервер её знает; иначе — последняя (клиент решит, продолжать ли)."""
    return requested if requested in PROTOCOL_VERSIONS else LATEST_VERSION


async def _dispatch(method: str, params: dict[str, Any], user: AuthUser,
                    client: Optional[dict[str, str]]) -> dict[str, Any]:
    if method == "initialize":
        return {
            "protocolVersion": negotiate_version(params.get("protocolVersion")),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": INSTRUCTIONS,
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": mcp_tools.describe_tools()}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or name not in mcp_tools.TOOLS:
            raise RpcError(INVALID_PARAMS, f"Неизвестный инструмент: {name}")
        if not isinstance(arguments, dict):
            raise RpcError(INVALID_PARAMS, "arguments — объект")
        return await mcp_tools.call_tool(name, arguments, user, client)
    raise RpcError(METHOD_NOT_FOUND, f"Метод не поддерживается: {method}")


async def handle_message(message: Any, user: AuthUser,
                         client: Optional[dict[str, str]] = None) -> Optional[dict[str, Any]]:
    """Одно сообщение JSON-RPC → ответ; уведомления и ответы клиента — None (HTTP 202).
    client — ip и user_agent запроса для журнала действий."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return error_response(None, INVALID_REQUEST, "Ожидается сообщение JSON-RPC 2.0")
    method = message.get("method")
    if method is None:
        return None  # ответ клиента на запрос сервера — сервер запросов не шлёт
    is_notification = "id" not in message
    msg_id = message.get("id")
    if not isinstance(method, str) or (not is_notification and not isinstance(msg_id, (str, int))):
        return error_response(msg_id if isinstance(msg_id, (str, int)) else None, INVALID_REQUEST,
                              "method — строка, id — строка или число")
    if is_notification:
        return None  # notifications/initialized, notifications/cancelled — ответа не требуют
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return error_response(msg_id, INVALID_PARAMS, "params — объект")
    try:
        result = await _dispatch(method, params, user, client)
    except RpcError as exc:
        return error_response(msg_id, exc.code, exc.message, exc.data)
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}
