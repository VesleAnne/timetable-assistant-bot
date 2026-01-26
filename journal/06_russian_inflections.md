# 06 — Russian Weekday Inflections Support

## Problem
Russian is a flective language, so weekday words appear in different forms depending on context:
- "пятница" (nominative)
- "в пятницу" (accusative)
- "во вторник" (accusative)
- "в эту пятницу" (weekday + adjective inflected)
- "в прошлую пятницу" (weekday + adjective inflected)
- "в следующую среду" (weekday + adjective inflected)

The initial parser only supported weekday words in nominative form, which would miss many realistic chat messages.

## MVP Decision
We support the most common practical weekday constructions in Russian:

### Supported weekday forms
Weekday tokens (including common inflections):
- понедельник / понедельника
- вторник / вторника
- среда / среду
- четверг / четверга
- пятница / пятницу
- суббота / субботу
- воскресенье / воскресенья
- abbreviations: пн, вт, ср, чт, пт, сб, вс

### Supported prepositions
- "в <weekday>"
- "во <weekday>" (e.g. "во вторник")

### Supported modifiers (inflected)
We support common modifier/adjective patterns using stem-based matching:
- "эт*" (этот, эту, этой...) => THIS
- "следующ*" (следующий, следующую...) => NEXT
- "прошл*" (прошлый, прошлую...) => LAST
- "тот/той" => LAST
- "... на той неделе" => LAST (explicit rule from spec)

Examples:
- "в эту пятницу" => THIS Friday
- "в прошлую пятницу" => LAST Friday
- "в следующую среду" => NEXT Wednesday

## Implementation Notes
- `RU_WEEKDAYS` dictionary was expanded to include common inflected forms.
- `RU_WEEKDAY_RE` was updated to match modifier stems and inflected weekday forms.
- Modifier resolution uses simple deterministic prefix matching:
  - startswith("эт") => THIS
  - startswith("следующ") => NEXT
  - startswith("прошл") => LAST

This approach is intentionally simple and robust for MVP.

## Explicit Non-Goals (MVP)
We do NOT support recurring time expressions such as:
- "по пятницам"
- "каждый понедельник"
- "каждую неделю"

Rationale:
Recurring scheduling introduces repetition semantics and is out of scope for MVP, which focuses on one-off meeting/event coordination.
