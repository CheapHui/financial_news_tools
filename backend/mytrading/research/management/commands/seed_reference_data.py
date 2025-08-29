# research/management/commands/seed_reference_data.py
from django.core.management.base import BaseCommand
from django.db import transaction
from reference.models import Sector, Industry, Company

class Command(BaseCommand):
    help = "管理參考數據。使用 --purge 清空現有數據，--check 檢查數據狀態，--create-basic 創建基本結構"

    def add_arguments(self, parser):
        parser.add_argument("--purge", action="store_true", help="清空所有現有參考數據")
        parser.add_argument("--check", action="store_true", help="檢查當前數據狀態")
        parser.add_argument("--create-basic", action="store_true", help="僅創建基本的 Sector/Industry 結構（不含公司數據）")

    def handle(self, *args, **opts):
        purge = opts["purge"]
        check = opts["check"]
        create_basic = opts["create_basic"]

        # 檢查數據狀態
        if check or not any([purge, create_basic]):
            self.check_data_status()
            return

        # 清空數據
        if purge:
            self.purge_data()

        # 創建基本結構
        if create_basic:
            self.create_basic_structure()

    def check_data_status(self):
        """檢查當前數據狀態"""
        company_count = Company.objects.count()
        industry_count = Industry.objects.count()
        sector_count = Sector.objects.count()

        self.stdout.write(self.style.SUCCESS("=== 當前數據狀態 ==="))
        self.stdout.write(f"公司 (Companies): {company_count}")
        self.stdout.write(f"行業 (Industries): {industry_count}")
        self.stdout.write(f"板塊 (Sectors): {sector_count}")

        if sector_count > 0:
            self.stdout.write("\n=== 板塊詳情 ===")
            for sector in Sector.objects.all():
                industry_count_in_sector = sector.industries.count()
                company_count_in_sector = Company.objects.filter(sector=sector).count()
                self.stdout.write(f"  {sector.name}: {industry_count_in_sector} 個行業, {company_count_in_sector} 家公司")

        if company_count == 0:
            self.stdout.write(self.style.WARNING("\n提示: 目前沒有公司數據，可以運行 research_pipeline.py 來導入公司數據"))

    @transaction.atomic
    def purge_data(self):
        """清空所有參考數據"""
        self.stdout.write(self.style.WARNING("正在清空現有參考數據..."))
        
        company_count = Company.objects.count()
        industry_count = Industry.objects.count()
        sector_count = Sector.objects.count()
        
        Company.objects.all().delete()
        Industry.objects.all().delete()
        Sector.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS(
            f"已清空: {company_count} 家公司, {industry_count} 個行業, {sector_count} 個板塊"
        ))

    @transaction.atomic
    def create_basic_structure(self):
        """創建基本的板塊和行業結構，不包含具體公司數據"""
        self.stdout.write("正在創建基本結構...")
        
        # 基本板塊和行業結構（不含公司）
        basic_structure = {
            "Technology": [
                "Semiconductors",
                "Software",
                "Software - Application", 
                "Software - Infrastructure",
                "Consumer Electronics",
                "Communication Equipment",
                "Semiconductor Equipment & Materials",
                "Information Technology Services",
            ],
            "Healthcare": [
                "Drug Manufacturers - General",
                "Medical Devices", 
                "Healthcare Plans",
            ],
            "Financial Services": [
                "Banks - Diversified",
                "Credit Services",
                "Capital Markets",
                "Asset Management",
                "Insurance - Diversified",
            ],
            "Consumer Cyclical": [
                "Internet Retail",
                "Home Improvement Retail",
                "Restaurants",
                "Auto Manufacturers",
            ],
            "Consumer Defensive": [
                "Discount Stores",
                "Beverages - Non-Alcoholic",
                "Household & Personal Products",
                "Tobacco",
            ],
            "Communication Services": [
                "Interactive Entertainment",
                "Entertainment",
                "Internet Content & Information",
                "Telecom Services",
            ],
            "Industrials": [
                "Farm & Heavy Construction Machinery",
                "Aerospace & Defense",
            ],
            "Energy": [
                "Oil & Gas Integrated",
            ],
            "Basic Materials": [
                "Specialty Chemicals",
            ],
        }

        created_counts = {"sectors": 0, "industries": 0}

        for sector_name, industries in basic_structure.items():
            sector, s_created = Sector.objects.get_or_create(
                name=sector_name, 
                defaults={"source": "custom"}
            )
            created_counts["sectors"] += int(s_created)

            for industry_name in industries:
                industry, i_created = Industry.objects.get_or_create(
                    name=industry_name,
                    defaults={"sector": sector}
                )
                if industry.sector_id != sector.id:
                    industry.sector = sector
                    industry.save(update_fields=["sector"])
                created_counts["industries"] += int(i_created)

        self.stdout.write(self.style.SUCCESS(
            f"基本結構創建完成: 新增 {created_counts['sectors']} 個板塊, {created_counts['industries']} 個行業"
        ))