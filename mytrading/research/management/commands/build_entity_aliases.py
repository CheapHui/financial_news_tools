# research/management/commands/build_entity_aliases.py
from django.core.management.base import BaseCommand
from reference.models import Company, Industry
from research.models import IndustryPlayer
from django.core.cache import cache

def normalize(s: str) -> str:
    import re
    return re.sub(r"[^A-Z0-9]+", " ", (s or "").upper()).strip()

class Command(BaseCommand):
    help = "Build alias dictionary for entity linking and cache in Redis."

    def handle(self, *args, **opts):
        aliases = {}  # norm -> list of candidates
        def add(alias, objtype, objid, weight=1.0):
            k = normalize(alias)
            if not k: return
            aliases.setdefault(k, []).append((objtype, objid, weight))

        for c in Company.objects.all():
            add(c.ticker, "company", c.id, 2.0)
            add(c.name, "company", c.id, 1.5)
            # 你可加 c.aliases_json 裏的別名
        for ind in Industry.objects.all():
            add(ind.name, "industry", ind.id, 1.0)
        for p in IndustryPlayer.objects.select_related("company").all():
            if p.company_id:
                add(p.company.ticker, "industry_player", p.id, 1.5)
                add(p.company.name, "industry_player", p.id, 1.2)
            add(p.name, "industry_player", p.id, 1.0)

        cache.set("entity_aliases", aliases, timeout=24*3600)
        self.stdout.write(self.style.SUCCESS(f"Aliases cached: {len(aliases)} keys"))