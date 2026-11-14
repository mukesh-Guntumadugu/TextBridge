# TextBridge SMS: how people opt in

TextBridge is a text line that connects rural residents of Southeast Ohio with community health
workers and lets them book clinic visits by text. It is a student hackathon project
(Hackpalachia, Group 3).

## Opt-in is always started by the person

TextBridge never texts anyone first. The number is shared on printed flyers and posters at
clinics, libraries and community centers, and by community health workers, with this wording:

> **Need a ride, medicine, or a doctor's visit? Text us at [TextBridge number].**
> A community health worker will text you back. Msg & data rates may apply.
> Message frequency varies. Reply HELP for help, STOP to opt out. Emergencies: call 911.
> Terms: https://github.com/mukesh-Guntumadugu/TextBridge/blob/main/docs/TERMS.md
> Privacy: https://github.com/mukesh-Guntumadugu/TextBridge/blob/main/docs/PRIVACY.md

A person opts in by sending any text message to the TextBridge number (for example "hi").
Their first text is their consent to receive replies about their request.

## First reply (opt-in confirmation)

The first time a phone number texts TextBridge, it receives:

> TextBridge health line: replies to your texts, visit bookings and reminders. Msg & data rates
> may apply. Reply HELP for help, STOP to opt out.

followed by:

> TextBridge: What do you need care for, and what is your ZIP code or town? If this is an
> emergency, call 911.

## Example conversation

```
Person:     hi
TextBridge: TextBridge health line: replies to your texts, visit bookings and reminders. Msg & data rates may apply. Reply HELP for help, STOP to opt out.
TextBridge: TextBridge: What do you need care for, and what is your ZIP code or town? If this is an emergency, call 911.
Person:     need a checkup, 45764
TextBridge: Got it: Nelsonville, OH 45764. Reply 1 if low income, Medicaid or no insurance. Reply 2 if other insurance or you can pay.
Person:     1
TextBridge: Reply 1-3 to book (0 = none):
            1) Nelsonville Mobile 0mi Tue 11/17 10AM
            2) Glouster Mobile 8mi Wed 11/18 10AM
            3) Athens Health Ctr 11mi Mon 11/16 9AM
Person:     1
TextBridge: Booked: Nelsonville Mobile, Tue 11/17 10AM, Library parking lot, Nelsonville. Call 740-555-0110. Text CANCEL VISIT or RESCHEDULE to change.
TextBridge: Reminder: visit Tue 11/17 10AM at Nelsonville Mobile, Library parking lot, Nelsonville. ... (sent 24 hours before)
```

## Keywords

| Text | Result |
|------|--------|
| HELP | "TextBridge health line. Text what care you need and your ZIP to book. CANCEL VISIT or RESCHEDULE changes a visit. STOP to opt out. Emergency: 911" |
| STOP (also STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT) | No further messages are sent to that number, including reminders. |
| START | Opts back in. |

## What is sent

Only replies to the person's own texts, booking confirmations, and one reminder 24 hours
before a booked visit. No marketing or promotional messages are ever sent.
