"""Minimal Codex Python SDK smoke test for Phase 1."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import webbrowser
from pathlib import Path
from typing import Any

from openai_codex import ApprovalMode, AsyncCodex, CodexConfig, Sandbox

from runner.config import load_settings


def _as_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


async def run_smoke_test(workspace: Path, allow_login: bool) -> dict[str, Any]:
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"workspace": str(workspace)}

    # The bundled runtime expects HOME even on Windows. Set it only for the
    # child process; do not change the machine or user environment.
    settings = load_settings()
    runtime_env = {
        "HOME": str(settings.codex_home.parent),
        "CODEX_HOME": str(settings.codex_home),
    }
    async with AsyncCodex(CodexConfig(cwd=str(workspace), env=runtime_env)) as client:
        account = await client.account()
        result["account_before_login"] = _as_jsonable(account)

        account_data = _as_jsonable(account)
        if isinstance(account_data, dict) and account_data.get("account") is None:
            if not allow_login:
                result["login_required"] = True
                return result
            login = await client.login_chatgpt()
            result["login_url"] = login.auth_url
            webbrowser.open(login.auth_url)
            await login.wait()
            account = await client.account(refresh_token=True)
            result["account_after_login"] = _as_jsonable(account)

        models = await client.models()
        models_data = _as_jsonable(models)
        result["models"] = models_data

        thread = await client.thread_start(
            cwd=str(workspace),
            sandbox=Sandbox.workspace_write,
            approval_mode=ApprovalMode.auto_review,
        )
        result["thread_id"] = thread.id
        turn = await thread.run(
            "Create a UTF-8 text file named sdk-smoke-ok.txt in the current "
            "workspace containing exactly: CODEX_SDK_SMOKE_OK",
            cwd=str(workspace),
            sandbox=Sandbox.workspace_write,
            approval_mode=ApprovalMode.auto_review,
        )
        result["final_response"] = _as_jsonable(turn)

    output = workspace / "sdk-smoke-ok.txt"
    result["output_exists"] = output.is_file()
    result["output_text"] = output.read_text(encoding="utf-8") if output.is_file() else None
    result["passed"] = result["output_text"] == "CODEX_SDK_SMOKE_OK"
    return result


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--allow-login", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(run_smoke_test(args.workspace, args.allow_login)),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
