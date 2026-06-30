"""WSGI app for serverless platforms such as Vercel."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any, Callable, Iterable

from .converter import convert_pdf_bytes, inspect_pdf_bytes
from .server import MAX_BODY_BYTES, STATIC_DIR, options_from_query


StartResponse = Callable[[str, list[tuple[str, str]]], None]


def app(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    path = str(environ.get("PATH_INFO", "/") or "/")
    query = str(environ.get("QUERY_STRING", ""))

    if method == "OPTIONS":
        return response(start_response, HTTPStatus.NO_CONTENT, b"", content_type="text/plain")

    if method == "GET":
        if path in {"", "/"}:
            return static_html(start_response, "index.html")
        if path == "/health":
            return json_response(start_response, {"ok": True, "service": "pdf-to-dxf"})
        return json_response(start_response, {"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    if method == "POST":
        if path in {"/convert", "/convert/pdf-to-dxf"}:
            return convert_request(environ, start_response, query)
        if path == "/inspect":
            return inspect_request(environ, start_response, query)
        return json_response(start_response, {"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    return json_response(start_response, {"error": "Method not allowed"}, status=HTTPStatus.METHOD_NOT_ALLOWED)


def convert_request(environ: dict[str, Any], start_response: StartResponse, query: str) -> Iterable[bytes]:
    try:
        raw = read_body(environ)
        source_name = str(environ.get("HTTP_X_FILE_NAME", "uploaded.pdf"))
        report, dxf_bytes = convert_pdf_bytes(raw, source_name=source_name, options=options_from_query(query))
    except Exception as error:
        return json_response(start_response, {"error": str(error)}, status=HTTPStatus.BAD_REQUEST)

    headers = [
        ("Content-Disposition", 'attachment; filename="converted.dxf"'),
        ("X-Vector-Entities", str(report.vector_entity_count)),
        ("X-Text-Count", str(report.text_count)),
        ("X-Image-Count", str(report.image_count)),
    ]
    return response(start_response, HTTPStatus.OK, dxf_bytes, content_type="application/dxf", extra_headers=headers)


def inspect_request(environ: dict[str, Any], start_response: StartResponse, query: str) -> Iterable[bytes]:
    try:
        raw = read_body(environ)
        source_name = str(environ.get("HTTP_X_FILE_NAME", "uploaded.pdf"))
        payload = inspect_pdf_bytes(raw, source_name=source_name, options=options_from_query(query))
    except Exception as error:
        return json_response(start_response, {"error": str(error)}, status=HTTPStatus.BAD_REQUEST)

    return json_response(start_response, payload)


def read_body(environ: dict[str, Any]) -> bytes:
    try:
        content_length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError as error:
        raise ValueError("Invalid Content-Length.") from error
    if content_length <= 0:
        raise ValueError("Request body is empty.")
    if content_length > MAX_BODY_BYTES:
        raise ValueError("Request body is too large.")
    return environ["wsgi.input"].read(content_length)


def static_html(start_response: StartResponse, name: str) -> Iterable[bytes]:
    path = STATIC_DIR / name
    if not path.is_file():
        return json_response(start_response, {"error": "UI asset not found"}, status=HTTPStatus.NOT_FOUND)
    return response(
        start_response,
        HTTPStatus.OK,
        path.read_bytes(),
        content_type="text/html; charset=utf-8",
        extra_headers=[("Cache-Control", "no-store")],
    )


def json_response(
    start_response: StartResponse,
    payload: dict[str, Any],
    status: HTTPStatus = HTTPStatus.OK,
) -> Iterable[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return response(start_response, status, body, content_type="application/json; charset=utf-8")


def response(
    start_response: StartResponse,
    status: HTTPStatus,
    body: bytes,
    content_type: str,
    extra_headers: list[tuple[str, str]] | None = None,
) -> Iterable[bytes]:
    headers = cors_headers()
    headers.extend(
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
        ]
    )
    if extra_headers:
        headers.extend(extra_headers)
    start_response(f"{status.value} {status.phrase}", headers)
    return [body]


def cors_headers() -> list[tuple[str, str]]:
    return [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type,X-File-Name"),
    ]
