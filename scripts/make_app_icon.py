from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> None:
    output_path = Path("assets/app_icon.ico")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images = [draw_icon(size) for size in SIZES]
    images[-1].save(output_path, sizes=[(size, size) for size in SIZES], append_images=images[:-1])
    print(output_path)


def draw_icon(size: int) -> Image.Image:
    scale = size / 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    radius = round(38 * scale)
    draw.rounded_rectangle(
        [0, 0, size - 1, size - 1],
        radius=radius,
        fill=(20, 112, 74, 255),
        outline=(12, 72, 56, 255),
        width=max(1, round(5 * scale)),
    )

    page = [round(58 * scale), round(38 * scale), round(174 * scale), round(166 * scale)]
    fold = round(30 * scale)
    draw.rounded_rectangle(page, radius=round(10 * scale), fill=(248, 252, 248, 255))
    draw.polygon(
        [(page[2] - fold, page[1]), (page[2], page[1] + fold), (page[2] - fold, page[1] + fold)],
        fill=(206, 232, 218, 255),
    )
    draw.line(
        [(page[2] - fold, page[1]), (page[2] - fold, page[1] + fold), (page[2], page[1] + fold)],
        fill=(127, 180, 154, 255),
        width=max(1, round(3 * scale)),
    )

    draw.line(
        [(round(82 * scale), round(132 * scale)), (round(143 * scale), round(78 * scale))],
        fill=(19, 103, 79, 255),
        width=max(2, round(9 * scale)),
    )
    draw.line(
        [(round(98 * scale), round(78 * scale)), (round(159 * scale), round(132 * scale))],
        fill=(19, 103, 79, 255),
        width=max(2, round(9 * scale)),
    )

    tag = [round(66 * scale), round(178 * scale), round(190 * scale), round(221 * scale)]
    draw.rounded_rectangle(tag, radius=round(12 * scale), fill=(8, 56, 44, 255))
    text = "DXF"
    font = load_font(max(9, round(31 * scale)))
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (tag[0] + tag[2] - (bbox[2] - bbox[0])) / 2
    y = (tag[1] + tag[3] - (bbox[3] - bbox[1])) / 2 - round(2 * scale)
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    return image


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


if __name__ == "__main__":
    main()
