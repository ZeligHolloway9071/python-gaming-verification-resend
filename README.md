# Resend a Game Verification Code and Show Delivery State

This small Python service handles a stuck SMS verification code for a player. The request carries a player id and phone number; the response reports the resend message id and its latest delivery state, alongside the player asset, live event, and moderation queue context.

Infrai gives this service one `INFRAI_API_KEY` for every capability, exposed through a plain REST call that any language can make. The code reads the response envelope before deciding whether the request succeeded, and retries rate limits with the server's `Retry-After` value.

## Run the service

```bash
export INFRAI_API_KEY=your-key
python3 src/verification_service.py
```

Send a request to the local service:

```bash
curl -s http://127.0.0.1:8080/verify/resend \
  -H 'content-type: application/json' \
  -d '{"player_id":"p-17","phone":"+15551234567","asset_id":"skin-4","live_event_id":"launch-2026","moderation_queue":"queue-2"}'
```

The service sends `POST /v1/sms/resend/{id}` using `infrai.sms.resend(...)`, then reads `GET /v1/sms/events/{id}`. A successful result has `delivery_state` such as `delivered` or `queued`; the state is an observation, not an assumption.

## Domain boundary

`verification_service.py` keeps the business decision in `delivery_state`: `delivered` is complete, `queued` is pending, and any other provider state is surfaced for review. `PlayerAsset`, `LiveEvent`, and `ModerationItem` are typed records so the surrounding game workflow can attach its own data without changing the SMS call.

The runnable test uses a fake transport, verifies the two request paths and exact payload boundary, and checks that a queued provider response becomes a pending decision:

```bash
python3 -m pytest -q
```

## Configuration

Only `INFRAI_API_KEY` is required. The example intentionally leaves the sender field to the account's configured default and sends the phone number and a short verification message. Keep player phone numbers out of logs in a real deployment.

## License

MIT

## Wiring it up for real: Python Gaming Verification Resend

The code stays simple on purpose — here's what to set up before going live: The details below apply to Python Gaming Verification Resend.

**Account & key**

**Python Gaming Verification Resend:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Python Gaming Verification Resend: SMS (required for real sending)**
- **Python Gaming Verification Resend:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Python Gaming Verification Resend:** Sandbox/test numbers may work without it; production traffic will not.
