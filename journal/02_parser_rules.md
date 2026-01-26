# 02 — Parsing Rules (Time / Date / Language)

## Scope
Parsing is strict and deterministic. The bot detects only supported formats and ignores ambiguous patterns.

## Supported Time Formats (MVP)
English:
- HH:MM (10:30)
- H am/pm (10am, 10 am, 10 a.m.)
- HHhMM (22h30)
- noon / midnight
- ranges (10:00–11:00, 10:00-11:00)
- multiple times in one message

Russian:
- "в HH:MM" (в 10:30, в 22:30)
- "в H утра/вечера/дня/ночи" (в 10 утра, в 7 вечера)

Explicitly not supported:
- 10.30
- standalone "10"
- standalone "в 10"

## Date Anchors
- today / сегодня
- tomorrow / завтра
- weekday references in EN/RU with modifiers:
  - next/this/last/previous/past
  - следующий/этот/прошлый/тот/на той неделе

## Ignore Rules (False Positive Prevention)
- version numbers (v10.3.0)
- numeric dates (10/11)
- ratings (10/10)
- unit/currency numbers (10km, 10$)
- floats (5.836)
- any time mentions inside inline or multiline code blocks

## Language Behavior
- Language detection is binary (en/ru) for MVP.
- Bot responses must match the triggering message language.
