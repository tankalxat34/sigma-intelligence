import httpx
from pathlib import Path

from app.config import settings


async def _call_analyze(file_path: Path, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=5.0)) as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                f"{settings.llm_api_url}/analyze_video",
                params=params,
                files={"file": (file_path.name, f, "video/mp4")},
            )
        response.raise_for_status()
        return response.json()


async def analyze_video(
    file_path: Path,
    domain: str | None = None,
    _progress: dict | None = None,
    _iid: int | None = None,
) -> dict:
    def _report(extra: dict) -> None:
        if _progress is not None and _iid is not None:
            _progress[_iid] = {"status": "PROCESSING", **extra}

    domain_clean = (domain or "").strip("\"' ").lower()

    params: dict = {
        "target_fps": settings.llm_target_fps,
        "window_sec": settings.llm_window_sec,
        "frames_per_window": settings.llm_frames_per_window,
        "max_highlights": settings.llm_max_highlights,
    }
    if domain_clean and domain_clean not in ("auto", "unknown"):
        params["domain"] = domain_clean

    _report({"stage": 1, "stage_name": "Первичный анализ"})
    result = await _call_analyze(file_path, params)

    if not result.get("has_event") and not result.get("events"):
        retry_params = {
            **params,
            "window_sec": max(0.5, settings.llm_window_sec / 2),
            "target_fps": min(30, settings.llm_target_fps * 2),
            "frames_per_window": min(10, settings.llm_frames_per_window + 2),
        }
        _report({"stage": 2, "stage_name": "Повторный анализ (мелкие окна)"})
        retry_result = await _call_analyze(file_path, retry_params)
        if retry_result.get("has_event") or retry_result.get("events"):
            return retry_result

        from app.api.v1.services.frame_analyzer import analyze_video_by_frames
        _report({"stage": 3, "stage_name": "Покадровый анализ"})
        frame_result = await analyze_video_by_frames(file_path, domain=domain)
        if frame_result.get("has_event") or frame_result.get("events"):
            return frame_result

    return result


async def generate_report(
    analysis_json: str,
    video_path: Path | None = None,
    return_format: str = "docx",
) -> bytes:
    files: dict = {"analysis_json": (None, analysis_json)}
    if video_path and video_path.exists():
        files["video"] = (video_path.name, open(video_path, "rb"), "video/mp4")

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=300.0, write=60.0, pool=5.0)) as client:
        response = await client.post(
            f"{settings.llm_api_url}/generate_report_from_json",
            params={"return_format": return_format},
            files=files,
        )
        response.raise_for_status()
        return response.content
