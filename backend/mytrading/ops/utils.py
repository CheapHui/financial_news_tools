import time, traceback
from contextlib import contextmanager
from django.utils import timezone
from django.db import connection
from .models import JobRun

def set_hnsw_ef_search(ef: int = 100):
    with connection.cursor() as cur:
        cur.execute("SET hnsw.ef_search = %s;", [ef])

@contextmanager
def record_job(name: str):
    run = JobRun.objects.create(name=name)
    t0 = time.perf_counter()
    processed = 0
    try:
        yield lambda n: globals().__setitem__("__ops_processed__", n)  # setter
        processed = globals().get("__ops_processed__", 0)
        run.success = True
    except Exception as e:
        run.error = f"{e}\n{traceback.format_exc()}"
        run.success = False
        processed = globals().get("__ops_processed__", 0)
        raise
    finally:
        dt = int((time.perf_counter() - t0) * 1000)
        run.duration_ms = dt
        run.processed = int(processed or 0)
        run.finished_at = timezone.now()
        run.save()