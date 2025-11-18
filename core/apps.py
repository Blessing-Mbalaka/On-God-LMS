from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from . import qualification_registry

        def sync_registry(sender, **kwargs):
            qualification_registry.sync_registry_to_db()

        post_migrate.connect(sync_registry, sender=self)