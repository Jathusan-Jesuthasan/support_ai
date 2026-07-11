import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from bson import ObjectId


# =====================================================================
# UUID Utilities
# =====================================================================


def generate_uuid() -> UUID:
    """
    Generates a cryptographically random UUIDv4.
    """
    return uuid4()


def validate_uuid(value: Any) -> bool:
    """
    Checks if a value is a valid UUID instance or parses into a valid UUIDv4.
    """
    if isinstance(value, UUID):
        return True
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
        return True
    except ValueError:
        return False


# =====================================================================
# Datetime Utilities
# =====================================================================


def utc_now() -> datetime:
    """
    Returns the current timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    Returns the current UTC datetime formatted as an ISO-8601 string.
    """
    return utc_now().isoformat()


def parse_datetime(value: str) -> Optional[datetime]:
    """
    Parses an ISO-8601 string into a timezone-aware UTC datetime object.
    Returns None if parsing fails.
    """
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


# =====================================================================
# String Utilities
# =====================================================================


def slugify(value: str) -> str:
    """
    Converts a string into a clean lowercase, hyphen-delimited URL slug.
    Example: "ACME Corp! 123" -> "acme-corp-123"
    """
    value = value.lower().strip()
    # Replace non-alphanumeric characters with a space
    value = re.sub(r"[^\w\s-]", "", value)
    # Replace spaces or multiple dashes with a single dash
    value = re.sub(r"[-\s]+", "-", value)
    return value.strip("-")


def normalize_email(email: str) -> str:
    """
    Trims whitespace and normalizes email string casing.
    """
    return email.strip().lower()


def safe_filename(filename: str) -> str:
    """
    Sanitizes file upload paths to prevent directory traversal and special character exploits.
    """
    # Remove directory paths
    basename = re.sub(r"^.*[\\/]", "", filename)
    # Remove characters other than letters, numbers, periods, dashes, and underscores
    basename = re.sub(r"[^\w\.-]", "", basename)
    return basename.strip()


# =====================================================================
# Pagination Utilities
# =====================================================================


def calculate_total_pages(total_items: int, limit: int) -> int:
    """
    Calculates total pages based on matching items and page limits.
    """
    if limit <= 0:
        return 0
    return math.ceil(total_items / limit)


# =====================================================================
# MongoDB Utilities
# =====================================================================


def objectid_to_str(value: Any) -> Optional[str]:
    """
    Resolves BSON ObjectIds to standard hex string formats.
    """
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str) and ObjectId.is_valid(value):
        return value
    return None


def remove_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively strips keys containing None values.
    Utilized during partial MongoDB update payload constructions.
    """
    cleaned: Dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, dict):
            cleaned[key] = remove_none_values(value)
        else:
            cleaned[key] = value
    return cleaned


# =====================================================================
# Non-Cryptographic Security Masking
# =====================================================================


def mask_email(email: str) -> str:
    """
    Masks sensitive email addresses for transaction tracing log safety.
    Example: "user.name@domain.com" -> "u***e@domain.com"
    """
    email = normalize_email(email)
    if "@" not in email:
        return email
    username, domain = email.split("@", 1)
    if len(username) <= 2:
        return f"{username[0]}***@{domain}"
    return f"{username[0]}***{username[-1]}@{domain}"


def mask_phone(phone: str) -> str:
    """
    Masks telephone numbers, retaining only the trailing 4 digits.
    Example: "+1234567890" -> "******7890"
    """
    clean_phone = re.sub(r"\D", "", phone)
    if len(clean_phone) <= 4:
        return "****"
    return f"{'*' * (len(clean_phone) - 4)}{clean_phone[-4:]}"
