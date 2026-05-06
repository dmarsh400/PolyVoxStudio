import re

def normalize_characters(results):
    """
    Clean and normalize speaker names while keeping all lines intact.
    Input:  [{"speaker": str, "text": str}]
    Output: [{"speaker": str, "text": str}]
    """

    normalized = []
    for r in results:
        speaker = r.get("speaker", "Unknown") or "Unknown"

        # Normalize case (always Title Case, except Narrator/Unknown)
        if speaker.lower() in ["narrator", "unknown"]:
            clean_name = speaker.capitalize()
        else:
            clean_name = speaker.strip()
            clean_name = re.sub(r"\s+", " ", clean_name)  # collapse multiple spaces
            clean_name = clean_name.title()

        normalized.append({
            "speaker": clean_name,
            "text": r.get("text", "").strip()
        })

    return normalized
