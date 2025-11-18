from __future__ import annotations

import re
from typing import Dict
from django.db import transaction

from core.models import ExtractorPaper as Paper, ExtractorBlock as Block


# Patterns that typically start assessor-only rubric/mark allocation sections
RUBRIC_START_RE = re.compile(
    r"(^|\n)\s*(?:mark\s*allocation|allocation\s*of\s*marks|rubric|assessment\s*rubric)\s*:?.*$",
    re.IGNORECASE | re.MULTILINE,
)


def delimit_rubric_sections(paper: Paper) -> Dict[str, int]:
    """Split trailing rubric/mark allocation text into its own 'rubric' Block.

    - Looks for the last occurrence of a rubric start within a text block and
      splits the block at that position.
    - The trailing part becomes a new Block with block_type='rubric'.
    - The original block text is truncated to exclude the rubric.

    Returns: {"split": N}
    """
    split_count = 0
    with transaction.atomic():
        # Load as list to manage order_index shifts safely
        blocks = list(paper.blocks.order_by("order_index"))
        i = 0
        while i < len(blocks):
            b = blocks[i]
            if b.block_type in ("image", "table"):
                i += 1
                continue
            text = (b.text or "").strip()
            if not text:
                i += 1
                continue
            # Find last rubric marker in the text
            matches = list(RUBRIC_START_RE.finditer(text))
            if not matches:
                i += 1
                continue
            m = matches[-1]
            start = m.start(0)
            rubric_text = text[start:].strip()
            main_text = text[:start].rstrip()
            # Require both parts to be non-trivial
            if not rubric_text or len(rubric_text) < 4:
                i += 1
                continue
            if not main_text:
                i += 1
                continue

            # Shift subsequent order_index by +1 to insert rubric block after b
            for j in range(i + 1, len(blocks)):
                bj = blocks[j]
                bj.order_index = (bj.order_index or 0) + 1
                bj.save(update_fields=["order_index"])

            # Update current block text
            b.text = main_text
            b.save(update_fields=["text"])

            # Insert rubric block in-memory list and DB
            rubric_block = Block.objects.create(
                paper=paper,
                order_index=(b.order_index or 0) + 1,
                block_type="rubric",
                xml="",
                text=rubric_text,
            )
            blocks.insert(i + 1, rubric_block)
            split_count += 1

            # Skip past the inserted rubric
            i += 2
    return {"split": split_count}

