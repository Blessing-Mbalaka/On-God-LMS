from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core.models import ExtractorPaper as Paper
from ...utils.bank import pick_random_for_qnums, build_test_from_boxes


class Command(BaseCommand):
    help = "Generate a randomized test based on a module and an existing paper's question numbers"

    def add_arguments(self, parser):
        parser.add_argument('--module', required=False, help='Module name to sample from. Defaults to paper.module_name')
        parser.add_argument('--paper', type=int, required=True, help='Paper ID to take question_numbers from')
        parser.add_argument('--title', required=False, default='', help='Test title override')

    def handle(self, *args, **opts):
        paper_id = opts['paper']
        try:
            paper = Paper.objects.get(id=paper_id)
        except Paper.DoesNotExist:
            raise CommandError(f"Paper {paper_id} not found")

        module = opts['module'] or paper.module_name
        if not module:
            raise CommandError('Module name is required (either on paper or via --module)')

        qnums = list(
            paper.user_boxes.filter(qtype='question').order_by('order_index').values_list('question_number', flat=True)
        )
        if not qnums:
            raise CommandError('No question boxes found on the given paper')

        boxes = pick_random_for_qnums(module, qnums)
        if not boxes:
            raise CommandError('No matching boxes found in bank for the selected module')

        title = opts['title'] or f"Randomized Test - {module}"
        test = build_test_from_boxes(module, title, boxes)
        self.stdout.write(self.style.SUCCESS(f"Created TestPaper id={test.id}. View at /test/{test.id}/"))

