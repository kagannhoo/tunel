from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from celery import Celery
from sqlalchemy.orm import Session

from ai.analyzer import analyze_results
from config import settings
from db.models import ScanLog, SessionLocal
from workers.breach_check import run_breach_check
from workers.email_intel import run_email_intel, _is_valid_derived_username
from workers.email_scan import run_email_scan
from workers.username_scan import run_username_scan

celery_app = Celery(
  "tunel",
  broker=settings.celery_broker_url,
  backend=settings.celery_result_backend,
)

celery_app.conf.update(
  task_serializer="json",
  result_serializer="json",
  accept_content=["json"],
  task_track_started=True,
  result_expires=3600,
  task_time_limit=settings.scan_timeout_seconds + 60,
  task_soft_time_limit=settings.scan_timeout_seconds,
)


def _update_scan_log(task_id: str, status: str, result: dict | None = None):
  db: Session = SessionLocal()
  try:
    log = db.query(ScanLog).filter(ScanLog.task_id == task_id).first()
    if log:
      log.status = status
      if result is not None:
        import json

        log.result_json = json.dumps(result, ensure_ascii=False)
        log.completed_at = datetime.utcnow()
      db.commit()
  finally:
    db.close()


def _run_email_deep_scan(email: str) -> dict:
  """E-posta için çok katmanlı derin tarama."""
  local = email.split("@")[0] if "@" in email else ""
  scan_jobs = {
    "registrations": lambda: run_email_scan(email),
    "breaches": lambda: run_breach_check(email),
    "email_intel": lambda: run_email_intel(email),
  }
  if _is_valid_derived_username(local):
    scan_jobs["username_platforms"] = lambda: run_username_scan(local)

  results = {}
  timeout = settings.scan_timeout_seconds

  with ThreadPoolExecutor(max_workers=len(scan_jobs)) as executor:
    futures = {key: executor.submit(fn) for key, fn in scan_jobs.items()}
    for key, future in futures.items():
      try:
        results[key] = future.result(timeout=timeout)
      except Exception as e:
        results[key] = {"error": str(e), "count": 0}

  return results


@celery_app.task(name="sherlock_task")
def sherlock_task(username: str):
  from workers.sherlock import run_sherlock
  return run_sherlock(username)


@celery_app.task(name="username_scan_task")
def username_scan_task(username: str):
  return run_username_scan(username)


@celery_app.task(name="email_scan_task")
def email_scan_task(email: str):
  return run_email_scan(email)


@celery_app.task(name="breach_check_task")
def breach_check_task(email: str):
  return run_breach_check(email)


@celery_app.task(name="run_osint_scan", bind=True)
def run_osint_scan(self, target: str, target_type: str):
  task_id = self.request.id
  _update_scan_log(task_id, "running")
  started = datetime.utcnow()

  results = {"target": target, "target_type": target_type, "scan_mode": "standard"}

  try:
    if target_type == "username":
      results["scan_mode"] = "deep_username"
      results["platforms"] = run_username_scan(target)
    elif target_type == "email":
      results["scan_mode"] = "deep_email"
      deep = _run_email_deep_scan(target)
      results.update(deep)
    else:
      results["error"] = f"Geçersiz target_type: {target_type}"

    scan_meta = {
      "task_id": task_id,
      "duration_seconds": (datetime.utcnow() - started).total_seconds(),
      "scan_mode": results.get("scan_mode"),
    }
    results["ai_analysis"] = analyze_results(results, scan_meta=scan_meta)
    results["scanned_at"] = datetime.utcnow().isoformat()

    _update_scan_log(task_id, "done", results)
    return results
  except Exception as e:
    error_result = {"error": str(e), "target": target, "target_type": target_type}
    _update_scan_log(task_id, "failed", error_result)
    raise
