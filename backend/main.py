import json
from datetime import datetime, timedelta

from celery.result import AsyncResult
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai.pdf_report import generate_pdf_report
from config import settings
from db.models import ScanLog, get_db, init_db
from tasks import celery_app, run_osint_scan

app = FastAPI(
  title="Tunel API",
  description="OSINT Intelligence Terminal",
  version="1.0.0",
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000", "http://localhost:5173"],
  allow_methods=["*"],
  allow_headers=["*"],
)


class ScanRequest(BaseModel):
  target: str = Field(..., min_length=2, max_length=255)
  target_type: str = Field(..., pattern="^(username|email)$")


def _check_rate_limit(db: Session, client_ip: str):
  since = datetime.utcnow() - timedelta(hours=1)
  count = (
    db.query(ScanLog)
    .filter(ScanLog.client_ip == client_ip, ScanLog.created_at >= since)
    .count()
  )
  if count >= settings.rate_limit_per_hour:
    raise HTTPException(
      status_code=429,
      detail=f"Saatlik tarama limiti aşıldı ({settings.rate_limit_per_hour}/saat)",
    )


@app.on_event("startup")
def on_startup():
  init_db()


@app.get("/health")
async def health():
  return {"status": "ok", "service": "tunel"}


@app.post("/scan")
async def start_scan(req: ScanRequest, request: Request, db: Session = Depends(get_db)):
  client_ip = request.client.host if request.client else "unknown"
  _check_rate_limit(db, client_ip)

  target = req.target.strip()
  if req.target_type == "email" and "@" not in target:
    raise HTTPException(status_code=400, detail="Geçerli bir e-posta adresi girin")
  if req.target_type == "username" and "@" in target:
    raise HTTPException(status_code=400, detail="Kullanıcı adı taraması için @ kullanmayın")

  task = run_osint_scan.delay(target, req.target_type)

  log = ScanLog(
    target=target,
    target_type=req.target_type,
    task_id=task.id,
    status="queued",
    client_ip=client_ip,
  )
  db.add(log)
  db.commit()

  return {"task_id": task.id, "status": "queued"}


@app.get("/scan/{task_id}")
async def get_result(task_id: str):
  result = AsyncResult(task_id, app=celery_app)

  if result.state == "PENDING":
    return {"status": "queued"}
  if result.state == "STARTED":
    return {"status": "running"}
  if result.state == "SUCCESS":
    return {"status": "done", "data": result.result}
  if result.state == "FAILURE":
    return {"status": "failed", "error": str(result.result)}

  return {"status": result.state.lower()}


@app.get("/scan/{task_id}/pdf")
async def download_pdf(task_id: str, db: Session = Depends(get_db)):
  log = db.query(ScanLog).filter(ScanLog.task_id == task_id).first()
  data = None

  if log and log.result_json:
    data = json.loads(log.result_json)
  else:
    result = AsyncResult(task_id, app=celery_app)
    if result.state != "SUCCESS":
      raise HTTPException(status_code=404, detail="Rapor henüz hazır değil")
    data = result.result

  target = (log.target if log else None) or data.get("target", "unknown")
  target_type = data.get("target_type", "unknown")
  pdf_bytes = generate_pdf_report(target, target_type, data)
  filename = f"tunel_{task_id[:8]}.pdf"
  return Response(
    content=pdf_bytes,
    media_type="application/pdf",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )


@app.get("/logs")
async def get_logs(limit: int = 20, db: Session = Depends(get_db)):
  logs = db.query(ScanLog).order_by(ScanLog.created_at.desc()).limit(limit).all()
  return [
    {
      "id": log.id,
      "target": log.target,
      "target_type": log.target_type,
      "status": log.status,
      "task_id": log.task_id,
      "created_at": log.created_at.isoformat() if log.created_at else None,
    }
    for log in logs
  ]
