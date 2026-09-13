"""Stable identity and port selection for side-by-side app copies."""

from __future__ import annotations

import hashlib
import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstanceInfo:
    instance_id: str
    channel: str
    label: str
    project_root: Path


def instance_info(project_root: Path) -> InstanceInfo:
    root = project_root.resolve()
    digest = hashlib.sha256(str(root).casefold().encode("utf-8")).hexdigest()[:12]
    channel = "development" if (root / ".git").exists() else "release"
    return InstanceInfo(digest, channel, "本地开发版" if channel == "development" else "发布版", root)


def preferred_ports(info: InstanceInfo) -> list[int]:
    if info.channel == "development":
        return [8765, *range(8766, 8786)]
    first = 8800 + int(info.instance_id[:4], 16) % 100
    return [8800 + ((first - 8800 + offset) % 100) for offset in range(100)]


def probe_instance(port: int, instance_id: str, timeout: float = 0.7) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("instance_id") == instance_id
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return False


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def select_port(info: InstanceInfo) -> tuple[int, bool]:
    """Return (port, already_running_for_this exact project root)."""
    for port in preferred_ports(info):
        if probe_instance(port, info.instance_id):
            return port, True
        if port_is_free(port):
            return port, False
    raise RuntimeError("没有可用的本地端口，请关闭不再使用的 Research Starter 实例后重试")
