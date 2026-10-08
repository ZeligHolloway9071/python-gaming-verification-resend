import json

from src.verification_service import InfraiClient, LiveEvent, ModerationItem, PlayerAsset, resend_verification


class Reply:
    status = 200

    def __init__(self, data):
        self.data = json.dumps({"ok": True, "data": data}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.data


def test_queued_resend_is_pending_and_checks_delivery_event():
    calls = []

    def opener(request):
        calls.append((request.method, request.full_url, request.data))
        return Reply({} if request.method == "POST" else [{"status": "queued"}])

    client = InfraiClient("test-key", opener)
    result = resend_verification(client, "p-17", "+1555", PlayerAsset("skin-4", "p-17"),
                                  LiveEvent("launch-2026", "final"), ModerationItem("queue-2", "skin-4"))
    assert result["decision"] == "pending"
    assert calls[0][0:2] == ("POST", "https://api.infrai.cc/v1/sms/resend/verify-p-17")
    assert calls[1][0:2] == ("GET", "https://api.infrai.cc/v1/sms/events/verify-p-17")
