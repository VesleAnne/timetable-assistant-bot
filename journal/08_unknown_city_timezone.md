# 08 — Unknown City Timezone Handling (Helpful Errors)

## Problem
In MVP we support "city name" timezones using a curated mapping (Amsterdam, Yerevan, etc.).
Users may write other cities such as "Berlin", which are valid timezones but not present in the curated list.

If the bot silently fails or falls back to onboarding (/tz set...), it becomes confusing:
- the user DID specify a timezone, but it wasn't recognized.

## MVP Decision
If a message includes an explicit timezone token that is NOT recognized (unknown city / unknown abbreviation),
the bot MUST NOT ask the sender to configure their profile timezone.

Instead, the bot MUST respond with a helpful error suggesting the IANA timezone format:

EN:
- "I couldn't recognize timezone 'Berlin'. Try `Europe/Berlin`."

RU:
- "Не удалось распознать часовой пояс 'Berlin'. Попробуйте `Europe/Berlin`."

## Rationale
- Teaches users the most reliable explicit timezone format.
- Prevents silent conversion failures.
- Keeps MVP deterministic and avoids introducing external city databases.

## Out of Scope (MVP)
- Full global city name recognition
- Automatic city->timezone lookup via external APIs
