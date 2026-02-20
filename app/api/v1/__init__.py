from fastapi import APIRouter

from .incidents.views import router as incidents_router
from .events.views import router as events_router
from .timelines.views import router as timelines_router
from .logs.views import router as logs_router

router = APIRouter()
router.include_router(incidents_router)
router.include_router(events_router)
router.include_router(timelines_router)
router.include_router(logs_router)
