"""
Auto Draw Blocks: Suggests grouped question regions for a paper.

Design goals
- Use robust heuristics to group blocks into question chunks starting at headers.
- Classify each chunk with a coarse qtype and note presence of images/tables.
- Prepare results for client-side drawing: provide involved block IDs and metadata.
- Optionally leverage per-paper `system_prompt` to guide an LLM in future.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import os, json
import logging
import requests

from core.models import ExtractorPaper as Paper, ExtractorBlock as Block
from .question_detect import detect_in_any_line


def _guess_qtype(texts: List[str]) -> str:
    t = "\n".join(texts).lower()
    # Simple instruction cues
    if any(k in t for k in ["instruction", "read all instructions", "read the following instructions", "answer all questions"]):
        return "instruction"
    # Default to question
    return "question"


def build_default_system_prompt() -> str:
    return (
        "You are an exam paper analyzer. Your job is to segment the paper into question blocks. "
        "Each question block starts at a detectable question header. question headers start from 1.1, some are nested in tables should be found regardless.(e.g., '' main question header (1.1)', sub questionsn (1.1.1, 1.1.2, 1.1.3, 1.1.4, 1.1.5, 1.16), 2.1.1, 2.1. '2.3'). "
        "Include all supporting content that belongs to the question such as paragraphs, images, and tables "
        "until the next peer question header. Capture whether the block contains images and/or tables. "
        "Output should preserve the question number and optionally the marks if stated."
        "constructive response, and other types of questions should be classified as questions."
        "ensure 1. are not classified as questions only 1.1 the 1. letter are instructuions"
    )


def _ollama_suggest(paper: Paper, blocks: List[Block]) -> Optional[List[Dict[str, Any]]]:
    """Call local Ollama (if available) to propose question regions.

    Returns None on failure. Expects Ollama at OLLAMA_HOST (default http://localhost:11434)
    and OLLAMA_MODEL env (default 'llama3:latest').
    """
    try:
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "llama3:latest")
        url = f"{host.rstrip('/')}/api/chat"
        # Prepare a concise document snapshot to keep prompt small
        items = []
        for b in blocks:
            txt = (b.text or "").strip()
            if len(txt) > 800:
                txt = txt[:800] + "…"
            items.append({
                "id": b.id,
                "type": b.block_type,
                "has_image": (b.block_type == "image") or b.images.exists(),
                "has_table": (b.block_type == "table"),
                "text": txt,
            })

        sys_prompt = (paper.system_prompt or build_default_system_prompt()).strip()
        user_req = (
            "Given the following ordered blocks from an exam paper, group them into question regions. "
            "A region starts at a question header and includes supporting blocks (paragraphs, images, tables) until the next header. "
            "Return strict JSON only in this schema: {\n  \"items\": [ {\n    \"block_ids\": [int...],\n    \"question_number\": string,\n    \"marks\": string,\n    \"qtype\": one of ['constructed','mcq','case_study','table_q','image_q']\n  } ... ]\n}. "
            "Use block IDs exactly as provided. Prefer contiguous ranges."
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_req + "\nBlocks JSON:\n" + json.dumps(items, ensure_ascii=False)},
        ]
        payload = {"model": model, "messages": messages, "stream": False}
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content") or data.get("response") or ""
        if not content:
            return None
        # Extract JSON payload
        start = content.find('{')
        if start == -1:
            start = content.find('[')
        if start == -1:
            return None
        json_text = content[start:]
        # Trim potential trailing code fences
        json_text = json_text.strip().rstrip('`')
        parsed = json.loads(json_text)
        items_out = parsed.get("items") if isinstance(parsed, dict) else parsed
        if not isinstance(items_out, list):
            return None
        # Normalize entries and ensure block_ids are in given list
        valid_ids = {b.id for b in blocks}
        out: List[Dict[str, Any]] = []
        for it in items_out:
            b_ids = [i for i in (it.get("block_ids") or []) if i in valid_ids]
            if not b_ids:
                continue
            out.append({
                "block_ids": b_ids,
                "question_number": (it.get("question_number") or "").strip(),
                "marks": (it.get("marks") or "").strip(),
                "qtype": (it.get("qtype") or "constructed").strip(),
                "has_table": any(next((bb for bb in blocks if bb.id == i and (bb.block_type == 'table')), None) for i in b_ids),
                "has_image": any(next((bb for bb in blocks if bb.id == i and ((bb.block_type == 'image') or bb.images.exists())), None) for i in b_ids),
            })
        return out or None
    except Exception as ex:
        logging.getLogger(__name__).warning("Ollama suggest failed: %s", ex)
        return None


def suggest_boxes_for_paper(paper: Paper) -> List[Dict[str, Any]]:
    """
    Returns a list of suggestions:
    [
      {
        'block_ids': [int, ...],       # contiguous region from header to next header-1
        'question_number': '1.1',
        'marks': '10',
        'qtype': 'constructed'|'mcq'|'case_study'|'table_q'|'image_q',
        'has_table': bool,
        'has_image': bool,
      }, ...
    ]

    Current implementation uses heuristics; future: use paper.system_prompt with an LLM.
    """
    # Ensure there is a system prompt to store on the paper for future use
    if not (paper.system_prompt or "").strip():
        paper.system_prompt = build_default_system_prompt()
        paper.save(update_fields=["system_prompt"])

    blocks = list(paper.blocks.order_by("order_index").prefetch_related("images"))

    # Try Ollama first; fallback to heuristics
    ollama_suggestions = _ollama_suggest(paper, blocks)
    if ollama_suggestions:
        return ollama_suggestions
    suggestions: List[Dict[str, Any]] = []

    cur_ids: List[int] = []
    cur_texts: List[str] = []
    cur_has_tbl = False
    cur_has_img = False
    cur_qnum = None
    cur_marks = None

    saw_any_header = False

    def flush():
        if not cur_ids:
            return
        # If we haven't seen any header yet and no question number, treat as cover page
        if not saw_any_header and not cur_qnum:
            qtype = "cover_page"
        else:
            qtype = _guess_qtype(cur_texts)
        suggestions.append(
            {
                "block_ids": list(cur_ids),
                "question_number": cur_qnum or "",
                "marks": cur_marks or "",
                "qtype": qtype,
                "has_table": bool(cur_has_tbl),
                "has_image": bool(cur_has_img),
            }
        )

    for b in blocks:
        text = (b.text or "").strip()
        det = detect_in_any_line(text)
        if det:
            # New header -> flush previous
            if cur_ids:
                flush()
                cur_ids.clear(); cur_texts.clear(); cur_has_tbl = False; cur_has_img = False
            num, marks = det
            cur_qnum = num
            cur_marks = marks or ""
            saw_any_header = True
        # Accumulate current
        cur_ids.append(b.id)
        if text:
            cur_texts.append(text)
        if b.block_type == "table":
            cur_has_tbl = True
        if b.block_type == "image" or b.images.exists():
            cur_has_img = True

    # tail
    flush()

    # Filter out degenerate suggestions (no qnum and very small set)
    cleaned: List[Dict[str, Any]] = []
    for s in suggestions:
        if not s.get("question_number") and len(s.get("block_ids", [])) <= 1:
            continue
        cleaned.append(s)

    return cleaned
