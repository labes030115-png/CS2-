import asyncio
import io
import json

from backend.app.sources.csqaq import CSQAQAuthenticationError
from scripts.csqaq_local import main


TOKEN = "test-token-must-never-leak"


class FakeCredentialStore:
    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.saved_tokens: list[str] = []
        self.delete_calls = 0

    def save_token(self, token: str) -> None:
        self.saved_tokens.append(token)
        self.token = token

    def load_token(self) -> str | None:
        return self.token

    def delete_token(self) -> bool:
        self.delete_calls += 1
        existed = self.token is not None
        self.token = None
        return existed


def invoke(
    argv: list[str],
    *,
    store: FakeCredentialStore,
    prompt=lambda _message: TOKEN,
    probe_runner=None,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = asyncio.run(
        main(
            argv,
            credential_store=store,
            token_prompt=prompt,
            probe_runner=probe_runner,
            stdout=stdout,
            stderr=stderr,
        )
    )
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_credential_set_uses_hidden_prompt_and_never_prints_token() -> None:
    store = FakeCredentialStore()
    prompts: list[str] = []

    def prompt(message: str) -> str:
        prompts.append(message)
        return f"  {TOKEN}  "

    exit_code, stdout, stderr = invoke(
        ["credential", "set"],
        store=store,
        prompt=prompt,
    )

    assert exit_code == 0
    assert store.saved_tokens == [f"  {TOKEN}  "]
    assert len(prompts) == 1
    assert json.loads(stdout)["status"] == "credential_saved"
    assert TOKEN not in stdout + stderr


def test_credential_status_reports_presence_without_revealing_value() -> None:
    store = FakeCredentialStore(TOKEN)

    exit_code, stdout, stderr = invoke(
        ["credential", "status"],
        store=store,
    )

    assert exit_code == 0
    assert json.loads(stdout) == {"status": "credential_status", "saved": True}
    assert TOKEN not in stdout + stderr


def test_credential_delete_is_a_single_idempotent_command() -> None:
    store = FakeCredentialStore(TOKEN)

    first = invoke(["credential", "delete"], store=store)
    second = invoke(["credential", "delete"], store=store)

    assert first[0] == second[0] == 0
    assert json.loads(first[1])["status"] == "credential_deleted"
    assert json.loads(second[1])["status"] == "credential_not_found"
    assert store.delete_calls == 2
    assert TOKEN not in first[1] + first[2] + second[1] + second[2]


def test_probe_requires_saved_credential_without_calling_network() -> None:
    store = FakeCredentialStore()
    called = False

    async def probe_runner(_token: str) -> dict[str, object]:
        nonlocal called
        called = True
        return {}

    exit_code, stdout, stderr = invoke(
        ["probe", "current"],
        store=store,
        probe_runner=probe_runner,
    )

    assert exit_code == 2
    assert stdout == ""
    assert json.loads(stderr)["error_type"] == "CredentialMissingError"
    assert called is False


def test_probe_loads_credential_only_in_memory_and_prints_redacted_result() -> None:
    store = FakeCredentialStore(TOKEN)
    received_tokens: list[str] = []

    async def probe_runner(token: str) -> dict[str, object]:
        received_tokens.append(token)
        return {
            "source_code": "YYYP",
            "metric": "lowest_listing",
            "targets": [],
        }

    exit_code, stdout, stderr = invoke(
        ["probe", "current"],
        store=store,
        probe_runner=probe_runner,
    )

    assert exit_code == 0
    assert received_tokens == [TOKEN]
    assert json.loads(stdout)["metric"] == "lowest_listing"
    assert TOKEN not in stdout + stderr


def test_probe_prints_only_safe_adapter_error() -> None:
    store = FakeCredentialStore(TOKEN)

    async def probe_runner(_token: str) -> dict[str, object]:
        raise CSQAQAuthenticationError(
            f"CSQAQ token authentication failed for {TOKEN}"
        )

    exit_code, stdout, stderr = invoke(
        ["probe", "current"],
        store=store,
        probe_runner=probe_runner,
    )

    error = json.loads(stderr)
    assert exit_code == 2
    assert stdout == ""
    assert error["error_type"] == "CSQAQAuthenticationError"
    assert TOKEN not in stderr


def test_forbidden_command_line_token_is_rejected_without_echoing_value() -> None:
    store = FakeCredentialStore()

    exit_code, stdout, stderr = invoke(
        ["probe", "current", "--token", TOKEN],
        store=store,
    )

    assert exit_code == 2
    assert stdout == ""
    assert json.loads(stderr)["error_type"] == "UnsafeTokenArgumentError"
    assert TOKEN not in stderr


def test_unexpected_local_error_details_are_not_printed() -> None:
    class BrokenCredentialStore(FakeCredentialStore):
        def load_token(self) -> str | None:
            raise RuntimeError(f"backend failed near {TOKEN}")

    exit_code, stdout, stderr = invoke(
        ["credential", "status"],
        store=BrokenCredentialStore(),
    )

    assert exit_code == 2
    assert stdout == ""
    assert json.loads(stderr)["error_type"] == "LocalCredentialError"
    assert TOKEN not in stderr
