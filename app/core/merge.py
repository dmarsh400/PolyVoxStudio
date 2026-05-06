from pydub import AudioSegment
from pathlib import Path

def merge_mp3(chapter_files, out_path, chapters_txt=None):
    combined = None
    for f in chapter_files:
        seg = AudioSegment.from_file(f)
        combined = seg if combined is None else combined + seg
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    combined.export(out_path, format="mp3")
    if chapters_txt:
        Path(chapters_txt).write_text("\n".join(chapter_files))

def to_m4b(chapter_files, out_path, cover=None):
    combined = None
    for f in chapter_files:
        seg = AudioSegment.from_file(f)
        combined = seg if combined is None else combined + seg
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    combined.export(out_path, format="mp4")