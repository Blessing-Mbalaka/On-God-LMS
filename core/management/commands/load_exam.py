import os
import json, pathlib
from django.core.management.base import BaseCommand
from models import ExamNode
from add_ids import ensure_ids   #  ← your helper in PYTHONPATH

class Command(BaseCommand):
    help = "Import a JSON exam tree (with IDs) into ExamNode rows"

    def add_arguments(self, parser):
        parser.add_argument('path', help='Path to the JSON file')

    def handle(self, *args, **opts):
        data = json.loads(pathlib.Path(opts['path']).read_text())
        ensure_ids(data)                      # belt & braces

        def upsert(node, parent_id=None):
            _id = node['id']
            ExamNode.objects.update_or_create(
                id=_id,
                defaults=dict(
                    parent_id = parent_id,
                    node_type = node.get('type', 'root'),
                    number    = node.get('number', ''),
                    marks     = node.get('marks', ''),
                    payload   = node,          # full blob
                )
            )
            for child in node.get('children', []):
                upsert(child, _id)

        upsert(data)
        self.stdout.write(self.style.SUCCESS('Import complete'))
