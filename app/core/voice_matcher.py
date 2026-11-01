"""Suggest a voice for each character from BookNLP gender/age, role words and speech style."""
from __future__ import annotations

import hashlib
import re
from typing import Dict, Iterable, List, Optional, Tuple

_AGE_LADDER = {"Teen": 0.0, "Young Adult": 1.0, "Adult": 2.0, "Middle-Aged": 3.0, "Mature": 4.0, "Senior": 5.0}
_BOOKNLP_AGE_TARGET = {"child": 0.0, "teen": 0.5, "adult": 2.0, "elder": 5.0}

_MALE_NAME_WORDS = {"mr", "sir", "lord", "king", "prince", "duke", "father", "brother", "boy", "uncle", "baron", "count", "sheriff"}
_FEMALE_NAME_WORDS = {"mrs", "miss", "ms", "lady", "queen", "princess", "duchess", "mother", "sister", "girl", "aunt", "madam", "madame", "baroness"}

# Role words in a character's name -> traits wanted from the voice.
_ROLE_TRAITS = {
    "authority": {"guard", "officer", "sergeant", "captain", "general", "sheriff", "deputy", "detective", "soldier", "agent", "warden", "commander", "lieutenant", "colonel", "major", "marshal"},
    "refined": {"doctor", "dr", "professor", "judge", "lawyer", "senator", "president", "bishop", "lord", "lady", "butler", "king", "queen"},
}

# Trait -> words searched in a voice's label/description/personality/accent.
_VOICE_TRAIT_WORDS = {
    "tough": {"tough", "gruff", "street", "badass", "rough", "urban", "casual", "hard"},
    "authority": {"military", "authoritative", "commanding", "deep", "gruff"},
    "refined": {"professional", "sophisticated", "elegant", "articulate", "classic", "clear"},
    "energetic": {"expressive", "energetic", "excited", "warm", "friendly", "cheerful", "bright"},
}

_PROFANITY = re.compile(r"\b(fuck\w*|shit\w*|damn\w*|bitch\w*|bastard\w*|hell|ass|crap|goddamn\w*)\b", re.IGNORECASE)

BOOKNLP_BONUS_GENDER = 12.0
GENDER_MISMATCH = -100.0


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z]+", (text or "").lower())


def _name_gender(name: str) -> Optional[str]:
    words = set(_tokens(name))
    if words & _FEMALE_NAME_WORDS:
        return "female"
    if words & _MALE_NAME_WORDS:
        return "male"
    return None


def _speech_traits(quotes: List[str]) -> Dict[str, bool]:
    text = " ".join(quotes)
    words = max(1, len(text.split()))
    excl = sum(q.count("!") for q in quotes) / max(1, len(quotes))
    return {
        "tough": len(_PROFANITY.findall(text)) >= 2 or len(_PROFANITY.findall(text)) / words > 0.015,
        "energetic": excl > 0.35,
    }


def _jitter(name: str, label: str) -> float:
    return int(hashlib.md5(f"{name}|{label}".encode()).hexdigest()[:4], 16) / 65535.0 * 0.5


def _voice_text(voice: Dict[str, object]) -> set:
    return set(_tokens(" ".join(str(voice.get(k) or "") for k in ("label", "description", "personality", "accent"))))


def _score(name: str, is_narrator: bool, gender: Optional[str], age_target: Optional[float],
           traits: Dict[str, bool], voice: Dict[str, object]) -> float:
    score = 0.0
    v_gender = str(voice.get("gender") or "").lower()
    if gender and v_gender:
        score += BOOKNLP_BONUS_GENDER if v_gender == gender else GENDER_MISMATCH

    v_age = _AGE_LADDER.get(str(voice.get("age") or ""))
    if v_age is not None:
        if age_target is not None:
            score -= max(0.0, abs(v_age - age_target) - 1.0) * 3.0
        elif is_narrator:
            score -= abs(v_age - 3.0) * 1.5

    words = _voice_text(voice)
    for trait, wanted in traits.items():
        if wanted and words & _VOICE_TRAIT_WORDS.get(trait, set()):
            score += 3.0
    if is_narrator:
        if words & _VOICE_TRAIT_WORDS["refined"]:
            score += 4.0
        if "narrator" in words:
            score += 6.0
        if words & _VOICE_TRAIT_WORDS["tough"]:
            score -= 3.0
    return score


def match_voices(
    characters: Iterable[str],
    lines: List[Dict[str, object]],
    profiles: Dict[str, Dict[str, object]],
    voices: List[Dict[str, object]],
    existing: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Return {character: voice label} for characters not already in `existing`."""
    existing = dict(existing or {})
    voices = [v for v in voices if v.get("label")]
    if not voices:
        return {}

    quotes: Dict[str, List[str]] = {}
    for line in lines:
        if line.get("is_quote"):
            quotes.setdefault(str(line.get("speaker")), []).append(str(line.get("text") or ""))

    ordered = sorted(
        set(characters),
        key=lambda c: (c != "Narrator", -len(quotes.get(c, [])), c),
    )

    uses: Dict[str, int] = {}
    for label in existing.values():
        uses[label] = uses.get(label, 0) + 1

    result: Dict[str, str] = {}
    for name in ordered:
        if name in existing:
            continue
        profile = profiles.get(name) or {}
        gender = profile.get("inferred_gender")
        gender = gender if gender in ("male", "female") else _name_gender(name)
        age_target = _BOOKNLP_AGE_TARGET.get(str(profile.get("inferred_age_category") or ""))

        traits = _speech_traits(quotes.get(name, []))
        words = set(_tokens(name))
        for trait, role_words in _ROLE_TRAITS.items():
            if words & role_words:
                traits[trait] = True

        best_label, best_score = None, None
        for voice in voices:
            label = str(voice["label"])
            score = _score(name, name == "Narrator", gender, age_target, traits, voice)
            score -= uses.get(label, 0) * 25.0  # spread characters across different voices
            score += _jitter(name, label)
            if best_score is None or score > best_score:
                best_label, best_score = label, score
        if best_label:
            result[name] = best_label
            uses[best_label] = uses.get(best_label, 0) + 1
    return result
