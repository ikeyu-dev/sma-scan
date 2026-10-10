"""スマスキャン バックエンドAPI。"""

import asyncio
import json
import os
import secrets
from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator

app = FastAPI(title="スマスキャン API", version="1.0.0")

HOST_IP = os.environ.get("HOST_IP", "localhost")
SCAN_TOKEN = os.environ.get("SCAN_TOKEN", "")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:3002", f"https://{HOST_IP}:3002"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Scan-Token"],
)


def require_token(x_scan_token: str = Header(default="")) -> None:
    if not SCAN_TOKEN or not secrets.compare_digest(x_scan_token, SCAN_TOKEN):
        raise HTTPException(status_code=401, detail="接続コードが正しくありません")


class ScanRequest(BaseModel):
    url: str

    @validator("url")
    @classmethod
    def valid_web_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if (
            len(value) > 2048
            or any(char in value for char in "\r\n\t")
            or parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("HTTPまたはHTTPSのURLを読み取ってください")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("ポート番号が正しくありません") from exc
        return value


class ScanResponse(BaseModel):
    success: bool
    message: str
    url: str
    timestamp: str


class OpenResult(BaseModel):
    success: bool


scan_history: list[dict] = []
pending_urls: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
pending_results: dict[str, asyncio.Future[bool]] = {}
opener_connected = False


@app.post("/scan", response_model=ScanResponse, dependencies=[Depends(require_token)])
async def scan_qr_code(request: ScanRequest) -> ScanResponse:
    if not opener_connected:
        raise HTTPException(status_code=503, detail="PCのブラウザオープナーに接続できません")

    event_id = uuid4().hex
    result = asyncio.get_running_loop().create_future()
    pending_results[event_id] = result
    timestamp = datetime.now().isoformat()
    try:
        await pending_urls.put((event_id, request.url))
        opened_in_browser = await asyncio.wait_for(result, timeout=15)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="PCからの応答がありません") from exc
    finally:
        pending_results.pop(event_id, None)

    scan_history.append(
        {"url": request.url, "timestamp": timestamp, "success": opened_in_browser}
    )
    if not opened_in_browser:
        raise HTTPException(status_code=502, detail="PCでブラウザを開けませんでした")
    return ScanResponse(
        success=True,
        message="PCでブラウザを開きました",
        url=request.url,
        timestamp=timestamp,
    )


@app.post("/opened/{event_id}", dependencies=[Depends(require_token)])
async def opened(event_id: str, result: OpenResult) -> dict:
    waiter = pending_results.get(event_id)
    if waiter is None or waiter.done():
        raise HTTPException(status_code=404, detail="処理待ちのURLがありません")
    waiter.set_result(result.success)
    return {"status": "ok"}


@app.get("/stream", dependencies=[Depends(require_token)])
async def stream_urls():
    global opener_connected
    if opener_connected:
        raise HTTPException(status_code=409, detail="オープナーは既に接続されています")
    opener_connected = True

    async def event_generator():
        global opener_connected
        try:
            yield ": connected\n\n"
            while True:
                try:
                    event_id, url = await asyncio.wait_for(pending_urls.get(), timeout=5)
                    if event_id in pending_results:
                        yield f"data: {json.dumps({'id': event_id, 'url': url})}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            opener_connected = False

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/history", dependencies=[Depends(require_token)])
async def get_scan_history() -> list[dict]:
    return list(reversed(scan_history[-100:]))


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
