"""Document processing / lifecycle status."""

from enum import StrEnum


class DocumentStatus(StrEnum):
    """Pipeline status for knowledge documents (RAG steps land later)."""

    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class StorageProvider(StrEnum):
    """Object storage backends."""

    LOCAL = "LOCAL"
    AWS_S3 = "AWS_S3"
    AZURE_BLOB = "AZURE_BLOB"
    GOOGLE_CLOUD = "GOOGLE_CLOUD"
    MINIO = "MINIO"
