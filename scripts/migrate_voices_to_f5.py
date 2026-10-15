"""One-time migration: backfill F5-TTS metadata on existing voice entries.

For every voice/narrator entry in voices_complete_xtts.json, this sets
engine="f5" and transcribes its reference clip into a cached "ref_text"
field so synthesize_text() never has to transcribe it at runtime.

Usage:
    ./PolyVox/bin/python scripts/migrate_voices_to_f5.py [--force]

--force re-transcribes entries that already have a ref_text.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VOICES_FILE = ROOT / "voices_complete_xtts.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-transcribe entries that already have ref_text")
    args = parser.parse_args()

    if not VOICES_FILE.exists():
        print(f"Voices file not found: {VOICES_FILE}")
        return 1

    from app.core.voices import transcribe_reference_audio

    data = json.loads(VOICES_FILE.read_text(encoding="utf-8"))
    updated = 0
    skipped = 0
    failed = 0

    for bucket in ("voices", "narrators"):
        for entry in data.get(bucket, []):
            label = entry.get("label", entry.get("id", "?"))
            entry["engine"] = "f5"

            if entry.get("ref_text") and not args.force:
                skipped += 1
                continue

            voice_file = entry.get("voice_file")
            voice_path = ROOT / voice_file if voice_file and not Path(voice_file).is_absolute() else Path(voice_file or "")
            if not voice_file or not voice_path.exists():
                print(f"  ⚠ {label}: voice_file missing ({voice_file}); skipping transcription")
                failed += 1
                continue

            try:
                print(f"  Transcribing {label} ({voice_file})...")
                entry["ref_text"] = transcribe_reference_audio(str(voice_path))
                print(f"    -> {entry['ref_text']!r}")
                updated += 1
            except Exception as exc:
                print(f"  ⚠ {label}: transcription failed: {exc}")
                failed += 1

    VOICES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. updated={updated} skipped(existing)={skipped} failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
