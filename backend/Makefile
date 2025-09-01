SHELL := /bin/bash

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose down && docker compose up -d

logs:
	docker compose logs -f --tail=200

psql:
	PGPASSWORD=$${POSTGRES_PASSWORD:-app} psql -h 127.0.0.1 -p 5433 -U $${POSTGRES_USER:-app} -d $${POSTGRES_DB:-mytrading}

psql-docker:
	docker exec -it pgvector-db psql -U $${POSTGRES_USER:-app} -d $${POSTGRES_DB:-mytrading}

minio-console:
	open http://localhost:9001 || xdg-open http://localhost:9001 || true

test-pgvector:
	PGPASSWORD=$${POSTGRES_PASSWORD:-app} psql -h 127.0.0.1 -p 5433 -U $${POSTGRES_USER:-app} -d $${POSTGRES_DB:-mytrading} -c "SELECT id, title, embedding <#> '[0.9,0.8,0.1]'::vector AS cosine_dist FROM demo_vectors ORDER BY cosine_dist ASC;"

test-pgvector-docker:
	docker exec -it pgvector-db psql -U $${POSTGRES_USER:-app} -d $${POSTGRES_DB:-mytrading} -c "SELECT id, title, embedding <#> '[0.9,0.8,0.1]'::vector AS cosine_dist FROM demo_vectors ORDER BY cosine_dist ASC;"

# 檢查數據狀態
check-data:
	cd mytrading && python manage.py seed_reference_data --check

# 創建基本結構（不含具體公司數據）
create-structure:
	cd mytrading && python manage.py migrate
	cd mytrading && python manage.py seed_reference_data --create-basic

# 完全重置（清空並重建基本結構）
reset-data:
	cd mytrading && python manage.py migrate
	cd mytrading && python manage.py seed_reference_data --purge --create-basic

# 舊的 seed 命令（保持向後兼容，但建議使用新命令）
seed: reset-data

# 生成幾隻測試公司 AI 分析
ai-company:
	cd mytrading && python manage.py gen_company_ai --ticker TSM --industry "Semiconductors" --replace
	cd mytrading && python manage.py gen_company_ai --ticker NVDA --industry "Semiconductors" --replace
	cd mytrading && python manage.py gen_company_ai --ticker AAPL --industry "Consumer Electronics" --replace
	cd mytrading && python manage.py gen_company_ai --ticker MSFT --industry "Software" --replace

# 測試行業 ID 獲取 (不實際運行 AI 生成)
test-industry-ids:
	@echo "=== 測試行業 ID 獲取 ==="
	@cd mytrading && python manage.py shell -c "from reference.models import Industry; semiconductors = Industry.objects.filter(name='Semiconductors').first(); software = Industry.objects.filter(name__in=['Software', 'Software - Application']).first(); print(f'Semiconductors ID: {semiconductors.id if semiconductors else \"Not found\"}'); print(f'Software ID: {software.id if software else \"Not found\"}')"

# 生成行業 AI 分析 (動態獲取 industry ID)
ai-industry:
	@echo "=== 開始生成行業 AI 分析 ==="
	@echo "正在獲取 Semiconductors 行業 ID..."
	@SEMICONDUCTORS_ID=$$(cd mytrading && python manage.py shell -c "from reference.models import Industry; ind = Industry.objects.filter(name='Semiconductors').first(); print(ind.id if ind else '')"); \
	if [ "$$SEMICONDUCTORS_ID" != "" ]; then \
		echo "找到 Semiconductors (ID: $$SEMICONDUCTORS_ID)，開始生成..."; \
		cd mytrading && python manage.py gen_industry_ai --industry-id $$SEMICONDUCTORS_ID --replace || echo "Semiconductors AI 生成失敗，但繼續處理下一個"; \
	else \
		echo "警告: Semiconductors 行業未找到，跳過"; \
	fi
	@echo "正在獲取 Software 相關行業 ID..."
	@SOFTWARE_ID=$$(cd mytrading && python manage.py shell -c "from reference.models import Industry; ind = Industry.objects.filter(name__in=['Software', 'Software - Application']).first(); print(ind.id if ind else '')"); \
	if [ "$$SOFTWARE_ID" != "" ]; then \
		echo "找到 Software (ID: $$SOFTWARE_ID)，開始生成..."; \
		cd mytrading && python manage.py gen_industry_ai --industry-id $$SOFTWARE_ID --replace || echo "Software AI 生成失敗，但已完成"; \
	else \
		echo "警告: Software 行業未找到，跳過"; \
	fi
	@echo "=== 行業 AI 分析生成完成 ==="

# 創建基礎公司數據
create-companies:
	cd mytrading && python manage.py shell -c "from reference.models import Company, Industry, Sector; semiconductors = Industry.objects.filter(name='Semiconductors').first(); consumer_electronics = Industry.objects.filter(name='Consumer Electronics').first(); software = Industry.objects.filter(name__in=['Software', 'Software - Application']).first(); tech_sector = Sector.objects.filter(name='Technology').first(); companies = [{'ticker': 'TSM', 'name': 'Taiwan Semiconductor Manufacturing Company Limited', 'industry': semiconductors}, {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'industry': semiconductors}, {'ticker': 'AAPL', 'name': 'Apple Inc.', 'industry': consumer_electronics}, {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'industry': software}]; [Company.objects.get_or_create(ticker=comp['ticker'], defaults={'name': comp['name'], 'industry': comp['industry'], 'sector': tech_sector, 'country': 'US', 'is_active': True}) for comp in companies]; print('基礎公司數據創建完成')"

# 一鍵全自動：Seed + 創建公司 + 生成公司 + 行業
init-all: seed create-companies ai-company ai-industry

news-ingest:
	cd mytrading && python manage.py ingest_rss --max 40

news-embed:
	cd mytrading && python manage.py embed_news --days-back 7 --limit 500

news-full: news-ingest news-embed

emb-research:
	cd mytrading && python manage.py build_research_embeddings --overwrite

emb-research-fast:
	cd mytrading && python manage.py build_research_embeddings --limit 200

aliases:
	cd mytrading && python manage.py build_entity_aliases

link-news:
	cd mytrading && python manage.py link_news_entities --days-back 7 --limit 800

# 信號聚合相關命令
rollup-signals:
	cd mytrading && python manage.py rollup_signals --days-back 7 --window-days 7 --include-industry-signal

rollup-signals-fast:
	cd mytrading && python manage.py rollup_signals --days-back 3 --window-days 3 --topk-per-chunk 3 --include-industry-signal

rollup-signals-full:
	cd mytrading && python manage.py rollup_signals --days-back 14 --window-days 7 --topk-per-chunk 10 --min-sim 0.3 --include-industry-signal --overwrite

# 完整的新聞處理流水線 (新聞攝取 → 嵌入 → 實體連結 → 信號聚合)
news-pipeline: news-full link-news rollup-signals

celery-up:
	docker compose up -d celery-worker celery-beat

celery-logs:
	docker compose logs -f celery-worker celery-beat

metrics:
	curl -s http://localhost:8000/api/metrics/summary | jq .

start-server:
	cd mytrading && python manage.py runserver 0.0.0.0:8001

start-frontend:
	cd .. && cd frontend && npm run dev

# 新聞分數相關命令
news-score:
	cd mytrading && python manage.py score_news --since-hours 24 --model deepseek-reasoner --half-life 72

rollup-news-score-signals:
	cd mytrading && python manage.py rollup_signals --lookback-hours 168 --apply-overall-when-missing

# 新聞分數完整流水線 (分數 → 聚合)
news-score-pipeline:
	cd mytrading && python manage.py process_news_pipeline --since-hours 24 --model deepseek-reasoner --half-life 72 --lookback-hours 168 --apply-overall-when-missing

# 研究匹配完整流水線 (攝取 → 嵌入 → 連結 → 聚合)
news-research-pipeline: news-full link-news rollup-signals

# 完整新聞分析流水線命令（包含新聞攝取）
full-pipeline:
	cd mytrading && python manage.py process_news_pipeline --max-news 40 --since-hours 24 --lookback-hours 168 --apply-overall-when-missing --verbose

full-pipeline-fast:
	cd mytrading && python manage.py process_news_pipeline --max-news 20 --since-hours 12 --lookback-hours 72 --apply-overall-when-missing

full-pipeline-skip-reco:
	cd mytrading && python manage.py process_news_pipeline --max-news 40 --since-hours 24 --lookback-hours 168 --apply-overall-when-missing --skip-recommendations --verbose

full-pipeline-no-ingest:
	cd mytrading && python manage.py process_news_pipeline --skip-ingest --since-hours 24 --lookback-hours 168 --apply-overall-when-missing --verbose

# 舊的命令別名（向後兼容）
recommendations: full-pipeline