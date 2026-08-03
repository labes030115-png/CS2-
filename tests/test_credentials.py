import pytest

import backend.app.core.credentials as credentials
from backend.app.core.credentials import (
    CSQAQ_ACCOUNT_NAME,
    CSQAQ_SERVICE_NAME,
    CSQAQCredentialStore,
    UnsupportedCredentialPlatformError,
)


TOKEN = "test-token-must-never-leak"


class FakeCredentialBackend:
    def __init__(self) -> None:
        self.passwords: dict[tuple[str, str], str] = {}
        self.calls: list[tuple[str, str, str]] = []

    def get_password(self, service_name: str, username: str) -> str | None:
        self.calls.append(("get", service_name, username))
        return self.passwords.get((service_name, username))

    def set_password(
        self,
        service_name: str,
        username: str,
        password: str,
    ) -> None:
        self.calls.append(("set", service_name, username))
        self.passwords[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        self.calls.append(("delete", service_name, username))
        del self.passwords[(service_name, username)]


def test_save_and_load_token_use_dedicated_windows_credential_key() -> None:
    backend = FakeCredentialBackend()
    store = CSQAQCredentialStore(backend=backend)

    store.save_token(f"  {TOKEN}  ")

    assert store.load_token() == TOKEN
    assert backend.calls == [
        ("set", CSQAQ_SERVICE_NAME, CSQAQ_ACCOUNT_NAME),
        ("get", CSQAQ_SERVICE_NAME, CSQAQ_ACCOUNT_NAME),
    ]


def test_save_token_overwrites_existing_credential() -> None:
    backend = FakeCredentialBackend()
    store = CSQAQCredentialStore(backend=backend)

    store.save_token("old-token")
    store.save_token("new-token")

    assert store.load_token() == "new-token"


@pytest.mark.parametrize("token", ["", " ", "\r\n\t"])
def test_save_token_rejects_empty_values(token: str) -> None:
    backend = FakeCredentialBackend()
    store = CSQAQCredentialStore(backend=backend)

    with pytest.raises(ValueError, match="Token"):
        store.save_token(token)

    assert backend.calls == []


def test_load_token_treats_blank_credential_as_missing() -> None:
    backend = FakeCredentialBackend()
    backend.passwords[(CSQAQ_SERVICE_NAME, CSQAQ_ACCOUNT_NAME)] = "  "

    assert CSQAQCredentialStore(backend=backend).load_token() is None


def test_delete_token_is_idempotent_and_reports_whether_it_deleted() -> None:
    backend = FakeCredentialBackend()
    store = CSQAQCredentialStore(backend=backend)
    store.save_token(TOKEN)

    assert store.delete_token() is True
    assert store.delete_token() is False
    assert store.load_token() is None
    assert backend.calls.count(
        ("delete", CSQAQ_SERVICE_NAME, CSQAQ_ACCOUNT_NAME)
    ) == 1


def test_store_repr_never_exposes_backend_or_token() -> None:
    backend = FakeCredentialBackend()
    store = CSQAQCredentialStore(backend=backend)
    store.save_token(TOKEN)

    rendered = repr(store)

    assert TOKEN not in rendered
    assert "FakeCredentialBackend" not in rendered
    assert CSQAQ_SERVICE_NAME in rendered


def test_non_windows_platform_refuses_any_credential_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(credentials.sys, "platform", "linux")

    with pytest.raises(UnsupportedCredentialPlatformError, match="Windows"):
        CSQAQCredentialStore()


def test_windows_rejects_non_win_vault_keyring_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import keyring

    monkeypatch.setattr(credentials.sys, "platform", "win32")
    monkeypatch.setattr(keyring, "get_keyring", lambda: FakeCredentialBackend())

    with pytest.raises(UnsupportedCredentialPlatformError, match="Credential Manager"):
        CSQAQCredentialStore()
