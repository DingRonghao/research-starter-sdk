"""Start the local-only web server and open the default browser."""

from __future__ import annotations

import asyncio
import threading
import urllib.request
import webbrowser

import uvicorn
from openai_codex import AsyncCodex, CodexConfig

from runner.config import load_settings


async def ensure_codex_login() -> None:
    settings = load_settings()
    config = CodexConfig(
        cwd=str(settings.project_root),
        env={"HOME": str(settings.codex_home.parent), "CODEX_HOME": str(settings.codex_home)},
    )
    async with AsyncCodex(config) as client:
        account = await client.account()
        if account.model_dump(mode="json").get("account") is None:
            login = await client.login_chatgpt()
            webbrowser.open(login.auth_url)
            await login.wait()


def main() -> None:
    url = "http://127.0.0.1:8765"
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
            if response.status == 200:
                webbrowser.open(url)
                return
    except OSError:
        pass
    # Always make Settings reachable, including when authentication is unavailable.
    # The web login manager owns the official browser-login lifecycle.
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run("web.app:app", host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    main()
