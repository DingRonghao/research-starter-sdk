"""Keep the SDK connection alive until official browser login completes."""
import asyncio
from openai_codex import AsyncCodex, CodexConfig


class LoginManager:
    def __init__(self):
        self.task = None
        self.state = {"status": "idle"}

    @property
    def active(self):
        return self.task is not None and not self.task.done()

    async def start(self, settings):
        if self.active:
            return dict(self.state)
        ready = asyncio.Event()
        self.state = {"status": "starting"}
        self.task = asyncio.create_task(self._run(settings, ready))
        try:
            await asyncio.wait_for(ready.wait(), timeout=30)
        except TimeoutError:
            await self.cancel()
            self.state = {"status": "failed", "error": "登录服务启动超时，请重试"}
        return dict(self.state)

    async def _run(self, settings, ready):
        env = {"HOME": str(settings.codex_home.parent), "CODEX_HOME": str(settings.codex_home)}
        try:
            async with AsyncCodex(CodexConfig(cwd=str(settings.project_root), env=env)) as client:
                handle = await client.login_chatgpt()
                self.state = {"status": "waiting", "auth_url": handle.auth_url}
                ready.set()
                try:
                    result = await asyncio.wait_for(handle.wait(), timeout=600)
                    self.state = {"status": "completed" if result.success else "failed", "error": result.error}
                except (asyncio.CancelledError, TimeoutError):
                    await handle.cancel()
                    self.state = {"status": "cancelled"}
        except asyncio.CancelledError:
            self.state = {"status": "cancelled"}
        except Exception as exc:
            self.state = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        finally:
            ready.set()

    async def cancel(self):
        if self.active:
            self.task.cancel()
            await self.task
        return dict(self.state)
