"""Append generated slides to a copy of an existing PowerPoint template."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path


def _pptx(path: str, *, existing: bool) -> Path:
    value = Path(path).resolve(strict=existing)
    if value.suffix.lower() != ".pptx":
        raise ValueError(f"Expected a .pptx path: {value}")
    return value


def append_slides(template_arg: str, content_arg: str, output_arg: str) -> Path:
    template = _pptx(template_arg, existing=True)
    content = _pptx(content_arg, existing=True)
    output = _pptx(output_arg, existing=False)
    if output in {template, content}:
        raise ValueError("Output must not overwrite the template or generated content deck")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, output)

    import win32com.client  # type: ignore[import-untyped]

    application = win32com.client.DispatchEx("PowerPoint.Application")
    presentation = None
    try:
        application.DisplayAlerts = 0
        presentation = application.Presentations.Open(str(output), False, False, False)
        before = presentation.Slides.Count
        inserted = presentation.Slides.InsertFromFile(str(content), before)
        if inserted < 1:
            raise RuntimeError("PowerPoint did not append any content slides")
        presentation.Save()
    finally:
        if presentation is not None:
            presentation.Close()
        application.Quit()

    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or "ppt/presentation.xml" not in archive.namelist():
            raise RuntimeError("Merged PowerPoint failed package validation")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(append_slides(args.template, args.content, args.output))


if __name__ == "__main__":
    main()
