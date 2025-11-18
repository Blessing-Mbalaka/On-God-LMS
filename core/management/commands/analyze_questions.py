from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch
import re

from core.models import ExtractorPaper as Paper


class Command(BaseCommand):
    help = "Analyze a Paper's blocks and print proposed question delimiters using robust heuristics"

    def add_arguments(self, parser):
        parser.add_argument("paper_id", type=int, help="ID of the Paper to analyze")

    def handle(self, *args, **options):
        try:
            paper = Paper.objects.get(id=options["paper_id"])
        except Paper.DoesNotExist:
            raise CommandError(f"Paper {options['paper_id']} not found")

        blocks = (
            paper.blocks.select_related()
            .prefetch_related("images")
            .order_by("order_index")
        )

        # Heuristics similar to robustexamextractor
        q_re = re.compile(
            r"^(?:question\s*|q\s*)?(\d+(?:[\.\-]\d+)*[A-Z]?|\d+[A-Z]|\d+)(?:\s*[:)\.-]?\s*)",
            re.IGNORECASE,
        )
        marks_re = re.compile(r"(\d+)\s*marks?", re.IGNORECASE)

        def is_q_header(text: str):
            t = (text or "").strip()
            if not t:
                return None
            m = q_re.match(t)
            if not m:
                return None
            num = m.group(1).strip().rstrip(".-")
            return num

        def plain(text: str) -> str:
            # crude HTML strip; ok for detection
            if not text:
                return ""
            return re.sub(r"<[^>]+>", " ", text)

        current = None
        groups = []

        self.stdout.write(self.style.NOTICE(f"Analyzing Paper {paper.id}: {paper.title}"))
        for b in blocks:
            src_text = b.text
            if b.block_type == "table":
                src_text = plain(src_text)
            header = is_q_header(src_text)
            if header:
                if current is not None:
                    groups.append(current)
                # detect marks in same line if present
                mm = marks_re.search(src_text or "")
                current = {
                    "q": header,
                    "marks": mm.group(1) if mm else None,
                    "start_block_id": b.id,
                    "items": [],
                }
            # always append block to current group if one exists
            if current is None:
                # preamble bucket with q = None
                current = {
                    "q": None,
                    "marks": None,
                    "start_block_id": b.id,
                    "items": [],
                }
            current["items"].append({
                "id": b.id,
                "type": b.block_type,
                "sample": (src_text or "").strip()[:120],
            })

        if current is not None:
            groups.append(current)

        # Print nicely
        for idx, g in enumerate(groups, 1):
            if g["q"] is None:
                self.stdout.write(self.style.HTTP_INFO(f"-- Preamble ({len(g['items'])} blocks)"))
            else:
                label = f"Question {g['q']}"
                if g["marks"]:
                    label += f" ({g['marks']} marks)"
                self.stdout.write(self.style.SUCCESS(f"-- {label} — start block {g['start_block_id']}"))
            for it in g["items"][:5]:  # show first few for context
                self.stdout.write(f"   [{it['type']}] {it['sample']}")
            if len(g["items"]) > 5:
                self.stdout.write(f"   … +{len(g['items']) - 5} more")

        self.stdout.write(self.style.SUCCESS(f"Proposed groups: {len(groups)}"))

