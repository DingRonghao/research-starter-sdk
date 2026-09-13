"""Start the local-only web server and open the default browser."""

from __future__ import annotations

import os
import threading
import time
import webbrowser

import uvicorn
from openai_codex import AsyncCodex, CodexConfig

from runner.config import load_settings
from runner.instance import instance_info, probe_instance, select_port


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
    settings = load_settings()
    identity = instance_info(settings.project_root)
    port, already_running = select_port(identity)
    url = f"http://127.0.0.1:{port}/?instance={identity.instance_id}"
    if already_running:
        webbrowser.open(url)
        return
    os.environ["RESEARCH_STARTER_INSTANCE_ID"] = identity.instance_id
    os.environ["RESEARCH_STARTER_CHANNEL"] = identity.channel
    os.environ["RESEARCH_STARTER_PORT"] = str(port)

    def open_when_ready() -> None:
        for _ in range(60):
            if probe_instance(port, identity.instance_id):
                webbrowser.open(url)
                return
            time.sleep(0.25)
    # Always make Settings reachable, including when authentication is unavailable.
    # The web login manager owns the official browser-login lifecycle.
    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run("web.app:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
