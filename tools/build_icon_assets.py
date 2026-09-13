"""Build reproducible web and Windows icon assets from the supplied source PNG."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def _content_square(source: Image.Image) -> Image.Image:
    image = source.convert("RGBA")
    alpha_box = image.getchannel("A").getbbox()
    if alpha_box is None:
        raise ValueError("Icon source has no visible pixels")
    content = image.crop(alpha_box)
    side = max(content.size)
    margin = max(24, round(side * 0.09))
    square = Image.new("RGBA", (side + margin * 2, side + margin * 2), (0, 0, 0, 0))
    square.alpha_composite(content, ((square.width - content.width) // 2, (square.height - content.height) // 2))
    return square


def build(source_path: Path, project_root: Path) -> None:
    source = Image.open(source_path)
    mark = _content_square(source)

    web_icon = mark.resize((512, 512), Image.Resampling.LANCZOS)
    web_path = project_root / "web" / "static" / "app-icon.png"
    web_path.parent.mkdir(parents=True, exist_ok=True)
    web_icon.save(web_path, optimize=True)

    size = 1024
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    inset = 26
    draw.rounded_rectangle(
        (inset, inset, size - inset, size - inset),
        radius=210,
        fill=(246, 244, 237, 255),
        outline=(218, 215, 205, 255),
        width=10,
    )
    fitted = mark.copy()
    fitted.thumbnail((820, 820), Image.Resampling.LANCZOS)
    canvas.alpha_composite(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2))

    ico_path = project_root / "assets" / "app-icon.ico"
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(ico_path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    canvas.resize((256, 256), Image.Resampling.LANCZOS).save(
        project_root / "web" / "static" / "favicon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    build(args.source.resolve(strict=True), args.project_root.resolve(strict=True))


if __name__ == "__main__":
    main()
