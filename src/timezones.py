"""
Timezone mappings - single source of truth.

This module contains all city-to-IANA timezone mappings and abbreviations.
By keeping this in one place, we avoid duplication between parser.py and engine.py.
"""
from .models import Language

# City name to IANA timezone mapping
# Includes both English and Russian city names
CITY_TO_IANA = {
    # Europe (English)
    "Amsterdam": "Europe/Amsterdam",
    "Moscow": "Europe/Moscow",
    "Lisbon": "Europe/Lisbon",
    "Milan": "Europe/Rome",
    "Belgrade": "Europe/Belgrade",
    "London": "Europe/London",
    "Paris": "Europe/Paris",
    "Berlin": "Europe/Berlin",
    
    # Europe (Russian - Европа)

    "Амстердам": "Europe/Amsterdam",
    "Москва": "Europe/Moscow",
    "Лиссабон": "Europe/Lisbon",
    "Милан": "Europe/Rome",
    "Белград": "Europe/Belgrade",
    "Лондон": "Europe/London",
    "Париж": "Europe/Paris",
    "Берлин": "Europe/Berlin",
    
    # Cyprus / Limassol (English + Russian)
    "Cyprus": "Asia/Nicosia",
    "Limassol": "Asia/Nicosia",
    "Кипр": "Asia/Nicosia",
    "Лимассол": "Asia/Nicosia",
    
    # Caucasus (English + Russian)
    "Tbilisi": "Asia/Tbilisi",
    "Yerevan": "Asia/Yerevan",
    "Тбилиси": "Asia/Tbilisi",
    "Ереван": "Asia/Yerevan",
    
    # Americas (English)
    "Vancouver": "America/Vancouver",
    "Miami": "America/New_York",
    "New York": "America/New_York",
    "Los Angeles": "America/Los_Angeles",
    "Chicago": "America/Chicago",
    
    # Americas (Russian - Америка)
    "Ванкувер": "America/Vancouver",
    "Майами": "America/New_York",
    "Нью-Йорк": "America/New_York",
    "Лос-Анджелес": "America/Los_Angeles",
    "Чикаго": "America/Chicago",
    
    # Asia (English + Russian)
    "Tokyo": "Asia/Tokyo",
    "Токио": "Asia/Tokyo",
    
    # Oceania (English + Russian)
    "Sydney": "Australia/Sydney",
    "Сидней": "Australia/Sydney",
}

# Automatically generated set of all known city names
# Used by parser to detect timezone mentions in messages
KNOWN_CITY_NAMES = set(CITY_TO_IANA.keys())

# Timezone abbreviations mapping
# Note: Abbreviations are ambiguous globally, so we keep this intentionally small
ABBR_TO_IANA = {
    "CET": "Europe/Paris",
    "CEST": "Europe/Paris",
    "EET": "Europe/Athens",
    "EEST": "Europe/Athens",
    "MSK": "Europe/Moscow",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
}

# IANA timezone -> preferred display label per language
IANA_TO_CITY_EN = {
    "Europe/Amsterdam": "Amsterdam",
    "Europe/Moscow": "Moscow",
    "Europe/Lisbon": "Lisbon",
    "Europe/Rome": "Milan",
    "Europe/Belgrade": "Belgrade",
    "Europe/London": "London",
    "Europe/Paris": "Paris",
    "Europe/Berlin": "Berlin",
    "Asia/Nicosia": "Limassol",
    "Asia/Tbilisi": "Tbilisi",
    "Asia/Yerevan": "Yerevan",
    "America/Vancouver": "Vancouver",
    "America/New_York": "New York",
    "America/Los_Angeles": "Los Angeles",
    "America/Chicago": "Chicago",
    "Asia/Tokyo": "Tokyo",
    "Australia/Sydney": "Sydney",
}

IANA_TO_CITY_RU = {
    "Europe/Amsterdam": "Амстердам",
    "Europe/Moscow": "Москва",
    "Europe/Lisbon": "Лиссабон",
    "Europe/Rome": "Милан",
    "Europe/Belgrade": "Белград",
    "Europe/London": "Лондон",
    "Europe/Paris": "Париж",
    "Europe/Berlin": "Берлин",
    "Asia/Nicosia": "Лимассол",
    "Asia/Tbilisi": "Тбилиси",
    "Asia/Yerevan": "Ереван",
    "America/Vancouver": "Ванкувер",
    "America/New_York": "Нью-Йорк",
    "America/Los_Angeles": "Лос-Анджелес",
    "America/Chicago": "Чикаго",
    "Asia/Tokyo": "Токио",
    "Australia/Sydney": "Сидней",
}



def tz_display_name(tz: str, lang: Language) -> str:
    if lang == Language.RU:
        return IANA_TO_CITY_RU.get(tz, tz)
    return IANA_TO_CITY_EN.get(tz, tz)

CITY_NAME_TRANSLATIONS = {
    "Amsterdam": "Амстердам",
    "Moscow": "Москва",
    "Lisbon": "Лиссабон",
    "Milan": "Милан",
    "Belgrade": "Белград",
    "Cyprus": "Кипр",
    "Limassol": "Лимассол",
    "Tbilisi": "Тбилиси",
    "Yerevan": "Ереван",
    "Vancouver": "Ванкувер",
    "Miami": "Майами",
    "New York": "Нью-Йорк",
    "London": "Лондон",
    "Paris": "Париж",
    "Berlin": "Берлин",
    "Tokyo": "Токио",
    "Sydney": "Сидней",
    "Los Angeles": "Лос-Анджелес",
    "Chicago": "Чикаго",
}
