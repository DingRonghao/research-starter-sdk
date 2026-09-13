"""Model-provider settings and Windows-local secret storage."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import win32crypt

OPENAI_PROVIDER = "openai"
DEEPSEEK_PROVIDER = "deepseek"
DEEPSEEK_MODEL = "deepseek-flash"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_REASONING_EFFORTS = ("none", "low", "high", "max")


def _secret_path(project_root: Path) -> Path:
    return project_root / ".runtime" / "secrets" / "deepseek-api-key.bin"


def deepseek_configured(project_root: Path) -> bool:
    return _secret_path(project_root).is_file()


def save_deepseek_key(project_root: Path, api_key: str) -> None:
    key = api_key.strip()
    if not key:
        raise ValueError("DeepSeek API Key 不能为空")
    try:
        encrypted = win32crypt.CryptProtectData(
            key.encode("utf-8"), "Research Starter DeepSeek", None, None, None, 0,
        )
    except Exception as exc:
        raise ValueError(
            "Windows 无法加密 API Key。请关闭由其他工具代为启动的服务，再直接双击 Start Research Starter.cmd。"
        ) from exc
    path = _secret_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(encrypted)
    temporary.replace(path)


def load_deepseek_key(project_root: Path) -> str:
    path = _secret_path(project_root)
    if not path.is_file():
        raise ValueError("尚未配置 DeepSeek API Key")
    try:
        return win32crypt.CryptUnprotectData(path.read_bytes(), None, None, None, 0)[1].decode("utf-8")
    except Exception as exc:
        raise ValueError("DeepSeek API Key 无法由当前 Windows 用户解密，请重新填写") from exc


def delete_deepseek_key(project_root: Path) -> bool:
    path = _secret_path(project_root)
    if not path.exists():
        return False
    path.unlink()
    return True


def test_deepseek_key(api_key: str, timeout: float = 15) -> dict:
    if not api_key.strip():
        raise ValueError("DeepSeek API Key 不能为空")
    request = urllib.request.Request(
        f"{DEEPSEEK_BASE_URL}/models",
        headers={"Authorization": f"Bearer {api_key.strip()}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise ValueError("DeepSeek API Key 无效或没有访问权限") from exc
        raise ValueError(f"DeepSeek 服务返回 HTTP {exc.code}") from exc
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ValueError("暂时无法连接 DeepSeek，请检查网络后重试") from exc
    models = {item.get("id") for item in payload.get("data", []) if isinstance(item, dict)}
    return {"reachable": True, "model_available": DEEPSEEK_MODEL in models, "models": sorted(m for m in models if m)}


def provider_overrides(provider: str, project_root: Path | None = None) -> tuple[str, ...]:
    if provider != DEEPSEEK_PROVIDER:
        return ()
    root = (project_root or Path(__file__).resolve().parent.parent).resolve()
    catalog = json.dumps(str(root / "resources" / "deepseek-models.json"))
    return (
        'model="deepseek-flash"',
        'model_provider="deepseek"',
        'preferred_auth_method="apikey"',
        'forced_login_method="api"',
        'model_reasoning_effort="high"',
        f"model_catalog_json={catalog}",
        'model_providers.deepseek.name="DeepSeek"',
        f'model_providers.deepseek.base_url="{DEEPSEEK_BASE_URL}"',
        'model_providers.deepseek.env_key="DEEPSEEK_API_KEY"',
        'model_providers.deepseek.wire_api="responses"',
        "model_providers.deepseek.requires_openai_auth=false",
    )
