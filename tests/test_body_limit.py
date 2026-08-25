import asyncio
import json

from anemiaiaback.internal.middleware.body_limit import RequestBodyLimitMiddleware


def test_rejects_oversized_content_length_without_reading_or_calling_downstream():
    called = {"receive": False, "app": False}
    sent = []

    async def app(_scope, _receive, _send):
        called["app"] = True

    async def receive():
        called["receive"] = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "headers": [(b"content-length", b"101")]}
    asyncio.run(RequestBodyLimitMiddleware(app, 100)(scope, receive, send))

    assert called == {"receive": False, "app": False}
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"]) == {
        "code": "request_too_large",
        "detail": "The request body exceeds the allowed size",
    }


def test_rejects_chunked_body_without_content_length_before_downstream():
    messages = iter([
        {"type": "http.request", "body": b"123456", "more_body": True},
        {"type": "http.request", "body": b"78901", "more_body": False},
    ])
    sent = []
    called = False

    async def app(_scope, _receive, _send):
        nonlocal called
        called = True

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    asyncio.run(RequestBodyLimitMiddleware(app, 10)({"type": "http", "headers": []}, receive, send))
    assert not called
    assert sent[0]["status"] == 413


def test_replays_accepted_chunked_body_unchanged():
    incoming = iter([
        {"type": "http.request", "body": b"abc", "more_body": True},
        {"type": "http.request", "body": b"def", "more_body": False},
    ])
    replayed = []

    async def app(_scope, receive, _send):
        replayed.append(await receive())
        replayed.append(await receive())

    async def receive():
        return next(incoming)

    async def send(_message):
        pass

    asyncio.run(RequestBodyLimitMiddleware(app, 10)({"type": "http", "headers": []}, receive, send))
    assert [message["body"] for message in replayed] == [b"abc", b"def"]
