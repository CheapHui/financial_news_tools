import os, time, uuid, json, traceback
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connection
from pgvector.django import CosineDistance
from ops.models import VectorProbe

# （可選）Qdrant
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    HAS_QDRANT = True
except Exception:
    HAS_QDRANT = False

class Command(BaseCommand):
    help = "Check Postgres(pgvector), Redis(cache), MinIO(storage), (optional) Qdrant."

    def handle(self, *args, **opts):
        results = {
            "postgres_pgvector": self.check_pgvector(),
            "redis_cache": self.check_redis(),
            "minio_storage": self.check_minio(),
        }
        if HAS_QDRANT and os.getenv("QDRANT_URL"):
            results["qdrant"] = self.check_qdrant()
        self.stdout.write(self.style.SUCCESS(json.dumps(results, indent=2, ensure_ascii=False)))

    # 1) Postgres + pgvector
    def check_pgvector(self):
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT extname FROM pg_extension WHERE extname='vector';")
                if not cur.fetchone():
                    return {"ok": False, "error": "pgvector extension not found (CREATE EXTENSION vector)"}

            # 清理舊數
            VectorProbe.objects.all().delete()
            VectorProbe.objects.bulk_create([
                VectorProbe(title="A", vector=[1,0,0]),
                VectorProbe(title="B", vector=[0,1,0]),
                VectorProbe(title="C", vector=[0,0,1]),
            ])
            qv = [0.9, 0.8, 0.1]
            hits = list(
                VectorProbe.objects
                .order_by(CosineDistance("vector", qv))
                .values_list("title", flat=True)
            )
            return {"ok": True, "nearest_order": hits}
        except Exception as e:
            return {"ok": False, "error": f"{e}", "trace": traceback.format_exc()}

    # 2) Redis（Django Cache）
    def check_redis(self):
        try:
            key = f"infra:redis:{uuid.uuid4().hex[:8]}"
            cache.set(key, "pong", timeout=30)
            val = cache.get(key)
            return {"ok": val == "pong", "value": val}
        except Exception as e:
            return {"ok": False, "error": f"{e}", "trace": traceback.format_exc()}

    # 3) MinIO（django-storages + boto3）
    def check_minio(self):
        try:
            # 先確保 bucket 存在（用 boto3 直接建立；若已存在會報錯，忽略即可）
            import boto3
            bucket = os.getenv("AWS_STORAGE_BUCKET_NAME", "news-raw")
            s3 = boto3.client(
                "s3",
                endpoint_url=os.getenv("AWS_S3_ENDPOINT_URL"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_S3_REGION_NAME", "us-east-1"),
            )
            try:
                s3.head_bucket(Bucket=bucket)
            except Exception:
                # 可能未建立；嘗試建立
                try:
                    s3.create_bucket(Bucket=bucket)
                except Exception:
                    pass  # 若有權限/設定限制，交由現有 bucket

            # 用 django default_storage 上傳/讀取/刪除
            key = f"health/{uuid.uuid4().hex}.txt"
            content = b"hello from django+minio"
            default_storage.save(key, ContentFile(content))
            url = default_storage.url(key)
            # 讀回（有啲設定不可直接讀；這步非必須）
            # default_storage.open(key).read()

            # 刪除（保持環境乾淨）
            default_storage.delete(key)

            return {"ok": True, "bucket": bucket, "sample_url": url}
        except Exception as e:
            return {"ok": False, "error": f"{e}", "trace": traceback.format_exc()}

    # 4) （可選）Qdrant
    def check_qdrant(self):
        try:
            url = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
            api_key = os.getenv("QDRANT_API_KEY") or None
            client = QdrantClient(url=url, api_key=api_key)
            cname = "infra_probe"
            client.recreate_collection(cname, vectors_config=VectorParams(size=3, distance=Distance.COSINE))
            client.upsert(cname, points=[PointStruct(id=1, vector=[0.1,0.8,0.2], payload={"k":"v"})])
            hits = client.search(cname, query_vector=[0.1,0.8,0.2], limit=1)
            return {"ok": True, "search_top_id": int(hits[0].id)}
        except Exception as e:
            return {"ok": False, "error": f"{e}", "trace": traceback.format_exc()}