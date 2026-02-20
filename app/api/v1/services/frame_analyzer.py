import asyncio
import base64
import json
from pathlib import Path

import cv2
import httpx

from app.config import settings


DOMAIN_PROMPTS = {
    "traffic": "столкновение автомобилей, наезд, резкое торможение, ДТП, авария",
    "production": "падение груза, нарушение техники безопасности, обрушение, травма",
    "violence": "драка, удар, нападение, агрессия, применение оружия",
}

ANALYZE_PROMPT = """Ты анализируешь кадры из видеозаписи (интервал {start:.1f}с – {end:.1f}с).
Определи: есть ли на кадрах опасное событие ({keywords})?
Ответь строго в JSON без markdown:
{{"has_event": true/false, "description": "краткое описание", "risk_score": 0.0-1.0}}"""

_CONCURRENCY = 5


def _extract_frames_b64(video_path: Path, start: float, end: float, n: int = 4) -> list[str]:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frames = []
    timestamps = [start + (end - start) * i / max(n - 1, 1) for i in range(n)]
    for ts in timestamps:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(ts * fps))
        ok, frame = cap.read()
        if not ok:
            continue
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frames.append(base64.b64encode(buf).decode())
    cap.release()
    return frames


async def _analyze_window(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    window_idx: int,
    ts: float,
    end: float,
    frames_b64: list[str],
    keywords: str,
    domain_clean: str,
) -> dict:
    prompt = ANALYZE_PROMPT.format(start=ts, end=end, keywords=keywords)
    async with sem:
        response = await client.post(
            f"{settings.llm_api_url}/generate",
            json={"prompt": prompt, "images_b64": frames_b64, "max_tokens": 150},
        )
        response.raise_for_status()
        text = response.json().get("text", "{}")

    try:
        parsed = json.loads(text.strip())
    except json.JSONDecodeError:
        parsed = {"has_event": False, "description": text[:200], "risk_score": 0.0}

    has_event = parsed.get("has_event", False)
    risk_score = float(parsed.get("risk_score", 0.0))
    description = parsed.get("description", "")

    return {
        "window_idx": window_idx,
        "ts": ts,
        "end": end,
        "has_event": has_event,
        "risk_score": risk_score,
        "description": description,
        "domain_clean": domain_clean,
    }


async def analyze_video_by_frames(
    video_path: Path,
    domain: str | None = None,
    window_sec: float = 2.0,
    frames_per_window: int = 4,
) -> dict:
    domain_clean = (domain or "").strip("\"' ").lower()
    keywords = DOMAIN_PROMPTS.get(domain_clean, "опасное событие, инцидент, нарушение")

    cap = cv2.VideoCapture(str(video_path))
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 25)
    cap.release()

    windows: list[tuple[int, float, float, list[str]]] = []
    ts = 0.0
    idx = 0
    while ts < duration:
        end = min(ts + window_sec, duration)
        frames_b64 = _extract_frames_b64(video_path, ts, end, frames_per_window)
        if frames_b64:
            windows.append((idx, ts, end, frames_b64))
        ts = end
        idx += 1

    sem = asyncio.Semaphore(_CONCURRENCY)
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)) as client:
        tasks = [
            _analyze_window(client, sem, w_idx, w_ts, w_end, w_frames, keywords, domain_clean)
            for w_idx, w_ts, w_end, w_frames in windows
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    timeline = []
    events = []
    for r in results:
        if isinstance(r, Exception):
            continue
        has_event = r["has_event"]
        timeline.append({
            "window_idx": r["window_idx"],
            "timestamp_sec": round(r["ts"], 2),
            "interval_end_sec": round(r["end"], 2),
            "label": "EVENT" if has_event else "SAFE",
            "has_event": has_event,
            "caption": r["description"],
            "risk_score": r["risk_score"],
            "event_type": domain_clean if has_event else "safe",
        })
        if has_event:
            events.append({
                "has_event": True,
                "event_type": domain_clean or "event",
                "interval_start_sec": round(r["ts"], 2),
                "interval_end_sec": round(r["end"], 2),
                "description": r["description"],
                "highlight_start_sec": round(r["ts"], 2),
                "highlight_end_sec": round(r["end"], 2),
            })

    timeline.sort(key=lambda x: x["window_idx"])

    return {
        "status": "completed",
        "inferred_domain": domain_clean or "other",
        "has_event": len(events) > 0,
        "events": events,
        "timeline": timeline,
        "metadata": {
            "duration_sec": round(duration, 2),
            "num_frames": int(duration * 25),
            "num_windows": idx,
        },
    }
