"""生成 Android TV 所需密度特定的 raster 图标（PNG）"""
import os
from PIL import Image, ImageDraw, ImageFont

RES_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "src", "main", "res")

# TV Banner 320x180 dp → 各密度 px 尺寸
BANNER_SIZES = {
    "mdpi": (320, 180),
    "hdpi": (480, 270),
    "xhdpi": (640, 360),
    "xxhdpi": (960, 540),
    "xxxhdpi": (1280, 720),
}

# Launcher 图标 48x48 dp → 各密度 px 尺寸
ICON_SIZES = {
    "mdpi": (48, 48),
    "hdpi": (72, 72),
    "xhdpi": (96, 96),
    "xxhdpi": (144, 144),
    "xxxhdpi": (192, 192),
}

BG_COLOR = (13, 71, 161)  # 深蓝 #0D47A1
FG_COLOR = (255, 255, 255)  # 白色


def draw_play_triangle(draw, img_w, img_h, scale):
    """在图片中央绘制播放三角形"""
    cx, cy = img_w // 2, img_h // 2
    size = min(img_w, img_h) * 0.35
    # 等边三角形顶点（向右偏一点更像播放按钮）
    pts = [
        (cx - size * 0.35, cy - size * 0.58),
        (cx - size * 0.35, cy + size * 0.58),
        (cx + size * 0.55, cy),
    ]
    draw.polygon(pts, fill=FG_COLOR)


def generate_icon(sizes, filename, draw_fn):
    """为各密度生成图标"""
    for density, (w, h) in sizes.items():
        mipmap_dir = os.path.join(RES_DIR, f"mipmap-{density}")
        os.makedirs(mipmap_dir, exist_ok=True)

        img = Image.new("RGBA", (w, h), BG_COLOR)
        draw = ImageDraw.Draw(img)
        draw_fn(draw, w, h, 1.0)

        out_path = os.path.join(mipmap_dir, filename)
        img.save(out_path, "PNG")
        print(f"  OK {density}: {w}x{h} -> {out_path}")


if __name__ == "__main__":
    print("生成 TV Banner 图标...")
    generate_icon(BANNER_SIZES, "ic_banner.png", draw_play_triangle)

    print("生成 Launcher 图标...")
    generate_icon(ICON_SIZES, "ic_launcher.png", draw_play_triangle)

    print("\nAll icons generated!")
