# research/management/commands/list_embeddings.py
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db.models import Count

class Command(BaseCommand):
    help = "List count of embeddings grouped by object_type"

    def handle(self, *args, **opts):
        # 動態讀取 embeddings model，設定需於 settings.py 定義
        from django.conf import settings
        path = getattr(settings, "EMBEDDINGS_MODEL", None)
        if not path:
            self.stderr.write(self.style.ERROR(
                "Please set EMBEDDINGS_MODEL in settings.py (e.g. research.ResearchEmbedding)"
            ))
            return

        try:
            app_label, model_name = path.split(".")
            Emb = apps.get_model(app_label, model_name)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Cannot load model {path}: {e}"))
            return

        qs = Emb.objects.values('object_type').annotate(total=Count('id')).order_by('object_type')
        if not qs:
            self.stdout.write(self.style.WARNING("No embeddings found."))
            return

        self.stdout.write(self.style.SUCCESS("Embedding counts by object_type:"))
        for row in qs:
            obj_type = row['object_type']
            count = row['total']
            self.stdout.write(f"  • {obj_type}: {count}")