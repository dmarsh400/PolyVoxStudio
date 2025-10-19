import os
from pathlib import Path
from typing import Optional

from app.core.voices import get_engine, list_all_voices


class Synthesizer:
    def __init__(self, output_dir: str = "output_audio", default_engine: str = "Coqui"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.default_engine = default_engine
        self.voices = list_all_voices(preferred_engine=default_engine)

    def synthesize(
        self,
        text: str,
        voice_id: str,
        out_path: Optional[str] = None,
        settings: Optional[dict] = None,
    ) -> str:
        """
        Synthesize text to speech using the correct engine.
        """
        # Find matching voice
        v = next(
            (x for x in self.voices if x["id"] == voice_id or x.get("label") == voice_id),
            None,
        )
        if not v:
            raise ValueError(f"Voice not found: {voice_id}")

        eng_name = v.get("engine", self.default_engine)
        eng = get_engine(eng_name)

        out_path = out_path or str(
            self.output_dir / f"{voice_id.replace('/', '_')}.wav"
        )
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        eng.synthesize(
            text=text,
            voice_id=v["id"],
            out_path=out_path,
            settings=settings or {"speaker": v.get("speaker")},
        )
        return out_path
