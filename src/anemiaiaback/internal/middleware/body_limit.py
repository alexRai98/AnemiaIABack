import json
from typing import Any, Awaitable, Callable


Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
AsgiApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class RequestBodyLimitMiddleware:
    """Pure ASGI guard that rejects oversized bodies before multipart parsing."""

    def __init__(self, app: AsgiApp, max_request_bytes: int) -> None:
        self._app = app
        self._max_request_bytes = max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length > self._max_request_bytes:
            await self._send_too_large(send)
            return

        messages: list[Message] = []
        total = 0
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                messages.append(message)
                break
            total += len(message.get("body", b""))
            if total > self._max_request_bytes:
                await self._send_too_large(send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        index = 0

        async def replay() -> Message:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self._app(scope, replay, send)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    length = int(value)
                except (TypeError, ValueError):
                    return None
                return max(length, 0)
        return None

    @staticmethod
    async def _send_too_large(send: Send) -> None:
        body = json.dumps(
            {
                "code": "request_too_large",
                "detail": "The request body exceeds the allowed size",
            },
            separators=(",", ":"),
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
