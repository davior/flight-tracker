from fastapi import APIRouter

from app.api.admin.ai import router as ai_router
from app.api.admin.data_sync import router as data_sync_router
from app.api.admin.logs import router as logs_router
from app.api.admin.metrics import router as metrics_router
from app.api.admin.users import router as users_router

router = APIRouter(prefix="/admin")
router.include_router(users_router)
router.include_router(metrics_router)
router.include_router(logs_router)
router.include_router(data_sync_router)
router.include_router(ai_router)
