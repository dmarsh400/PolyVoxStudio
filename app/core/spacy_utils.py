import spacy
import json
import os

# Load spaCy English pipeline with NER + parser + tagging
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' not found. "
                "Run: python -m spacy download en_core_web_sm"
            )
    return _nlp

def extract_entities(text):
    """
    Extract named entities (people, orgs, places) from text using spaCy.
    Returns list of (entity_text, entity_label).
    """
    nlp = get_nlp()
    doc = nlp(text)
    return [(ent.text, ent.label_) for ent in doc.ents]

def extract_person_names(text):
    """
    Extract PERSON entities from text.
    Returns list of unique names.
    """
    nlp = get_nlp()
    doc = nlp(text)
    return list({ent.text for ent in doc.ents if ent.label_ == "PERSON"})

def resolve_coreferences(text):
    """
    Enhanced pronoun resolution: map 'he', 'she', 'they' to recent PERSON entities
    with gender, proximity, and narrative context.
    Returns list of (original_text, resolved_speaker, confidence).
    """
    nlp = get_nlp()
    doc = nlp(text)
    results = []
    last_persons = []
    gender_map = {}
    sentence_idx = 0
    person_positions = {}
    context_roles = {}

    for sent in doc.sents:
        sentence_idx += 1
        for ent in sent.ents:
            if ent.label_ == "PERSON":
                if ent.text not in last_persons:
                    last_persons.append(ent.text)
                    person_positions[ent.text] = sentence_idx
                    if len(last_persons) > 5:
                        oldest = last_persons.pop(0)
                        del person_positions[oldest]
                for token in sent:
                    if token.lower_ in {"prisoner", "manager"} and ent.text not in context_roles:
                        context_roles[ent.text] = token.lower_
                for token in sent:
                    if token.lower_ in {"he", "him", "his"}:
                        gender_map[ent.text] = "male"
                    elif token.lower_ in {"she", "her", "hers"}:
                        gender_map[ent.text] = "female"

        for token in sent:
            if token.lower_ in {"he", "she", "they"} and token.pos_ == "PRON":
                pronoun_gender = (
                    "male" if token.lower_ in {"he", "him", "his"}
                    else "female" if token.lower_ in {"she", "her", "hers"}
                    else None
                )
                best_candidate, best_score = None, 0.0
                for person in reversed(last_persons):
                    score = 0.8 if person_positions[person] == sentence_idx else 0.6
                    if pronoun_gender and gender_map.get(person) == pronoun_gender:
                        score += 0.2
                    if context_roles.get(person) in {"prisoner", "manager"} and "plexiglass" in sent.text.lower():
                        score += 0.3
                    if score > best_score:
                        best_candidate, best_score = person, score
                results.append((token.text, best_candidate, best_score if best_candidate else 0.0))

    return results if results else [(text, None, 0.0)]

def detect_speaker_candidates(text):
    """
    Find PERSON entities and narrative roles near speech verbs.
    Returns list of candidate names, integrating coreference resolution.
    """
    nlp = get_nlp()
    doc = nlp(text)
    candidates = []
    coref_results = resolve_coreferences(text)
    pronoun_to_speaker = {pr: sp for pr, sp, _ in coref_results if sp}

    for sent in doc.sents:
        has_speech_verb = any(
            token.lemma_ in {
                "say", "ask", "reply", "shout", "cry", "mutter", "whisper",
                "exclaim", "murmur", "declare", "groan", "sigh", "quip",
                "retort", "snap"
            }
            for token in sent
        )
        if has_speech_verb:
            for ent in sent.ents:
                if ent.label_ == "PERSON":
                    candidates.append(ent.text)
            for token in sent:
                if token.lower_ in pronoun_to_speaker:
                    candidates.append(pronoun_to_speaker[token.lower_])
            for token in sent:
                if token.lower_ in {"prisoner", "manager"}:
                    sent_idx = list(doc.sents).index(sent) if hasattr(doc.sents, "index") else 0
                    context_sents = [sent] if sent_idx == 0 else [list(doc.sents)[sent_idx-1], sent]
                    for ctx_sent in context_sents:
                        for ent in ctx_sent.ents:
                            if ent.label_ == "PERSON":
                                candidates.append(ent.text)
                                break
            sent_idx = list(doc.sents).index(sent) if hasattr(doc.sents, "index") else 0
            if sent_idx > 0:
                prev_sent = list(doc.sents)[sent_idx - 1]
                for ent in prev_sent.ents:
                    if ent.label_ == "PERSON":
                        candidates.append(ent.text)
                for token in prev_sent:
                    if token.lower_ in pronoun_to_speaker:
                        candidates.append(pronoun_to_speaker[token.lower_])
    return list(set(candidates))


# ---------------- Configuration Loader ---------------- #

CONFIG = {
    "min_speaker_frequency": 2,
    "forbidden_speakers": []
}

config_path = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "config", "character_detection_config.json"
)
config_path = os.path.abspath(config_path)

if os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            if isinstance(user_config, dict):
                CONFIG.update(user_config)
    except Exception as e:
        print(f"[spacy_utils] Warning: Failed to load config: {e}")
