"""Routing between patients and community health workers (CHWs).

Patient (any carrier) --text--> clinic number --> server --> on-call CHW phones
CHW texts "#<case> message"      --> server --> patient, from the clinic number

Neither side ever sees the other's personal number.
"""
import re

from . import config, db, sms
from .triage import triage

STOP_WORDS = {"stop", "stopall", "unsubscribe", "cancel", "end", "quit"}
CHW_REPLY = re.compile(r"^\s*#(\d+)\s*(.*)$", re.S)

TEXT = {
    "en": {
        "ack": "Thanks, we got your message. A community health worker will text you back "
               "soon at this number. If this is an emergency, call 911.",
        "emergency": "If someone is in danger right now, call 911. We are alerting a "
                     "health worker now.",
        "crisis": "You are not alone. Call or text 988 any time to reach the Suicide & "
                  "Crisis Lifeline.",
        "help": "This is the community health text line. Text us what you need (rides, "
                "medicine, appointments, food, bills). Text STOP to opt out. Emergencies: 911.",
    },
    "es": {
        "ack": "Gracias, recibimos su mensaje. Un trabajador de salud comunitaria le "
               "responderá pronto a este número. Si es una emergencia, llame al 911.",
        "emergency": "Si alguien está en peligro ahora, llame al 911. Estamos avisando a "
                     "un trabajador de salud.",
        "crisis": "No está solo. Llame o envíe un texto al 988 para hablar con la Línea "
                  "de Crisis y Suicidio (oprima 2 para español).",
        "help": "Esta es la línea de texto de salud comunitaria. Díganos qué necesita. "
                "Envíe STOP para cancelar. Emergencias: 911.",
    },
}


def _t(lang: str, key: str) -> str:
    return TEXT.get(lang if lang in TEXT else "en")[key]


def _tail(phone: str) -> str:
    return "..." + phone[-4:]


def is_chw(phone: str) -> bool:
    return phone in config.CHW_NUMBERS


def handle_incoming(from_phone: str, body: str) -> None:
    body = (body or "").strip()
    if not body:
        return
    if is_chw(from_phone):
        _from_chw(from_phone, body)
    else:
        _from_patient(from_phone, body)


# ---------------------------------------------------------------- patients
def _from_patient(phone: str, body: str) -> None:
    word = body.lower()
    case = db.open_case_for(phone)

    if word in STOP_WORDS:
        # Twilio blocks further texts and sends its own opt-out confirmation.
        if case:
            db.add_message(case["id"], "patient", phone, config.CLINIC_NUMBER, body, "inbound")
            db.update_case(case["id"], status="closed")
        return
    if word == "help":
        lang = case["language"] if case else "en"
        db.add_message(case["id"] if case else None, "patient", phone, config.CLINIC_NUMBER, body, "inbound")
        sms.send(phone, _t(lang, "help"), case["id"] if case else None, "system")
        return

    if case is None:
        tri = triage(body)
        case_id = db.create_case(phone, tri)
        db.add_message(case_id, "patient", phone, config.CLINIC_NUMBER, body, "inbound")
        lang = tri["language"]
        if tri["crisis"]:
            sms.send(phone, _t(lang, "crisis"), case_id, "system")
        if tri["urgency"] == "emergency":
            sms.send(phone, _t(lang, "emergency"), case_id, "system")
        else:
            sms.send(phone, _t(lang, "ack"), case_id, "system")
        header = f"[#{case_id} {tri['urgency'].upper()} {tri['category']}] {_tail(phone)}"
        note = f"{header}: {body}\nSummary: {tri['summary']}\nReply: #{case_id} your message"
        for chw in config.CHW_NUMBERS:
            sms.send(chw, note, case_id, "system")
        return

    # Follow-up on an open case: relay to the assigned CHW, or everyone on call.
    db.add_message(case["id"], "patient", phone, config.CLINIC_NUMBER, body, "inbound")
    targets = [case["assigned_chw"]] if case["assigned_chw"] else config.CHW_NUMBERS
    for chw in targets:
        sms.send(chw, f"[#{case['id']}] {_tail(phone)}: {body}", case["id"], "system")


# ---------------------------------------------------------------- CHWs
def _from_chw(chw: str, body: str) -> None:
    if body.lower() == "list":
        db.add_message(None, "chw", chw, config.CLINIC_NUMBER, body, "inbound")
        open_cases = db.list_cases("open")[:8]
        lines = [f"#{c['id']} {c['urgency']} {c['category']} {_tail(c['patient_phone'])}"
                 + (" (you)" if c["assigned_chw"] == chw else "") for c in open_cases]
        sms.send(chw, "Open cases:\n" + "\n".join(lines) if lines else "No open cases.", None, "system")
        return

    m = CHW_REPLY.match(body)
    if not m:
        db.add_message(None, "chw", chw, config.CLINIC_NUMBER, body, "inbound")
        sms.send(chw, "Start with the case number, e.g. \"#12 I can drive you Tuesday at 9\". "
                      "\"#12 close\" closes it, LIST shows open cases.", None, "system")
        return

    case_id, text = int(m.group(1)), m.group(2).strip()
    case = db.get_case(case_id)
    if case is None:
        sms.send(chw, f"No case #{case_id}.", None, "system")
        return
    db.add_message(case_id, "chw", chw, config.CLINIC_NUMBER, body, "inbound")

    if text.lower() == "close":
        db.update_case(case_id, status="closed")
        sms.send(chw, f"#{case_id} closed.", case_id, "system")
        return
    if not text:
        sms.send(chw, f"Add a message after #{case_id}.", case_id, "system")
        return
    if case["status"] != "open":
        sms.send(chw, f"#{case_id} is closed; the patient's next text opens a new case.", case_id, "system")
        return

    if not case["assigned_chw"]:
        db.update_case(case_id, assigned_chw=chw)
        for other in config.CHW_NUMBERS:
            if other != chw:
                sms.send(other, f"#{case_id} taken by {_tail(chw)}.", case_id, "system")
    sms.send(case["patient_phone"], text, case_id, "chw")


def reply_from_dashboard(case_id: int, text: str) -> bool:
    case = db.get_case(case_id)
    if case is None or case["status"] != "open" or not text.strip():
        return False
    sms.send(case["patient_phone"], text.strip(), case_id, "dashboard")
    return True
