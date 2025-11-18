#This helps to ensure that the node_type field of ExamNode
# is always set to one of the valid types before saving to the database.

from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import ExamNode

VALID_NODE_TYPES = {'question', 'table', 'image', 'case_study', 'instruction'}

@receiver(pre_save, sender=ExamNode)
def enforce_valid_node_type(sender, instance, **kwargs):
        """Ensure node_type is always one of the valid options."""
        if instance.node_type not in VALID_NODE_TYPES:
            instance.node_type = 'question'
