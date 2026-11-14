# TextBridge

A text line that connects rural patients with community health workers. It works on any phone,
flip phones included, so patients don't need home internet.

```
Patient (any carrier) ──text──▶ clinic number ──▶ server ──▶ health worker phones + dashboard
Health worker texts "#12 msg" ──▶ server ──▶ patient, sent from the clinic number
```

Neither side ever sees the other's personal number. Each new text is triaged by need (rides, medicine,
appointments, food, housing, mental health, insurance, utilities) and urgency. Claude does this when
`ANTHROPIC_API_KEY` is set, keyword rules otherwise. Emergency and crisis words always get an
immediate 911 / 988 reply, in English or Spanish.

## Run locally (no Twilio needed)

```bash
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8790
```

- Phone simulator: http://127.0.0.1:8790/simulator (a patient phone and a health worker phone side by side)
- Dashboard: http://127.0.0.1:8790/dashboard

## Health worker text commands

| Text            | Does                                   |
|-----------------|----------------------------------------|
| `#12 message`   | Sends the message to case 12's patient (first reply claims the case) |
| `#12 close`     | Closes case 12                         |
| `LIST`          | Lists open cases                       |

Patients can text `HELP`. `STOP` opts them out (Twilio enforces it) and closes their case.

## Connect real phones (Twilio)

1. Buy a number with SMS in the Twilio console (a 740 area code is local to Southeast Ohio).
2. Fill in `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `CLINIC_NUMBER`, `CHW_NUMBERS` and
   `PUBLIC_BASE_URL` in `.env`, and set `DASHBOARD_PASSWORD`.
3. Under the number's Messaging settings, set "A message comes in" to a webhook:
   `POST {PUBLIC_BASE_URL}/sms/inbound`.
4. For US numbers, register for A2P 10DLC (trial accounts can only text verified numbers).

For a quick public URL while testing: `ngrok http 8790`.

## Health data

Use made-up data in demos. Real patient texts need a Twilio BAA (HIPAA) or a self-hosted model
for triage.
