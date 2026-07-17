"""
app/utils/image_optimize.py
───────────────────────────
Auto-converts any uploaded image to AVIF (preferred) or WebP on save.
Original file is deleted after a successful conversion.

Usage:
    from app.utils.image_optimize import optimize_image
    path = optimize_image("/absolute/path/to/uploaded.jpg")
    # path is now "/absolute/path/to/uploaded.avif" (or .webp)
    # original .jpg is gone
"""
import os
import logging

_log = logging.getLogger(__name__)

_AVIF_QUALITY = 68   # 0-100  (72 ≈ visually lossless for photos, ~70 % smaller than JPEG)
_WEBP_QUALITY = 78   # 0-100  (82 gives excellent quality)
_WEBP_METHOD  = 4    # 0-6    (4 = good speed/size balance)
_MAX_DIMENSION = 1400  # pixels — downscale huge originals to save even more space


def optimize_image(src_path: str) -> str:
    """
    Convert src_path → AVIF (or WebP fallback).
    Deletes the original on success.
    Returns the new file path (always absolute).
    Safe: on any error, returns src_path unchanged.
    """
    try:
        from PIL import Image

        stem = os.path.splitext(src_path)[0]

        with Image.open(src_path) as img:
            img.load()  # fully decode before we potentially delete

            # Downscale very large images (saves storage + loads faster on mobile)
            w, h = img.size
            if max(w, h) > _MAX_DIMENSION:
                scale = _MAX_DIMENSION / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

            # Normalise colour mode — both AVIF and WebP support RGBA
            if img.mode not in ("RGB", "RGBA", "L", "LA"):
                img = img.convert("RGBA" if "A" in img.mode else "RGB")

            # ── 1. Try AVIF (better compression, ~50 % smaller than WebP) ──
            avif_path = stem + ".avif"
            try:
                img.save(avif_path, "AVIF", quality=_AVIF_QUALITY)
                _safe_del(src_path)
                _log.info("img→avif  %s", avif_path)
                return avif_path
            except Exception as _e:
                _log.debug("AVIF encode failed (%s); trying WebP", _e)
                _safe_del(avif_path)  # partial file

            # ── 2. Fall back to WebP ──────────────────────────────────────
            webp_path = stem + ".webp"
            img.save(webp_path, "WEBP", quality=_WEBP_QUALITY, method=_WEBP_METHOD)
            _safe_del(src_path)
            _log.info("img→webp  %s", webp_path)
            return webp_path

    except Exception as exc:
        _log.warning("optimize_image failed for %s: %s", src_path, exc)
        return src_path  # safe fallback — keep original as-is


def _safe_del(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
