"""
Token encryption utility for secure storage of OAuth tokens.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC) for encrypting
sensitive tokens before database storage.

Usage:
    from mint.utils.token_encryption import get_token_encryption

    encryption = get_token_encryption()
    encrypted = encryption.encrypt("my-secret-token")
    decrypted = encryption.decrypt(encrypted)

Environment Variables:
    TOKEN_ENCRYPTION_KEY: Fernet key for encryption. Generate with:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class TokenEncryptionError(Exception):
    """Raised when token encryption/decryption fails."""
    pass


class TokenEncryption:
    """
    Handles encryption/decryption of OAuth tokens using Fernet.

    Fernet guarantees that a message encrypted using it cannot be
    manipulated or read without the key. It uses AES-128-CBC for
    encryption and HMAC-SHA256 for authentication.
    """

    def __init__(self, key: Optional[str] = None):
        """
        Initialize the encryption service.

        Args:
            key: Fernet encryption key. If not provided, reads from
                 TOKEN_ENCRYPTION_KEY environment variable.

        Raises:
            TokenEncryptionError: If no key is available.
        """
        encryption_key = key or os.getenv("TOKEN_ENCRYPTION_KEY")

        if not encryption_key:
            raise TokenEncryptionError(
                "TOKEN_ENCRYPTION_KEY environment variable is not set. "
                "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

        try:
            # Ensure key is bytes
            if isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()

            self.cipher = Fernet(encryption_key)
        except Exception as e:
            raise TokenEncryptionError(f"Invalid encryption key: {str(e)}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a token string.

        Args:
            plaintext: The token to encrypt.

        Returns:
            Base64-encoded encrypted string.

        Raises:
            TokenEncryptionError: If encryption fails.
        """
        if not plaintext:
            raise TokenEncryptionError("Cannot encrypt empty token")

        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode("utf-8"))
            return encrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"Token encryption failed: {str(e)}")
            raise TokenEncryptionError(f"Encryption failed: {str(e)}")

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt a token string.

        Args:
            encrypted: The encrypted token (base64-encoded).

        Returns:
            Decrypted plaintext string.

        Raises:
            TokenEncryptionError: If decryption fails (invalid token or key).
        """
        if not encrypted:
            raise TokenEncryptionError("Cannot decrypt empty token")

        try:
            decrypted_bytes = self.cipher.decrypt(encrypted.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            logger.error("Token decryption failed: Invalid token or key")
            raise TokenEncryptionError(
                "Decryption failed: Invalid token or wrong encryption key"
            )
        except Exception as e:
            logger.error(f"Token decryption failed: {str(e)}")
            raise TokenEncryptionError(f"Decryption failed: {str(e)}")

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            A new Fernet key suitable for TOKEN_ENCRYPTION_KEY env var.
        """
        return Fernet.generate_key().decode("utf-8")


# Singleton instance
_token_encryption: Optional[TokenEncryption] = None


def get_token_encryption() -> TokenEncryption:
    """
    Get or create the singleton TokenEncryption instance.

    Returns:
        TokenEncryption instance.

    Raises:
        TokenEncryptionError: If TOKEN_ENCRYPTION_KEY is not set.
    """
    global _token_encryption
    if _token_encryption is None:
        _token_encryption = TokenEncryption()
    return _token_encryption


def reset_token_encryption() -> None:
    """
    Reset the singleton instance. Useful for testing.
    """
    global _token_encryption
    _token_encryption = None
