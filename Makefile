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

seed:
	python manage.py migrate
	python manage.py seed_reference_data --purge

# 生成幾隻測試公司 AI 分析
ai-company:
	python manage.py gen_company_ai --ticker TSM --industry "Semiconductors" --replace
	python manage.py gen_company_ai --ticker NVDA --industry "Semiconductors" --replace
	python manage.py gen_company_ai --ticker AAPL --industry "Consumer Electronics" --replace
	python manage.py gen_company_ai --ticker MSFT --industry "Software" --replace

# 生成行業 AI 分析 (需先查 TablePlus 搵 industry id)
# Example: 假設 Semiconductors id=1, Software id=2
ai-industry:
	python manage.py gen_industry_ai --industry-id 1 --replace
	python manage.py gen_industry_ai --industry-id 2 --replace

# 一鍵全自動：Seed + 生成公司 + 行業
init-all: seed ai-company ai-industry