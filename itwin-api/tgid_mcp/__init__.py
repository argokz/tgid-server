"""MCP-сервер ТГИД (Model Context Protocol): инструменты API для ИИ-клиентов (Claude, Cursor, свои агенты).

protocol.py — JSON-RPC 2.0 и методы MCP (initialize, tools/list, tools/call, ping) без сторонних библиотек;
tools.py — инструменты поверх тех же функций, что у веба (права пользователя те же); маршрут — routers/mcp.py.
"""
