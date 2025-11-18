"""
Convert .emf images to visible .jpeg for a given paper.

Best-effort strategy:
- Prefer ImageMagick if available: `magick input.emf output.jpg` or legacy `convert`.
- Updates BlockImage records to point to the new JPEG and removes the old EMF on success.

Configure via env:
- CONVERT_EMF_CMD (optional): full command template, supports {src} and {dst}.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import List, Tuple

from django.conf import settings

from core.models import ExtractorPaper


def _run(cmd: List[str]) -> Tuple[bool, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
        return (p.returncode == 0, p.stdout or "")
    except Exception as ex:
        return (False, str(ex))


def _im_available() -> Tuple[str|None, str|None]:
    # Try `magick -version`
    ok, out = _run(["magick", "-version"]) 
    if ok:
        return ("magick", out)
    # Try legacy `convert -version` (GraphicsMagick or ImageMagick)
    ok, out = _run(["convert", "-version"]) 
    if ok:
        return ("convert", out)
    return (None, None)


def _convert_one(src_abs: str, dst_abs: str) -> Tuple[bool, str]:
    # Allow override
    tmpl = os.environ.get("CONVERT_EMF_CMD", "").strip()
    if tmpl:
        cmdline = [c.format(src=src_abs, dst=dst_abs) for c in tmpl.split()]
        return _run(cmdline)
    # Auto-detect ImageMagick
    exe, _ = _im_available()
    if exe:
        if exe == "magick":
            return _run(["magick", src_abs, dst_abs])
        else:
            return _run([exe, src_abs, dst_abs])
    return (False, "No converter found (set CONVERT_EMF_CMD or install ImageMagick)")


def convert_emf_images(paper: ExtractorPaper) -> dict:
    """Convert .emf images for this paper to .jpeg.

    Returns a summary dict: {converted: int, skipped: int, failed: list[str]}
    """
    from core.models import ExtractorBlockImage  # local import to avoid cycles

    media_root = settings.MEDIA_ROOT
    qs = paper.blocks.prefetch_related("images").all()
    converted = 0
    skipped = 0
    failed: List[str] = []

    for block in qs:
        for img in block.images.all():
            rel = img.image.name  # e.g., paper_images/12/image2.emf
            if not rel.lower().endswith(".emf"):
                skipped += 1
                continue
            src_abs = os.path.join(media_root, rel)
            if not os.path.exists(src_abs):
                failed.append(f"missing: {rel}")
                continue
            base, _ = os.path.splitext(rel)
            dst_rel = base + ".jpeg"
            dst_abs = os.path.join(media_root, dst_rel)

            # Ensure output dir exists
            os.makedirs(os.path.dirname(dst_abs), exist_ok=True)

            ok, out = _convert_one(src_abs, dst_abs)
            if not ok or not os.path.exists(dst_abs):
                failed.append(f"convert failed: {rel} -> {dst_rel} :: {out}")
                continue

            # Update DB to new JPEG path
            img.image.name = dst_rel.replace("\\", "/")
            img.save(update_fields=["image"])

            # Remove original EMF to avoid dangling files
            try:
                os.remove(src_abs)
            except OSError:
                pass

            converted += 1

    return {"converted": converted, "skipped": skipped, "failed": failed}