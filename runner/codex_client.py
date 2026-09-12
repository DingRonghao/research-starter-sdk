"""Long-lived AsyncCodex client wrapper with fixed safety defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openai_codex import ApprovalMode, AsyncCodex, CodexConfig, Sandbox, SkillInput, TextInput
from openai_codex.generated.v2_all import GetAccountRateLimitsResponse, ReasoningEffort


def _json(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json", by_alias=True)


async def codex_status(codex_home: Path, project_root: Path) -> dict[str, Any]:
    env = {"HOME": str(codex_home.parent), "CODEX_HOME": str(codex_home)}
    async with AsyncCodex(CodexConfig(cwd=str(project_root), env=env)) as client:
        account = _json(await client.account())
        errors = {}
        try:
            models = _json(await client.models())
        except Exception as exc:
            models = {"data": []}
            errors["models"] = type(exc).__name__
        try:
            usage = _json(await client._client.request_with_retry_on_overload(
                "account/rateLimits/read", None, response_model=GetAccountRateLimitsResponse,
            ))
        except Exception as exc:
            usage = {}
            errors["usage"] = type(exc).__name__
    return {"account": account, "models": models, "usage": usage, "errors": errors}


class CodexRunner:
    def __init__(self, codex_home: Path, project_root: Path) -> None:
        env = {"HOME": str(codex_home.parent), "CODEX_HOME": str(codex_home)}
        self._client = AsyncCodex(CodexConfig(cwd=str(project_root), env=env))

    async def __aenter__(self) -> "CodexRunner":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self._client.__aexit__(exc_type, exc, traceback)

    async def run_skill(
        self,
        *,
        skill_name: str,
        skill_path: Path,
        prompt: str,
        cwd: Path,
        thread_id: str | None = None,
        model: str | None = None,
        effort: str | None = None,
    ):
        reasoning_effort = ReasoningEffort(effort) if effort else None
        if thread_id:
            thread = await self._client.thread_resume(
                thread_id,
                cwd=str(cwd),
                sandbox=Sandbox.workspace_write,
                approval_mode=ApprovalMode.auto_review,
            )
        else:
            thread = await self._client.thread_start(
                cwd=str(cwd),
                sandbox=Sandbox.workspace_write,
                approval_mode=ApprovalMode.auto_review,
            )
        result = await thread.run(
            [SkillInput(name=skill_name, path=str(skill_path)), TextInput(prompt)],
            cwd=str(cwd),
            sandbox=Sandbox.workspace_write,
            approval_mode=ApprovalMode.auto_review,
            model=model,
            effort=reasoning_effort,
        )
        return thread.id, result
