"""Training-free emotion steering for F5-TTS (after EmoSteer-TTS, arXiv:2508.03543).

Steering vectors (emotion mean - neutral mean of DiT activations) are built once from the public
RAVDESS speech corpus and cached on disk. At synthesis time they are added to each DiT block's
post-attention residual stream.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

import torch
import torch.nn.functional as F

DATA_DIR = Path(__file__).resolve().parent / "data" / "emosteer"
VECTOR_FILE = DATA_DIR / "steering_vectors.pt"
RAVDESS_URL = "https://zenodo.org/records/1188976/files/Audio_Speech_Actors_01-24.zip?download=1"

# RAVDESS emotion codes -> our labels.
_CODE_TO_EMOTION = {"01": "neutral", "03": "happy", "04": "sad", "05": "angry", "06": "fearful", "07": "disgusted", "08": "surprised"}
_STATEMENTS = {"01": "Kids are talking by the door.", "02": "Dogs are sitting by the door."}
_ACTORS = range(1, 7)
_VECTOR_LEN = 512
_EXTRACT_NFE = 16

# Steering strength at intensity 1.0; vectors are unit-norm per layer, so this is absolute (paper uses 5-10).
BASE_ALPHA = 8.0
MAX_ALPHA = 12.0

_lock = threading.Lock()
_vectors: Optional[Dict[str, torch.Tensor]] = None
_patched = False


def _steer_block(x: torch.Tensor, steer: torch.Tensor, alpha: float, cache: dict) -> torch.Tensor:
    t_len = x.shape[1]
    resized = cache.get(t_len)
    if resized is None:
        resized = F.interpolate(steer.transpose(1, 2), size=t_len, mode="nearest").transpose(1, 2)
        resized = resized.to(x.dtype)
        cache.clear()
        cache[t_len] = resized
    orig = x.norm(dim=-1, keepdim=True)
    steered = x + alpha * resized
    return steered * (orig / (steered.norm(dim=-1, keepdim=True) + 1e-8))


def _patch_dit_block() -> None:
    """Add optional capture/steer hooks to F5-TTS DiTBlock without changing default behavior."""
    global _patched
    if _patched:
        return
    from f5_tts.model.modules import DiTBlock

    def forward(self, x, t, mask=None, rope=None):
        norm, gate_msa, shift_mlp, scale_mlp, gate_mlp = self.attn_norm(x, emb=t)
        attn_output = self.attn(x=norm, mask=mask, rope=rope)
        x = x + gate_msa.unsqueeze(1) * attn_output

        if getattr(self, "_emo_capture", False):
            self._emo_captured = x[:1].detach().float().cpu()
        steer = getattr(self, "_emo_steer", None)
        if steer is not None:
            x = _steer_block(x, steer, self._emo_alpha, self._emo_cache)

        norm = self.ff_norm(x) * (1 + scale_mlp[:, None]) + shift_mlp[:, None]
        ff_output = self.ff(norm)
        return x + gate_mlp.unsqueeze(1) * ff_output

    DiTBlock.forward = forward
    _patched = True


def _blocks(tts):
    return tts.ema_model.transformer.transformer_blocks


def _download_corpus(dest_zip: Path) -> None:
    print(f"[emosteer] Downloading RAVDESS speech corpus (~200MB, one time) -> {dest_zip}")
    req = urllib.request.Request(RAVDESS_URL, headers={"User-Agent": "PolyVoxStudio"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest_zip, "wb") as out:
        shutil.copyfileobj(resp, out, length=1 << 20)


def _select_clips(zf: zipfile.ZipFile) -> Dict[str, List[tuple]]:
    """Per emotion: [(zip_member, transcript)] using fixed actors; neutral uses normal intensity."""
    clips: Dict[str, List[tuple]] = {e: [] for e in _CODE_TO_EMOTION.values()}
    for name in sorted(zf.namelist()):
        m = re.search(r"(\d\d)-(\d\d)-(\d\d)-(\d\d)-(\d\d)-(\d\d)-(\d\d)\.wav$", name)
        if not m:
            continue
        modality, channel, emo, intensity, statement, rep, actor = m.groups()
        if channel != "01" or rep != "01" or int(actor) not in _ACTORS or emo not in _CODE_TO_EMOTION:
            continue
        wanted_intensity = "01" if emo == "01" else "02"
        if intensity != wanted_intensity or statement not in _STATEMENTS:
            continue
        clips[_CODE_TO_EMOTION[emo]].append((name, _STATEMENTS[statement]))
    return clips


def _class_mean(tts, zf: zipfile.ZipFile, items: List[tuple], tmp: Path, label: str) -> torch.Tensor:
    blocks = _blocks(tts)
    total = torch.zeros(len(blocks), _VECTOR_LEN, blocks[0].attn.to_q.in_features)
    count = 0
    for block in blocks:
        block._emo_capture = True
    try:
        for n, (member, transcript) in enumerate(items, start=1):
            wav_path = tmp / os.path.basename(member)
            wav_path.write_bytes(zf.read(member))
            try:
                tts.infer(
                    ref_file=str(wav_path), ref_text=transcript, gen_text=transcript,
                    nfe_step=_EXTRACT_NFE, show_info=lambda *_: None, progress=_NullProgress,
                )
            except Exception as exc:
                print(f"[emosteer] {label} clip {n} failed: {exc}")
                continue
            if not all(torch.isfinite(b._emo_captured).all() for b in blocks):
                print(f"[emosteer] {label} clip {n} produced non-finite activations; skipped")
                continue
            for i, block in enumerate(blocks):
                act = block._emo_captured[0]  # [T, D]
                resized = F.interpolate(act.t().unsqueeze(0), size=_VECTOR_LEN, mode="nearest")[0].t()
                total[i] += resized
            count += 1
            print(f"[emosteer] {label}: {n}/{len(items)}")
    finally:
        for block in blocks:
            block._emo_capture = False
            block._emo_captured = None
    if count == 0:
        raise RuntimeError(f"No activations captured for '{label}'")
    return total / count


class _NullProgress:
    @staticmethod
    def tqdm(iterable=None, *a, **k):
        return iterable if iterable is not None else []


def build_vectors(tts) -> Dict[str, torch.Tensor]:
    """Extract activations from RAVDESS and save emotion-minus-neutral steering vectors."""
    _patch_dit_block()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_root = Path(tempfile.mkdtemp(prefix="emosteer_"))
    try:
        zip_path = tmp_root / "ravdess.zip"
        _download_corpus(zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            clips = _select_clips(zf)
            print("[emosteer] Building steering vectors (one time, several minutes)...")
            neutral = _class_mean(tts, zf, clips["neutral"], tmp_root, "neutral")
            vectors: Dict[str, torch.Tensor] = {}
            for emotion, items in clips.items():
                if emotion == "neutral":
                    continue
                diff = _class_mean(tts, zf, items, tmp_root, emotion) - neutral  # [layers, L, D]
                norms = diff.flatten(1).norm(dim=1).clamp_min(1e-8)
                vectors[emotion] = (diff / norms[:, None, None]).half()
        torch.save(vectors, VECTOR_FILE)
        print(f"[emosteer] Saved steering vectors -> {VECTOR_FILE}")
        return vectors
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def _ensure_vectors(tts) -> Optional[Dict[str, torch.Tensor]]:
    global _vectors
    if _vectors is not None:
        return _vectors
    with _lock:
        if _vectors is not None:
            return _vectors
        _patch_dit_block()
        try:
            if VECTOR_FILE.exists():
                _vectors = torch.load(VECTOR_FILE, map_location="cpu")
            else:
                _vectors = build_vectors(tts)
        except Exception as exc:
            print(f"[emosteer] Steering unavailable, using neutral synthesis: {exc}")
            _vectors = {}
    return _vectors


def apply(tts, emotion: Optional[str], intensity: float = 1.0) -> bool:
    """Arm steering for the next infer() call. Returns True if steering is active."""
    clear(tts)
    if not emotion:
        return False
    vectors = _ensure_vectors(tts)
    vec = (vectors or {}).get(emotion)
    if vec is None:
        return False
    blocks = _blocks(tts)
    if vec.shape[0] != len(blocks) or not torch.isfinite(vec).all():
        return False
    alpha = min(MAX_ALPHA, BASE_ALPHA * max(0.0, intensity))
    device = next(tts.ema_model.parameters()).device
    for i, block in enumerate(blocks):
        block._emo_steer = vec[i].unsqueeze(0).to(device=device, dtype=torch.float32)
        block._emo_alpha = alpha
        block._emo_cache = {}
    print(f"[emosteer] Steering toward '{emotion}' (alpha={alpha:.2f})")
    return True


def clear(tts) -> None:
    if not _patched:
        return
    for block in _blocks(tts):
        block._emo_steer = None
        block._emo_cache = {}
