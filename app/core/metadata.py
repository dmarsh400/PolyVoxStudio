from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover

def tag_mp3(path, title, artist, album, year=None, cover_path=None):
    audio = MP3(path, ID3=EasyID3)
    audio["title"] = title
    audio["artist"] = artist
    audio["album"] = album
    if year:
        audio["date"] = year
    audio.save()

def tag_m4b(path, title, artist, album, year=None, cover_path=None):
    audio = MP4(path)
    if title: audio["\xa9nam"] = title
    if artist: audio["\xa9ART"] = artist
    if album: audio["\xa9alb"] = album
    if year: audio["\xa9day"] = year
    if cover_path:
        with open(cover_path, "rb") as f:
            audio["covr"] = [MP4Cover(f.read(), imageformat=MP4Cover.FORMAT_PNG)]
    audio.save()