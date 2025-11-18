import re, os, logging
from typing import Optional

from core.models import ExtractorBlock as Block, ExtractorPaper as Paper

logger = logging.getLogger(__name__)

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


_CONFIG_CACHE = None


def _load_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "question_detection.yaml")
    cfg_path = os.path.normpath(cfg_path)
    data = None
    if yaml and os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            data = None
    _CONFIG_CACHE = data or {}
    return _CONFIG_CACHE


def _q_re():
    cfg = _load_config()
    pattern = (
        cfg.get("q_regex")
        or r"^(?:question\s*|q\s*)?(?P<num>\d+(?:[\.\-]\d+)*[A-Z]?|\d+[A-Z]|\d+)(?:\s*[:)\.-]?\s*)"
    )
    flags = re.IGNORECASE
    return re.compile(pattern, flags)


def _marks_re():
    cfg = _load_config()
    pattern = cfg.get("marks_regex") or r"(?P<marks>\d+)\s*marks?"
    return re.compile(pattern, re.IGNORECASE)


def _word_to_num_re():
    words = (
        _load_config().get("marks_word_numbers")
        or ["one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen","twenty"]
    )
    pat = r"(?P<word>" + "|".join(re.escape(w) for w in words) + r")\s*marks?"
    return re.compile(pat, re.IGNORECASE)


def detect_in_text(text: str) -> Optional[tuple[str, Optional[str]]]:
    t = (text or "").strip()
    if not t:
        return None
    m = _q_re().match(t)
    if not m:
        return None
    num = m.group("num").strip().rstrip(".-")
    mm = _marks_re().search(t)
    marks = mm.group("marks") if mm else None
    if not marks:
        wmm = _word_to_num_re().search(t)
        if wmm:
            word = wmm.group("word").lower()
            mapping = {
                "one": "1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10",
                "eleven":"11","twelve":"12","thirteen":"13","fourteen":"14","fifteen":"15","sixteen":"16","seventeen":"17","eighteen":"18","nineteen":"19","twenty":"20",
            }
            marks = mapping.get(word)
    return num, marks


def detect_in_any_line(text: str) -> Optional[tuple[str, Optional[str]]]:
    """Looks for a question header at the start of any line in a multi-line text.

    Helpful for table text where headers may sit inside a cell.
    """
    if not text:
        return None
    # Fast path: whole text
    hit = detect_in_text(text)
    if hit:
        return hit
    # Check line by line
    for raw in (text.splitlines() or []):
        line = (raw or "").strip()
        if not line:
            continue
        m = _q_re().match(line)
        if not m:
            continue
        num = m.group("num").strip().rstrip(".-")
        mm = _marks_re().search(line)
        marks = mm.group("marks") if mm else None
        if not marks:
            wmm = _word_to_num_re().search(line)
            if wmm:
                word = wmm.group("word").lower()
                mapping = {
                    "one": "1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10",
                    "eleven":"11","twelve":"12","thirteen":"13","fourteen":"14","fifteen":"15","sixteen":"16","seventeen":"17","eighteen":"18","nineteen":"19","twenty":"20",
                }
                marks = mapping.get(word)
        return num, marks
    return None


def annotate_paper_questions(paper: Paper) -> int:
    """Annotate blocks for a paper with detected question headers.

    Returns count of detected headers.
    """
    count = 0
    logger.info(f"Starting question detection for paper ID: {paper.id}")
    for b in paper.blocks.order_by("order_index").all():
        # Look for headers at the start or in any table line
        num_marks = detect_in_any_line(b.text)
        if num_marks:
            num, marks = num_marks
            b.is_qheader = True
            b.detected_qnum = num
            b.detected_marks = marks or ""
            b.save(update_fields=["is_qheader", "detected_qnum", "detected_marks"])
            logger.info(f"Detected question header in block {b.id}: Question {num}, Marks: {marks or 'N/A'}")
            count += 1
        else:
            if b.is_qheader or b.detected_qnum or b.detected_marks:
                b.is_qheader = False
                b.detected_qnum = ""
                b.detected_marks = ""
                b.save(update_fields=["is_qheader", "detected_qnum", "detected_marks"])
    logger.info(f"Question detection completed for paper ID: {paper.id}. Total detected headers: {count}")
    return count
