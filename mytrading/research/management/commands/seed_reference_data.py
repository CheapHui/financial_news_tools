# research/management/commands/seed_reference_data.py
from django.core.management.base import BaseCommand
from django.db import transaction
from reference.models import Sector, Industry, Company

DEFAULT_DATA = {
    "Technology": {
        "Semiconductors": [
            # ticker, name, country(optional), exchange(optional)
            ("TSM", "Taiwan Semiconductor Manufacturing Company", "TW", "NYSE"),
            ("NVDA", "NVIDIA Corporation", "US", "NASDAQ"),
            ("ASML", "ASML Holding N.V.", "NL", "NASDAQ"),
            ("AMD", "Advanced Micro Devices, Inc.", "US", "NASDAQ"),
        ],
        "Software": [
            ("MSFT", "Microsoft Corporation", "US", "NASDAQ"),
            ("ADBE", "Adobe Inc.", "US", "NASDAQ"),
        ],
        "Consumer Electronics": [
            ("AAPL", "Apple Inc.", "US", "NASDAQ"),
        ],
    },
    "Communication Services": {
        "Interactive Entertainment": [
            ("0700.HK", "Tencent Holdings Ltd", "CN", "HKEX"),
        ]
    },
}

class Command(BaseCommand):
    help = "Seed basic Sectors / Industries / Companies. Use --purge to wipe existing reference tables first."

    def add_arguments(self, parser):
        parser.add_argument("--purge", action="store_true", help="Delete all existing reference data before seeding")
        parser.add_argument("--minimal", action="store_true", help="Only seed a minimal set (TSM/NVDA/AAPL/MSFT)")

    @transaction.atomic
    def handle(self, *args, **opts):
        purge = opts["purge"]
        minimal = opts["minimal"]

        if purge:
            self.stdout.write(self.style.WARNING("Purging existing reference data..."))
            Company.objects.all().delete()
            Industry.objects.all().delete()
            Sector.objects.all().delete()

        data = DEFAULT_DATA
        if minimal:
            data = {
                "Technology": {
                    "Semiconductors": [
                        ("TSM", "Taiwan Semiconductor Manufacturing Company", "TW", "NYSE"),
                        ("NVDA", "NVIDIA Corporation", "US", "NASDAQ"),
                    ],
                    "Software": [("MSFT", "Microsoft Corporation", "US", "NASDAQ")],
                    "Consumer Electronics": [("AAPL", "Apple Inc.", "US", "NASDAQ")],
                }
            }

        created_counts = {"sectors": 0, "industries": 0, "companies": 0}

        for sector_name, inds in data.items():
            sector, s_created = Sector.objects.get_or_create(name=sector_name, defaults={"source": "custom"})
            created_counts["sectors"] += int(s_created)

            for ind_name, companies in inds.items():
                industry, i_created = Industry.objects.get_or_create(name=ind_name, defaults={"sector": sector})
                if industry.sector_id != sector.id:
                    industry.sector = sector
                    industry.save(update_fields=["sector"])
                created_counts["industries"] += int(i_created)

                for ticker, name, *rest in companies:
                    country = rest[0] if len(rest) > 0 else "US"
                    exchange = rest[1] if len(rest) > 1 else ""
                    company, c_created = Company.objects.get_or_create(
                        ticker=ticker,
                        defaults={
                            "name": name,
                            "exchange": exchange,
                            "country": country,
                            "sector": sector,
                            "industry": industry,
                            "is_active": True,
                        },
                    )
                    # 若已存在但未關聯 sector/industry，就補上
                    changed = False
                    if company.sector_id != sector.id:
                        company.sector = sector
                        changed = True
                    if company.industry_id != industry.id:
                        company.industry = industry
                        changed = True
                    if changed:
                        company.save(update_fields=["sector", "industry"])
                    created_counts["companies"] += int(c_created)

        self.stdout.write(self.style.SUCCESS(
            f"Seed done. Sectors(+{created_counts['sectors']}), "
            f"Industries(+{created_counts['industries']}), Companies(+{created_counts['companies']})."
        ))