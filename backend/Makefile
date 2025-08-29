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

# 一鍵全自動：Seed + 生成公司 + 行業
init-all: seed ai-company ai-industry

news-ingest:
	cd mytrading && python manage.py ingest_rss --max 40

news-embed:
	cd mytrading && python manage.py embed_news --days-back 7 --limit 500

news-full: news-ingest news-embed

emb-research:
	python manage.py build_research_embeddings --overwrite

emb-research-fast:
	python manage.py build_research_embeddings --limit 200

aliases:
	cd mytrading && python manage.py build_entity_aliases

link-news:
	cd mytrading && python manage.py link_news_entities --days-back 7 --limit 800