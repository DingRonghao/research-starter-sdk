"""External model-provider metadata, overrides, and Windows-local secrets."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import win32crypt

OPENAI_PROVIDER = "openai"
DEEPSEEK_PROVIDER = "deepseek"
DEEPSEEK_MODEL = "deepseek-flash"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_REASONING_EFFORTS = ("none", "low", "high", "max")
KIMI_PROVIDER = "kimi"
KIMI_MODEL = "kimi-k3"
KIMI_BASE_URL = "https://api.moonshot.ai/v1"
KIMI_REASONING_EFFORTS = ("low", "high", "max")


@dataclass(frozen=True)
class ProviderSpec:
    provider: str
    name: str
    model: str
    model_name: str
    base_url: str
    env_key: str
    reasoning_efforts: tuple[str, ...]
    default_effort: str
    catalog_file: str
    context_window: int
    description: str
    usage_note: str

    def public(self, configured: bool = False) -> dict:
        return {
            "provider": self.provider,
            "name": self.name,
            "model": self.model,
            "model_name": self.model_name,
            "reasoning_efforts": list(self.reasoning_efforts),
            "default_effort": self.default_effort,
            "description": self.description,
            "usage_note": self.usage_note,
            "configured": configured,
        }


EXTERNAL_PROVIDERS = {
    DEEPSEEK_PROVIDER: ProviderSpec(
        DEEPSEEK_PROVIDER, "DeepSeek", DEEPSEEK_MODEL, "DeepSeek Flash（当前 V4.1 Flash）",
        DEEPSEEK_BASE_URL, "DEEPSEEK_API_KEY", DEEPSEEK_REASONING_EFFORTS, "high",
        "deepseek-models.json", 1048576, "DeepSeek Flash 及其四档推理等级，不需要 Codex 付费账户。",
        "DeepSeek API 用量请在 DeepSeek 控制台查看。",
    ),
    KIMI_PROVIDER: ProviderSpec(
        KIMI_PROVIDER, "Kimi", KIMI_MODEL, "Kimi K3",
        KIMI_BASE_URL, "KIMI_API_KEY", KIMI_REASONING_EFFORTS, "high",
        "kimi-models.json", 1048576, "Kimi K3 原生接入 Codex Responses API，支持 1M 上下文和视觉输入。",
        "Kimi API 用量请在 Kimi 开放平台查看。",
    ),
}


def provider_spec(provider: str) -> ProviderSpec:
    try:
        return EXTERNAL_PROVIDERS[provider]
    except KeyError as exc:
        raise ValueError(f"不支持的模型提供方：{provider}") from exc


def external_provider_data(project_root: Path) -> list[dict]:
    return [spec.public(provider_configured(project_root, spec.provider)) for spec in EXTERNAL_PROVIDERS.values()]


def _secret_path(project_root: Path, provider: str) -> Path:
    provider_spec(provider)
    return project_root / ".runtime" / "secrets" / f"{provider}-api-key.bin"


def provider_configured(project_root: Path, provider: str) -> bool:
    return _secret_path(project_root, provider).is_file()


def save_provider_key(project_root: Path, provider: str, api_key: str) -> None:
    spec = provider_spec(provider)
    key = api_key.strip()
    if not key:
        raise ValueError(f"{spec.name} API Key 不能为空")
    try:
        encrypted = win32crypt.CryptProtectData(
            key.encode("utf-8"), f"Research Starter {spec.name}", None, None, None, 0,
        )
    except Exception as exc:
        raise ValueError(
            "Windows 无法加密 API Key。请关闭由其他工具代为启动的服务，再直接双击 Start Research Starter.cmd。"
        ) from exc
    path = _secret_path(project_root, provider)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(encrypted)
    temporary.replace(path)


def load_provider_key(project_root: Path, provider: str) -> str:
    spec = provider_spec(provider)
    path = _secret_path(project_root, provider)
    if not path.is_file():
        raise ValueError(f"尚未配置 {spec.name} API Key")
    try:
        return win32crypt.CryptUnprotectData(path.read_bytes(), None, None, None, 0)[1].decode("utf-8")
    except Exception as exc:
        raise ValueError(f"{spec.name} API Key 无法由当前 Windows 用户解密，请重新填写") from exc


def delete_provider_key(project_root: Path, provider: str) -> bool:
    path = _secret_path(project_root, provider)
    if not path.exists():
        return False
    path.unlink()
    return True


def test_provider_key(provider: str, api_key: str, timeout: float = 15) -> dict:
    spec = provider_spec(provider)
    if not api_key.strip():
        raise ValueError(f"{spec.name} API Key 不能为空")
    request = urllib.request.Request(
        f"{spec.base_url}/models",
        headers={"Authorization": f"Bearer {api_key.strip()}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise ValueError(f"{spec.name} API Key 无效或没有访问权限") from exc
        raise ValueError(f"{spec.name} 服务返回 HTTP {exc.code}") from exc
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ValueError(f"暂时无法连接 {spec.name}，请检查网络后重试") from exc
    models = {item.get("id") for item in payload.get("data", []) if isinstance(item, dict)}
    return {"reachable": True, "model_available": spec.model in models, "models": sorted(m for m in models if m)}


def provider_overrides(provider: str, project_root: Path | None = None) -> tuple[str, ...]:
    if provider == OPENAI_PROVIDER:
        return ()
    spec = provider_spec(provider)
    root = (project_root or Path(__file__).resolve().parent.parent).resolve()
    catalog = json.dumps(str(root / "resources" / spec.catalog_file))
    return (
        f'model="{spec.model}"',
        f'model_provider="{spec.provider}"',
        'preferred_auth_method="apikey"',
        'forced_login_method="api"',
        f'model_reasoning_effort="{spec.default_effort}"',
        f"model_context_window={spec.context_window}",
        f"model_catalog_json={catalog}",
        f'model_providers.{spec.provider}.name="{spec.name}"',
        f'model_providers.{spec.provider}.base_url="{spec.base_url}"',
        f'model_providers.{spec.provider}.env_key="{spec.env_key}"',
        f'model_providers.{spec.provider}.wire_api="responses"',
        f"model_providers.{spec.provider}.requires_openai_auth=false",
    )


# Compatibility helpers keep existing callers and encrypted DeepSeek data working.
def deepseek_configured(project_root: Path) -> bool:
    return provider_configured(project_root, DEEPSEEK_PROVIDER)


def save_deepseek_key(project_root: Path, api_key: str) -> None:
    save_provider_key(project_root, DEEPSEEK_PROVIDER, api_key)


def load_deepseek_key(project_root: Path) -> str:
    return load_provider_key(project_root, DEEPSEEK_PROVIDER)


def delete_deepseek_key(project_root: Path) -> bool:
    return delete_provider_key(project_root, DEEPSEEK_PROVIDER)


def test_deepseek_key(api_key: str, timeout: float = 15) -> dict:
    return test_provider_key(DEEPSEEK_PROVIDER, api_key, timeout)
