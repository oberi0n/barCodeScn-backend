import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.models import HealthResponse, ScanRequest, ScanResponse

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("barcode-scanner")
_write_lock = threading.Lock()


def allowed_origins() -> list[str]:
    return [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append_scan(scan: ScanRequest, received_at: str) -> None:
    log_path = Path(os.getenv("SCANS_LOG_PATH", "/data/scans.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        received_at,
        f"barcode={scan.barcode}",
        f"lat={scan.latitude}",
        f"lon={scan.longitude}",
    ]
    if scan.accuracy is not None:
        fields.append(f"accuracy={scan.accuracy}m")
    line = " | ".join(fields) + "\n"

    # O_APPEND plus one write keeps each short record contiguous; the lock also
    # serializes concurrent requests handled by threads in this process.
    with _write_lock:
        descriptor = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(descriptor, line.encode("utf-8"))
        finally:
            os.close(descriptor)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Barcode Scanner API started")
    yield


app = FastAPI(title="Barcode Scanner test API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/scan", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def scan(payload: ScanRequest) -> ScanResponse:
    received_at = utc_timestamp()
    logger.info("Scan received: barcode=%s", payload.barcode)
    try:
        append_scan(payload, received_at)
    except OSError as error:
        logger.error("Unable to append scan log: %s", error)
        raise HTTPException(status_code=500, detail="Unable to store scan") from None
    return ScanResponse(status="ok", barcode=payload.barcode, received_at=received_at)
