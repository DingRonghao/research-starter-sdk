from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import zipfile


def normalized_pptx_bytes(path: Path) -> bytes:
    """Return a renderer-friendly copy without changing the source PPTX."""
    with zipfile.ZipFile(path, "r") as source:
        files = {info.filename: source.read(info.filename) for info in source.infolist() if not info.is_dir()}

    changed = False
    for name, data in list(files.items()):
        if re.search(r"\.(?:xml|rels)$", name, re.I) and data.startswith(b"\xef\xbb\xbf"):
            files[name] = data[3:]
            changed = True

    legacy_charts = [name for name in files if re.fullmatch(r"ppt/slides/charts/[^/]+\.xml", name, re.I)]
    for chart_path in legacy_charts:
        filename = chart_path.rsplit("/", 1)[-1]
        files[f"ppt/charts/{filename}"] = files[chart_path]
        rels_source = f"ppt/slides/charts/_rels/{filename}.rels"
        if rels_source in files:
            files[f"ppt/charts/_rels/{filename}.rels"] = files[rels_source].replace(
                b'Target="../../embeddings/', b'Target="../embeddings/'
            )
        changed = True

    aliases: dict[str, str] = {}
    for name, data in list(files.items()):
        if not re.fullmatch(r"ppt/media/[^/]+\.(?:png|jpe?g)", name, re.I):
            continue
        head = data[:256].decode("utf-8-sig", errors="ignore").lstrip()
        if not (head.startswith("<svg") or (head.startswith("<?xml") and "<svg" in head)):
            continue
        alias = re.sub(r"\.(?:png|jpe?g)$", ".svg", name, flags=re.I)
        files[alias] = data
        aliases[name.rsplit("/", 1)[-1]] = alias.rsplit("/", 1)[-1]
        changed = True

    for name, data in list(files.items()):
        if not re.search(r"_rels/[^/]+\.rels$", name, re.I):
            continue
        text = data.decode("utf-8-sig")
        original = text
        text = re.sub(
            r'Target="(?:/ppt/slides/charts/|\.\./charts/|charts/)([^"/]+\.xml)"',
            r'Target="../charts/\1"',
            text,
            flags=re.I,
        )
        for old, new in aliases.items():
            text = re.sub(rf'(Target="[^"]*){re.escape(old)}(")', rf"\1{new}\2", text)
        if text != original:
            files[name] = text.encode("utf-8")
            changed = True

    if not changed:
        return path.read_bytes()

    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in files.items():
            target.writestr(name, data)
    return output.getvalue()
