# Financial News Tools

A comprehensive Django-based trading infrastructure MVP for financial news analysis and vector search.

## Features

- **Django REST API** - RESTful API for financial data
- **Vector Search** - pgvector integration for semantic search
- **News Analysis** - AI-powered news embedding and analysis
- **Company Research** - Automated company profile generation
- **Financial Data** - Fundamental analysis and metrics
- **Multi-database Support** - PostgreSQL + pgvector, Redis, MinIO, Qdrant

## Architecture

### Services
- **PostgreSQL + pgvector** - Primary database with vector search capabilities (Port: 5433)
- **Redis** - Caching and Celery message broker (Port: 6380)
- **MinIO** - S3-compatible object storage (Port: 9000/9001)
- **Qdrant** - Vector database for advanced similarity search (Port: 6333/6334)

### Django Apps
- `reference` - Company, industry, sector reference data
- `news` - News articles and embeddings
- `research` - AI-generated company analysis
- `fundamentals` - Financial metrics and data
- `api` - REST API endpoints
- `ops` - Operational tools and monitoring

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/CheapHui/financial_news_tools.git
   cd financial_news_tools
   ```

2. **Start infrastructure services**
   ```bash
   make up
   ```

3. **Set up Python environment**
   ```bash
   pyenv local 3.11.9
   source .venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install "Django>=5.0" djangorestframework "psycopg[binary]" django-environ "celery[redis]" redis boto3 django-storages qdrant-client
   ```

5. **Run migrations**
   ```bash
   cd mytrading
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database
DB_NAME=mytrading
DB_USER=app
DB_PASSWORD=app
DB_HOST=127.0.0.1
DB_PORT=5433

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6380

# MinIO
AWS_ACCESS_KEY_ID=admin
AWS_SECRET_ACCESS_KEY=adminadmin
AWS_S3_ENDPOINT_URL=http://127.0.0.1:9000

# Qdrant
QDRANT_URL=http://127.0.0.1:6333
```

## Available Commands

```bash
# Infrastructure
make up              # Start all services
make down            # Stop all services
make restart         # Restart all services
make logs            # View service logs

# Database
make psql-docker     # Connect to PostgreSQL
make test-pgvector-docker  # Test vector functionality

# MinIO
make minio-console   # Open MinIO web interface
```

## API Endpoints

- `/admin/` - Django admin interface
- `/api/` - REST API endpoints
- Health checks and monitoring endpoints

## Development

### Project Structure
```
trading-infra-mvp/
├── docker-compose.yml    # Infrastructure services
├── Makefile             # Convenience commands
├── .env                 # Environment variables
├── mytrading/           # Django project
│   ├── mytrading/       # Project settings
│   ├── reference/       # Reference data models
│   ├── news/           # News and embeddings
│   ├── research/       # AI analysis
│   ├── fundamentals/   # Financial data
│   ├── api/           # REST API
│   └── ops/           # Operations
└── db/
    └── init/           # Database initialization
```

### Testing Vector Search

```python
from news.models import NewsEmbedding
import numpy as np

# Create a news embedding
embedding = NewsEmbedding.objects.create(
    model_name="test-model",
    dim=1024,
    vector=np.random.rand(1024).tolist()
)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions, please open a GitHub issue.
