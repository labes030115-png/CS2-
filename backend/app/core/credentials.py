from __future__ import annotations

import sys
from typing import Protocol


CSQAQ_SERVICE_NAME = "cs2-collection-tracker"
CSQAQ_ACCOUNT_NAME = "CSQAQ_TOKEN"


class UnsupportedCredentialPlatformError(RuntimeError):
    """Raised rather than falling back to a non-Windows credential store."""


class CredentialBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(
        self,
        service_name: str,
        username: str,
        password: str,
    ) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


def _system_credential_backend() -> CredentialBackend:
    if sys.platform != "win32":
        raise UnsupportedCredentialPlatformError(
            "CSQAQ credentials are supported only on Windows"
        )

    import keyring
    from keyring.backends.Windows import WinVaultKeyring

    backend = keyring.get_keyring()
    if not isinstance(backend, WinVaultKeyring):
        raise UnsupportedCredentialPlatformError(
            "Windows Credential Manager is required for CSQAQ credentials"
        )
    return backend


class CSQAQCredentialStore:
    """Store the local probe token outside project files and process logs."""

    __slots__ = ("_backend",)

    def __init__(self, backend: CredentialBackend | None = None) -> None:
        self._backend = backend if backend is not None else _system_credential_backend()

    def __repr__(self) -> str:
        return (
            "CSQAQCredentialStore("
            f"service_name={CSQAQ_SERVICE_NAME!r}, "
            f"account_name={CSQAQ_ACCOUNT_NAME!r})"
        )

    def save_token(self, token: str) -> None:
        normalized = token.strip()
        if not normalized:
            raise ValueError("Token must not be empty")
        self._backend.set_password(
            CSQAQ_SERVICE_NAME,
            CSQAQ_ACCOUNT_NAME,
            normalized,
        )

    def load_token(self) -> str | None:
        token = self._backend.get_password(
            CSQAQ_SERVICE_NAME,
            CSQAQ_ACCOUNT_NAME,
        )
        if token is None:
            return None
        normalized = token.strip()
        return normalized or None

    def delete_token(self) -> bool:
        if self.load_token() is None:
            return False
        self._backend.delete_password(
            CSQAQ_SERVICE_NAME,
            CSQAQ_ACCOUNT_NAME,
        )
        return True
