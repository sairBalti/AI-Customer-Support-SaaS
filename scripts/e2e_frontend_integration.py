"""One-shot Docs→Knowledge→Chat→Ticket→Audit E2E against local API."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000/api/v1"


def req(method: str, path: str, token: str | None = None, data: dict | None = None, files: dict | None = None):
    url = f"{BASE}{path}"
    headers: dict[str, str] = {}
    body: bytes | None = None
    if files:
        import uuid

        boundary = f"----ACS{uuid.uuid4().hex}"
        parts: list[bytes] = []
        for name, (filename, content, ctype) in files.items():
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
            )
            parts.append(f"Content-Type: {ctype}\r\n\r\n".encode())
            parts.append(content)
            parts.append(b"\r\n")
        for name, value in (data or {}).items():
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            parts.append(str(value).encode())
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return exc.code, payload


def main() -> int:
    results: dict[str, str] = {}
    code, login = req(
        "POST",
        "/auth/login",
        data={"email": "superadmin@platform.com", "password": "Str0ng!Password"},
    )
    results["login"] = str(code)
    if code != 200:
        print(json.dumps({"results": results, "error": login}, indent=2))
        return 1
    token = login["data"]["tokens"]["access_token"]
    uid = login["data"]["user"]["user_id"]

    content = (
        b"Password Reset Policy\n\n"
        b"To reset your password, visit the account settings page and click Forgot Password.\n"
        b"You will receive a reset link by email within 5 minutes.\n"
        b"Never share your password with support agents.\n"
        b"Support agents cannot see customer passwords.\n"
    )
    code, upload = req(
        "POST",
        "/documents",
        token=token,
        data={"document_name": "Password Reset Policy"},
        files={"file": ("password_reset.txt", content, "text/plain")},
    )
    results["upload"] = f"{code} id={upload.get('data', {}).get('document_id')}"
    if code not in (200, 201):
        print(json.dumps({"results": results, "error": upload}, indent=2))
        return 1
    doc_id = upload["data"]["document_id"]

    code, proc = req("POST", f"/documents/{doc_id}/process", token=token, data={})
    results["process"] = str(code)

    status = ""
    chunks = 0
    fail = None
    for i in range(40):
        time.sleep(2)
        code, doc = req("GET", f"/documents/{doc_id}", token=token)
        status = doc["data"]["processing_status"]
        chunks = doc["data"]["total_chunks"]
        fail = doc["data"].get("failure_reason")
        print(f"poll {i} {status} chunks={chunks}", flush=True)
        if status in {"COMPLETED", "FAILED"}:
            break
    results["poll"] = f"status={status} chunks={chunks} fail={fail}"
    if status != "COMPLETED":
        print(json.dumps({"results": results, "error": "process incomplete"}, indent=2))
        return 1

    code, ks = req(
        "POST",
        "/knowledge/search",
        token=token,
        data={"query": "How do I reset my password?", "top_k": 5},
    )
    hits = len(ks.get("data", {}).get("items") or [])
    results["knowledge"] = f"{code} hits={hits}"

    code, conv = req("POST", "/chat/conversations", token=token, data={"title": "E2E password help"})
    cid = conv["data"]["conversation_id"]
    code, msg = req(
        "POST",
        f"/chat/conversations/{cid}/messages",
        token=token,
        data={"content": "How do I reset my password according to company policy?"},
    )
    sources = len(msg.get("data", {}).get("sources") or [])
    used = msg.get("data", {}).get("used_knowledge")
    results["chat"] = f"{code} used={used} sources={sources}"

    code, esc = req(
        "POST",
        f"/chat/conversations/{cid}/ticket",
        token=token,
        data={
            "subject": "Need password reset help",
            "description": "Customer asked about password reset",
            "priority": "HIGH",
            "category": "ACCOUNT",
        },
    )
    tid = esc["data"]["ticket_id"]
    results["escalate"] = f"{code} ticket={esc['data']['ticket_number']} status={esc['data']['status']}"

    code, assigned = req("POST", f"/tickets/{tid}/assign", token=token, data={"assigned_to": uid})
    results["assign"] = f"{code} status={assigned['data']['status']}"

    code, resolved = req("POST", f"/tickets/{tid}/resolve", token=token, data={})
    results["resolve"] = f"{code} status={resolved['data']['status']}"

    code, closed = req("POST", f"/tickets/{tid}/close", token=token, data={})
    results["close"] = f"{code} status={closed['data']['status']}"

    code, audit = req("GET", "/audit-logs?page=1&page_size=40", token=token)
    items = audit.get("data", {}).get("items") or []
    interesting = [
        i["action"]
        for i in items
        if any(k in i["action"] for k in ("document", "chat", "ticket", "knowledge"))
    ][:15]
    results["audit"] = f"{code} total={audit['data']['meta']['total_items']} interesting={';'.join(interesting)}"

    print(json.dumps({"ok": True, "results": results}, indent=2))
    Path("e2e_report.json").write_text(json.dumps({"ok": True, "results": results}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
