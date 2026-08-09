"""Knowledge Base indexing service (compat alias)."""

from app.application.services.knowledge.knowledge_service import KnowledgeService

IndexingService = KnowledgeService

__all__ = ["IndexingService", "KnowledgeService"]
