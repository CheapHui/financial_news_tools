from django.core.management.base import BaseCommand
from reference.models import Company, Industry, Sector
from decimal import Decimal

class Command(BaseCommand):
    help = "添加美國最大的25間公司和主要10大行業到數據庫"

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true", help="更新現有數據")

    def handle(self, *args, **opts):
        self.stdout.write(self.style.SUCCESS("開始添加美國公司和行業數據..."))
        
        # 1. 創建主要行業分類
        sectors_data = [
            {"name": "Technology", "source": "GICS"},
            {"name": "Healthcare", "source": "GICS"},
            {"name": "Financial Services", "source": "GICS"},
            {"name": "Consumer Discretionary", "source": "GICS"},
            {"name": "Communication Services", "source": "GICS"},
            {"name": "Industrials", "source": "GICS"},
            {"name": "Consumer Staples", "source": "GICS"},
            {"name": "Energy", "source": "GICS"},
            {"name": "Utilities", "source": "GICS"},
            {"name": "Real Estate", "source": "GICS"},
        ]
        
        sectors = {}
        for sector_data in sectors_data:
            sector, created = Sector.objects.get_or_create(
                name=sector_data["name"],
                defaults={"source": sector_data["source"]}
            )
            sectors[sector.name] = sector
            if created:
                self.stdout.write(f"  ✅ 創建行業分類: {sector.name}")
            else:
                self.stdout.write(f"  📝 行業分類已存在: {sector.name}")
        
        # 2. 創建細分行業
        industries_data = [
            {"name": "Software", "sector": "Technology"},
            {"name": "Semiconductors", "sector": "Technology"},
            {"name": "Cloud Computing", "sector": "Technology"},
            {"name": "Biotechnology", "sector": "Healthcare"},
            {"name": "Pharmaceuticals", "sector": "Healthcare"},
            {"name": "Investment Banking", "sector": "Financial Services"},
            {"name": "Insurance", "sector": "Financial Services"},
            {"name": "E-commerce", "sector": "Consumer Discretionary"},
            {"name": "Automotive", "sector": "Consumer Discretionary"},
            {"name": "Social Media", "sector": "Communication Services"},
        ]
        
        industries = {}
        for industry_data in industries_data:
            industry, created = Industry.objects.get_or_create(
                name=industry_data["name"],
                defaults={"sector": sectors[industry_data["sector"]]}
            )
            industries[industry.name] = industry
            if created:
                self.stdout.write(f"  ✅ 創建細分行業: {industry.name}")
            else:
                self.stdout.write(f"  📝 細分行業已存在: {industry.name}")
        
        # 3. 添加美國最大的25間公司（按市值排序，2024年數據）
        companies_data = [
            # 科技股
            {"ticker": "AAPL", "name": "Apple Inc.", "market_cap": 3500000000000, "industry": "Software", "exchange": "NASDAQ"},
            {"ticker": "MSFT", "name": "Microsoft Corporation", "market_cap": 3200000000000, "industry": "Software", "exchange": "NASDAQ"},
            {"ticker": "GOOGL", "name": "Alphabet Inc. Class A", "market_cap": 2100000000000, "industry": "Software", "exchange": "NASDAQ"},
            {"ticker": "AMZN", "name": "Amazon.com Inc.", "market_cap": 1800000000000, "industry": "E-commerce", "exchange": "NASDAQ"},
            {"ticker": "NVDA", "name": "NVIDIA Corporation", "market_cap": 1700000000000, "industry": "Semiconductors", "exchange": "NASDAQ"},
            {"ticker": "META", "name": "Meta Platforms Inc.", "market_cap": 1300000000000, "industry": "Social Media", "exchange": "NASDAQ"},
            {"ticker": "TSLA", "name": "Tesla Inc.", "market_cap": 800000000000, "industry": "Automotive", "exchange": "NASDAQ"},
            {"ticker": "TSM", "name": "Taiwan Semiconductor Manufacturing", "market_cap": 500000000000, "industry": "Semiconductors", "exchange": "NYSE"},
            {"ticker": "AVGO", "name": "Broadcom Inc.", "market_cap": 600000000000, "industry": "Semiconductors", "exchange": "NASDAQ"},
            {"ticker": "ORCL", "name": "Oracle Corporation", "market_cap": 400000000000, "industry": "Software", "exchange": "NYSE"},
            
            # 金融股
            {"ticker": "BRK.B", "name": "Berkshire Hathaway Inc. Class B", "market_cap": 900000000000, "industry": "Investment Banking", "exchange": "NYSE"},
            {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "market_cap": 550000000000, "industry": "Investment Banking", "exchange": "NYSE"},
            {"ticker": "V", "name": "Visa Inc.", "market_cap": 500000000000, "industry": "Financial Services", "exchange": "NYSE"},
            {"ticker": "MA", "name": "Mastercard Incorporated", "market_cap": 400000000000, "industry": "Financial Services", "exchange": "NYSE"},
            {"ticker": "BAC", "name": "Bank of America Corporation", "market_cap": 300000000000, "industry": "Investment Banking", "exchange": "NYSE"},
            
            # 醫療保健
            {"ticker": "UNH", "name": "UnitedHealth Group Incorporated", "market_cap": 550000000000, "industry": "Insurance", "exchange": "NYSE"},
            {"ticker": "JNJ", "name": "Johnson & Johnson", "market_cap": 450000000000, "industry": "Pharmaceuticals", "exchange": "NYSE"},
            {"ticker": "PFE", "name": "Pfizer Inc.", "market_cap": 200000000000, "industry": "Pharmaceuticals", "exchange": "NYSE"},
            {"ticker": "ABBV", "name": "AbbVie Inc.", "market_cap": 300000000000, "industry": "Biotechnology", "exchange": "NYSE"},
            {"ticker": "LLY", "name": "Eli Lilly and Company", "market_cap": 700000000000, "industry": "Pharmaceuticals", "exchange": "NYSE"},
            
            # 消費品
            {"ticker": "PG", "name": "Procter & Gamble Company", "market_cap": 380000000000, "industry": "Consumer Staples", "exchange": "NYSE"},
            {"ticker": "KO", "name": "Coca-Cola Company", "market_cap": 270000000000, "industry": "Consumer Staples", "exchange": "NYSE"},
            {"ticker": "PEP", "name": "PepsiCo Inc.", "market_cap": 250000000000, "industry": "Consumer Staples", "exchange": "NASDAQ"},
            
            # 能源
            {"ticker": "XOM", "name": "Exxon Mobil Corporation", "market_cap": 450000000000, "industry": "Energy", "exchange": "NYSE"},
            {"ticker": "CVX", "name": "Chevron Corporation", "market_cap": 350000000000, "industry": "Energy", "exchange": "NYSE"},
        ]
        
        added_companies = 0
        updated_companies = 0
        
        for company_data in companies_data:
            industry = industries.get(company_data["industry"])
            if not industry:
                self.stderr.write(f"警告: 找不到行業 {company_data['industry']} for {company_data['ticker']}")
                continue
            
            company, created = Company.objects.get_or_create(
                ticker=company_data["ticker"],
                defaults={
                    "name": company_data["name"],
                    "market_cap": company_data["market_cap"],
                    "industry": industry,
                    "sector": industry.sector,
                    "exchange": company_data["exchange"],
                    "country": "US",
                    "is_active": True,
                }
            )
            
            if created:
                added_companies += 1
                self.stdout.write(f"  ✅ 添加公司: {company.ticker} - {company.name}")
            elif opts["update"]:
                company.name = company_data["name"]
                company.market_cap = company_data["market_cap"]
                company.industry = industry
                company.sector = industry.sector
                company.exchange = company_data["exchange"]
                company.is_active = True
                company.save()
                updated_companies += 1
                self.stdout.write(f"  🔄 更新公司: {company.ticker} - {company.name}")
            else:
                self.stdout.write(f"  📝 公司已存在: {company.ticker} - {company.name}")
        
        # 統計
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("數據添加完成！"))
        self.stdout.write(f"行業分類: {len(sectors_data)} 個")
        self.stdout.write(f"細分行業: {len(industries_data)} 個")
        self.stdout.write(f"新增公司: {added_companies} 間")
        if opts["update"]:
            self.stdout.write(f"更新公司: {updated_companies} 間")
        self.stdout.write(f"總公司數: {Company.objects.count()} 間")
        self.stdout.write("="*50)
