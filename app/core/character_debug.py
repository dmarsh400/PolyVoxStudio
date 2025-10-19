import sys
import json
import argparse
from pathlib import Path

from app.core.character_detection import attribute_dialogue, normalize_speakers


def main():
    parser = argparse.ArgumentParser(description="Character Detection Debugger")
    parser.add_argument("input_file", help="Path to input text file")
    parser.add_argument(
        "--use-spacy",
        action="store_true",
        help="Enable spaCy PERSON entity extraction",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    text = input_path.read_text(encoding="utf-8", errors="ignore")

    results, persons = attribute_dialogue(text, use_spacy=args.use_spacy)

    print("=== Raw Attributed Quotes ===")
    for r in results:
        print(json.dumps(r, ensure_ascii=False))

    print("\n=== spaCy PERSON Entities Detected ===")
    for p in persons:
        print(f"- {p}")

    # Save normalization map
    norm_path = Path(__file__).parent / "normalization.json"
    normalization = normalize_speakers(results, persons, norm_path)

    print(f"\nSaved normalization map → {norm_path}")


if __name__ == "__main__":
    main()
