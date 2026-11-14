"""Outbound texts. Goes through Twilio when keys are set, otherwise only
recorded in the database so the dev phone simulator can show it."""
import logging

from . import config, db

log = logging.getLogger("sms")
_client = None


def _twilio():
    global _client
    if _client is None:
        from twilio.rest import Client

        _client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    return _client


def send(to: str, body: str, case_id: int | None, sender: str) -> None:
    sid, channel = None, "dev"
    if config.TWILIO_ENABLED:
        try:
            msg = _twilio().messages.create(to=to, from_=config.CLINIC_NUMBER, body=body)
            sid, channel = msg.sid, "twilio"
        except Exception as e:
            log.error("Twilio send to %s failed: %s", to, e)
            channel = "failed"
    else:
        log.info("[dev] -> %s: %s", to, body)
    db.add_message(case_id, sender, config.CLINIC_NUMBER, to, body, channel, sid)
