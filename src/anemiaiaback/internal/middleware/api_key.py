import hmac

from starlette.types import ASGIApp, Receive, Scope, Send


class APIKeyMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        api_key: str,
        protected_prefix: str = "/api/v1",
        header_name: bytes = b"x-api-key",
    ) -> None:
        self._app = app
        self._api_key = api_key.encode("utf-8")
        self._protected_prefix = protected_prefix.rstrip("/")
        self._header_name = header_name.lower()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self._is_protected(scope.get("path", "")):
            await self._app(scope, receive, send)
            return

        supplied_key = next(
            (
                value
                for name, value in scope.get("headers", [])
                if name.lower() == self._header_name
            ),
            b"",
        )
        if not hmac.compare_digest(supplied_key, self._api_key):
            body = b'{"code":"unauthorized","detail":"A valid API key is required"}'
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        await self._app(scope, receive, send)

    def _is_protected(self, path: str) -> bool:
        return path == self._protected_prefix or path.startswith(
            f"{self._protected_prefix}/"
        )
