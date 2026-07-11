import re
# pyrefly: ignore [missing-import]
from pwdlib import PasswordHash
from app.shared.exceptions import ValidationException, ErrorDetail


class PasswordManager:
    """
    Handles secure password hashing and verification using the Argon2id algorithm via pwdlib.
    Enforces password complexity requirements.
    """

    def __init__(self) -> None:
        # Initialize PasswordHash using the recommended Argon2 configuration
        self._hasher = PasswordHash.recommended()

    def validate_password_strength(self, password: str) -> None:
        """
        Validates password strength against policy:
        - Minimum 12 characters
        - Contains at least one uppercase letter
        - Contains at least one lowercase letter
        - Contains at least one digit
        - Contains at least one special character

        Raises:
            ValidationException: If the password does not meet complexity requirements.
        """
        errors = []
        if len(password) < 12:
            errors.append(ErrorDetail(field="password", issue="Password must be at least 12 characters long"))
        if not re.search(r"[A-Z]", password):
            errors.append(ErrorDetail(field="password", issue="Password must contain at least one uppercase letter"))
        if not re.search(r"[a-z]", password):
            errors.append(ErrorDetail(field="password", issue="Password must contain at least one lowercase letter"))
        if not re.search(r"\d", password):
            errors.append(ErrorDetail(field="password", issue="Password must contain at least one numeric digit"))
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append(ErrorDetail(field="password", issue="Password must contain at least one special character"))

        if errors:
            raise ValidationException(
                message="Password does not meet complexity requirements",
                details=errors
            )

    def hash_password(self, password: str) -> str:
        """
        Hashes a plaintext password string.

        Args:
            password: The raw plaintext password string to encrypt.

        Returns:
            The secure, salted Argon2id hash string.
        """
        return self._hasher.hash(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verifies a plaintext password against an existing hash.
        Protects against timing analysis attacks.

        Args:
            password: The raw plaintext password to check.
            hashed: The stored Argon2id hash.

        Returns:
            True if verification succeeds, False otherwise.
        """
        return self._hasher.verify(password, hashed)


