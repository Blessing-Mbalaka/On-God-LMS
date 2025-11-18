# exam_extractor/utils/llm_autoclassify.py
from core.models import ExtractorBlock as Block
import re

def classify_blocks_llm(paper, max_passes=3, include_instructions=False):
    """
    Placeholder:
    - merge 'heading' + following 'paragraph' if header lines like 'Question 1.1'
    - tag paragraphs starting with '1.' or '1.1.' as 'instruction' vs 'paragraph'
    - (Future) call an LLM with the block list & raw XML to propose q-boundaries
    """
    blocks = list(paper.blocks.order_by("order_index"))
    instr_kw = re.compile(r"^(instructions?\b|read\s+all\s+instructions?|answer\s+all\s+questions)\b", re.IGNORECASE)
    for _ in range(max_passes):
        changed = False
        for i, b in enumerate(blocks):
            t = (b.text or "").strip()
            # Heuristic: question header pattern
            if t and t.split()[0].rstrip(".").replace(".", "").isdigit():
                if b.block_type == "paragraph":
                    b.block_type = "heading"
                    b.save(update_fields=["block_type"])
                    changed = True
            # Optional: classify instructions blocks
            if include_instructions and b.block_type in ("paragraph", "heading"):
                if instr_kw.match(t) or t.upper() == "INSTRUCTIONS":
                    if b.block_type != "instruction":
                        b.block_type = "instruction"
                        b.save(update_fields=["block_type"])
                        changed = True
        if not changed:
            break
    return True
