"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.admin.router import router as admin_router
from app.api.v1.analytics.router import router as analytics_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.chat.router import router as chat_router
from app.api.v1.company.router import router as company_router
from app.api.v1.document.router import router as document_router
from app.api.v1.knowledge.router import router as knowledge_router
from app.api.v1.role.router import router as role_router
from app.api.v1.ticket.router import router as ticket_router
from app.api.v1.user.router import router as user_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(company_router)
api_v1_router.include_router(user_router)
api_v1_router.include_router(role_router)
api_v1_router.include_router(document_router)
api_v1_router.include_router(knowledge_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(ticket_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(admin_router)
