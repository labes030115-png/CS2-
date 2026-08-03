from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import sys
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol, TextIO

from backend.app.core.credentials import CSQAQCredentialStore
from backend.app.sources.csqaq import CSQAQAdapter, CSQAQConfig, CSQAQError
from scripts.probe_csqaq import run_probe


class CredentialStore(Protocol):
    def save_token(self, token: str) -> None: ...

    def load_token(self) -> str | None: ...

    def delete_token(self) -> bool: ...


ProbeRunner = Callable[[str], Awaitable[dict[str, object]]]


class SafeArgumentError(ValueError):
    """Raised without retaining or echoing potentially sensitive arguments."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise SafeArgumentError("Invalid command arguments")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        prog="python -m scripts.csqaq_local",
        description="Windows-local CSQAQ lowest-listing probe",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    credential = commands.add_parser(
        "credential",
        help="Manage the CSQAQ token in Windows Credential Manager",
    )
    credential.add_argument("action", choices=("set", "status", "delete"))

    probe = commands.add_parser("probe", help="Run a redacted local probe")
    probe.add_argument("action", choices=("current",))
    return parser


def _contains_forbidden_token_argument(argv: Sequence[str]) -> bool:
    return any(
        argument.casefold() == "--token"
        or argument.casefold().startswith("--token=")
        for argument in argv
    )


def _write_json(stream: TextIO, payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream)


def _write_error(
    stream: TextIO,
    error_type: str,
    message: str,
) -> None:
    _write_json(
        stream,
        {
            "status": "error",
            "error_type": error_type,
            "message": message,
        },
    )


async def run_current_probe(token: str) -> dict[str, object]:
    config = CSQAQConfig(api_token=token)
    async with CSQAQAdapter(config) as adapter:
        return await run_probe(adapter)


async def main(
    argv: Sequence[str] | None = None,
    *,
    credential_store: CredentialStore | None = None,
    token_prompt: Callable[[str], str] = getpass.getpass,
    probe_runner: ProbeRunner | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    output = stdout if stdout is not None else sys.stdout
    error_output = stderr if stderr is not None else sys.stderr

    if _contains_forbidden_token_argument(arguments):
        _write_error(
            error_output,
            "UnsafeTokenArgumentError",
            "Do not pass a token on the command line; use credential set",
        )
        return 2

    try:
        parsed = build_parser().parse_args(arguments)
    except SafeArgumentError:
        _write_error(
            error_output,
            "CommandUsageError",
            "Invalid command; use --help to list safe local commands",
        )
        return 2

    try:
        store = credential_store or CSQAQCredentialStore()

        if parsed.command == "credential" and parsed.action == "set":
            token = token_prompt("CSQAQ Token（输入内容不会显示）: ")
            store.save_token(token)
            _write_json(output, {"status": "credential_saved"})
            return 0

        if parsed.command == "credential" and parsed.action == "status":
            _write_json(
                output,
                {
                    "status": "credential_status",
                    "saved": store.load_token() is not None,
                },
            )
            return 0

        if parsed.command == "credential" and parsed.action == "delete":
            deleted = store.delete_token()
            _write_json(
                output,
                {
                    "status": (
                        "credential_deleted"
                        if deleted
                        else "credential_not_found"
                    )
                },
            )
            return 0

        token = store.load_token()
        if token is None:
            _write_error(
                error_output,
                "CredentialMissingError",
                "No CSQAQ credential is saved; run credential set locally",
            )
            return 2
        runner = probe_runner or run_current_probe
        result = await runner(token)
        _write_json(output, result)
        return 0
    except CSQAQError as exc:
        _write_error(
            error_output,
            type(exc).__name__,
            "CSQAQ probe failed; only the safe error category is shown",
        )
        return 2
    except (EOFError, KeyboardInterrupt):
        _write_error(
            error_output,
            "CredentialInputCancelled",
            "Credential input was cancelled",
        )
        return 2
    except (Exception, asyncio.CancelledError):
        _write_error(
            error_output,
            "LocalCredentialError",
            "The local credential operation failed without exposing details",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
