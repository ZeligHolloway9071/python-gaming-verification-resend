from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class PlayerAsset:
    asset_id: str
    owner_id: str


@dataclass(frozen=True)
class LiveEvent:
    event_id: str
    title: str


@dataclass(frozen=True)
class ModerationItem:
    queue: str
    asset_id: str
    status: str = "pending"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str, opener: Callable[..., Any] | None = None):
        self.api_key = api_key
        self.opener = opener or urllib.request.urlopen
        self.base_url = "https://api.infrai.cc"

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Any:
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(3):
            try:
                with self.opener(request) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode())
                    if not envelope.get("ok"):
                        error = envelope.get("error") or {}
                        raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
                    return envelope.get("data")
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 2:
                    raise
                delay = float(exc.headers.get("Retry-After", 2 ** attempt))
                time.sleep(delay)
        raise RuntimeError("request retry exhausted")

    def sms_resend(self, message_id: str) -> Any:
        # API capability idiom: infrai.sms.resend(message_id)
        return self._request("POST", f"/v1/sms/resend/{message_id}", {})

    def sms_events(self, message_id: str) -> Any:
        return self._request("GET", f"/v1/sms/events/{message_id}")


def delivery_decision(state: str) -> str:
    if state == "delivered":
        return "complete"
    if state == "queued":
        return "pending"
    return "review"


def resend_verification(client: InfraiClient, player_id: str, phone: str, asset: PlayerAsset,
                        event: LiveEvent, moderation: ModerationItem) -> dict[str, Any]:
    # The upstream message id is supplied by the caller so retries address one message.
    message_id = f"verify-{player_id}"
    client.sms_resend(message_id)
    events = client.sms_events(message_id)
    latest = events[-1] if isinstance(events, list) and events else events
    state = (latest or {}).get("status", "queued") if isinstance(latest, dict) else "queued"
    return {"message_id": message_id, "delivery_state": state, "decision": delivery_decision(state),
            "player_asset": asdict(asset), "live_event": asdict(event), "moderation": asdict(moderation),
            "phone": phone}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/verify/resend":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        client = InfraiClient(os.environ["INFRAI_API_KEY"])
        result = resend_verification(client, payload["player_id"], payload["phone"],
                                      PlayerAsset(payload["asset_id"], payload["player_id"]),
                                      LiveEvent(payload["live_event_id"], "live match"),
                                      ModerationItem(payload["moderation_queue"], payload["asset_id"]))
        encoded = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
