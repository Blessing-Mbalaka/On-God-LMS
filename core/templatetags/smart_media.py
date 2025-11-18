# core/templatetags/smart_media.py
from django import template
from django.conf import settings
from pathlib import Path

register = template.Library()

@register.filter
def smart_src(rel_path: str) -> str:
    """
    Accepts:
      - "question_images/foo.emf" (relative)
      - "/media/question_images/foo.emf" (absolute under MEDIA_URL)
      - Full URLs (http/https) or data: URIs
    Returns a URL that prefers a sibling .png if present.
    """
    if not rel_path:
        return ""

    rel_str = str(rel_path).strip()

    # Pass through absolute URLs and data URIs
    if rel_str.startswith(("http://", "https://", "data:")):
        return rel_str

    media_url = settings.MEDIA_URL
    media_root = Path(settings.MEDIA_ROOT)

    # Normalize: strip MEDIA_URL or leading slash to get a relative path
    if rel_str.startswith(media_url):
        rel_str = rel_str[len(media_url):]
    if rel_str.startswith("/"):
        rel_str = rel_str[1:]

    rel_norm = rel_str.replace("\\", "/")
    abs_path = media_root / rel_norm

    # If EMF/WMF, prefer a .png sibling
    low = rel_norm.lower()
    if low.endswith(".emf") or low.endswith(".wmf"):
        png_rel = rel_norm.rsplit(".", 1)[0] + ".png"
        png_abs = media_root / png_rel
        if png_abs.exists():
            return (media_url.rstrip("/") + "/" + png_rel)

    # Otherwise, return original under MEDIA_URL
    return (media_url.rstrip("/") + "/" + rel_norm)
