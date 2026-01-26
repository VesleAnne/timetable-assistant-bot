# 04 — Metrics, Feedback, and "Shutdown" Signals

## Why
We want to measure:
- activation rate (how often bot triggers)
- adoption (how often people use it successfully)
- friction (how often onboarding happens)
- complaints (feedback volume)
- shutdown behavior (monitor_off, mute)

## MVP Metrics Events

Discord:
- discord_time_detected
- discord_convert_button_clicked
- discord_conversion_success
- discord_conversion_onboarding_shown
- discord_conversion_blocked_user_muted
- discord_monitor_channel_added
- discord_monitor_channel_removed

Telegram:
- telegram_time_detected
- telegram_public_reply_sent
- telegram_dm_sent
- telegram_dm_skipped_disabled
- telegram_dm_skipped_not_eligible
- telegram_dm_blocked_user_muted
- telegram_monitor_enabled
- telegram_monitor_disabled
- telegram_timezone_override_set / cleared (admin actions)

User preference changes:
- user_timezone_set / cleared
- user_muted / unmuted
- user_deleted_data

Feedback:
- feedback_submitted

## Commands Added (MVP)
- /feedback <text>  (Discord + Telegram)
- /mute (Discord + Telegram)
- /unmute (Discord + Telegram)

## Interpretation Guidance
- "Activation" can be defined as time detection events.
- Discord adoption can be measured via click-through rate (clicks / detections).
- Onboarding rate is a measure of missing timezone setups.
- Shutdown signals include monitor_off and per-user mute.