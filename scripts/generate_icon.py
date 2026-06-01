"""生成桌面 app 图标 — 蓝绿渐变 + 白色 ψ。

只在第一次/换图标时跑一次，结果存到 assets/app.ico（多尺寸）+ app.png。
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent
ASSETS = HERE / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 圆角矩形背景：从左上 #0EA5E9（青蓝）到右下 #6366F1（靛紫）—
    # 区别于 learning-system 的纯紫，psy 偏'冷静理性'的蓝绿
    radius = int(size * 0.22)
    # 渐变填充：逐行画
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(0x0E + (0x63 - 0x0E) * t)
        g = int(0xA5 + (0x66 - 0xA5) * t)
        b = int(0xE9 + (0xF1 - 0xE9) * t)
        d.line([(0, y), (size, y)], fill=(r, g, b, 255))
    # 加圆角 mask
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    img.putalpha(mask)

    # 中心 ψ 字符（希腊字母 Psi，心理学常用 logo）
    d2 = ImageDraw.Draw(img)
    target_text = "Ψ"  # Ψ 大写更醒目
    # 选字体：Windows 自带的 Segoe UI / Arial 都能渲染希腊字母
    font_size = int(size * 0.62)
    font = None
    for name in ("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(name, font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = d2.textbbox((0, 0), target_text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # textbbox 的左上偏移：bbox[0]/bbox[1] 通常不为 0
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1]
    # 软阴影
    d2.text((x + size * 0.012, y + size * 0.012), target_text, font=font, fill=(0, 0, 0, 90))
    d2.text((x, y), target_text, font=font, fill=(255, 255, 255, 245))

    return img


def main():
    sizes = [256, 128, 64, 48, 32, 16]
    images = [make_icon(s) for s in sizes]

    ico_path = ASSETS / "app.ico"
    png_path = ASSETS / "app.png"

    images[0].save(png_path, "PNG")
    # ICO 多尺寸
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print(f"OK: {ico_path}")
    print(f"OK: {png_path}")


if __name__ == "__main__":
    main()
