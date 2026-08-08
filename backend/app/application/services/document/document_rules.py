"""Document upload validation helpers and plan file-size limits."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.exceptions.document import DocumentValidationError

# Per-plan max upload size (bytes) — docs/database/03_Tables/documents.md.txt
MAX_FILE_BYTES_BY_PLAN: dict[SubscriptionPlan, int] = {
    SubscriptionPlan.FREE: 10 * 1024 * 1024,
    SubscriptionPlan.STARTER: 25 * 1024 * 1024,
    SubscriptionPlan.PRO: 100 * 1024 * 1024,
    SubscriptionPlan.BUSINESS: 250 * 1024 * 1024,
    SubscriptionPlan.ENTERPRISE: 500 * 1024 * 1024,
}

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".docx",
        ".doc",
        ".txt",
        ".html",
        ".htm",
        ".md",
        ".markdown",
        ".csv",
        ".xlsx",
        ".xls",
        ".pptx",
        ".ppt",
        ".json",
        ".xml",
    }
)

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/html",
        "text/markdown",
        "text/csv",
        "application/json",
        "application/xml",
        "text/xml",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/octet-stream",
    }
)

SORTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "created_at",
        "updated_at",
        "document_name",
        "file_size_bytes",
        "processing_status",
        "original_filename",
    }
)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def validate_sort_by(sort_by: str) -> str:
    field = (sort_by or "created_at").strip()
    if field not in SORTABLE_FIELDS:
        raise DocumentValidationError(
            f"Invalid sort_by. Allowed: {', '.join(sorted(SORTABLE_FIELDS))}."
        )
    return field


def normalize_document_name(name: str) -> str:
    value = (name or "").strip()
    if not value:
        raise DocumentValidationError("Document name is required.")
    if len(value) > 255:
        raise DocumentValidationError("Document name must be at most 255 characters.")
    return value


def extract_extension(filename: str) -> str:
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    if not suffix:
        raise DocumentValidationError("File extension is required.")
    if suffix not in ALLOWED_EXTENSIONS:
        raise DocumentValidationError(
            f"Unsupported file type '{suffix}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    return suffix


def validate_mime_type(mime_type: str | None) -> str:
    value = (mime_type or "application/octet-stream").split(";")[0].strip().lower()
    if value not in ALLOWED_MIME_TYPES:
        raise DocumentValidationError(f"Unsupported MIME type: {value}")
    return value


def validate_file_size(size_bytes: int, plan: SubscriptionPlan) -> None:
    if size_bytes <= 0:
        raise DocumentValidationError("Uploaded file is empty.")
    limit = MAX_FILE_BYTES_BY_PLAN.get(plan, MAX_FILE_BYTES_BY_PLAN[SubscriptionPlan.FREE])
    if size_bytes > limit:
        raise DocumentValidationError(
            f"File exceeds the {plan.value} plan limit of {limit // (1024 * 1024)} MB."
        )


def sanitize_filename(filename: str) -> str:
    base = PurePosixPath(filename.replace("\\", "/")).name.strip()
    if not base:
        raise DocumentValidationError("Original filename is required.")
    cleaned = _SAFE_NAME_RE.sub("_", base)
    return cleaned[:200] or "upload.bin"
