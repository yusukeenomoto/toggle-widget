"""アプリのアイコンを作る (macOS で実行する)。

    pip install resvg-py pillow
    python assets/build_icons.py                    # assets/icon.svg から作り直す
    python assets/build_icons.py ~/Desktop/toggle.svg   # Illustrator から書き出した SVG を取り込んでから作る

取り込むときは、書き出した SVG を次のように整えて assets/icon.svg に保存する (元のファイルは変えない):
- 埋め込み画像 (下絵など) を外す
- 本体 (角丸のある正方形のうち一番大きいもの) がアイコン格子 (1024 のうち 824) に来るよう切り出す
- 絵全体を本体の角丸四角で切り取る (アートボードからはみ出した部分が透明の隅に出ないように)

作るもの (どれもリポジトリに入れておき、ビルド時には作り直さない):
- assets/icon.png   1024x1024
- assets/icon.icns  macOS の .app 用 (iconutil で作る)
- assets/icon.ico   Windows の .exe とウインドウ用

縮小でぼやけないよう、サイズごとに SVG から直接描く。
"""
import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import resvg_py
from PIL import Image

HERE = Path(__file__).resolve().parent
ICON_SVG = HERE / "icon.svg"

ICNS_SIZES = [16, 32, 128, 256, 512]          # それぞれ @1x と @2x を作る
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def import_svg(source: Path) -> str:
    """Illustrator などから書き出した SVG を、アイコン用に整えた文字列にする。"""
    svg = source.read_text(encoding="utf-8")
    svg = re.sub(r"\s*<image\b[^>]*/>", "", svg)

    # 本体 = 角丸のある正方形のうち一番大きいもの
    body = None
    for attrs in re.findall(r"<rect\b([^>]*)/>", svg):
        a = dict(re.findall(r'([\w:-]+)="([^"]*)"', attrs))
        if "rx" not in a or "transform" in a or a.get("width") != a.get("height"):
            continue
        if body is None or float(a["width"]) > float(body["width"]):
            body = a
    if body is None:
        raise SystemExit("本体の角丸四角 (rx のある正方形の rect) が見つかりません")
    x, y, w = float(body["x"]), float(body["y"]), float(body["width"])
    rx, ry = body["rx"], body.get("ry", body["rx"])

    size = w * 1024 / 824
    view_box = f"{x + w / 2 - size / 2:.3f} {y + w / 2 - size / 2:.3f} {size:.3f} {size:.3f}"
    svg = re.sub(r'viewBox="[^"]*"', f'viewBox="{view_box}"', svg, count=1)

    clip = (f'<clipPath id="icon-body"><rect x="{x}" y="{y}" width="{w}" height="{w}" '
            f'rx="{rx}" ry="{ry}"/></clipPath>')
    if "</defs>" in svg:
        svg = svg.replace("</defs>", f"  {clip}\n  </defs>", 1)
        head, rest = svg.split("</defs>", 1)
        head += "</defs>"
    else:
        m = re.search(r"<svg\b[^>]*>", svg)
        head, rest = svg[:m.end()] + f"\n  <defs>{clip}</defs>", svg[m.end():]
    body_part, tail = rest.rsplit("</svg>", 1)
    return f'{head}\n  <g clip-path="url(#icon-body)">{body_part}  </g>\n</svg>{tail}'


def render(svg: str, size: int) -> Image.Image:
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=size, height=size))
    return Image.open(io.BytesIO(png)).convert("RGBA")


def main() -> None:
    if len(sys.argv) > 1:
        ICON_SVG.write_text(import_svg(Path(sys.argv[1]).expanduser()), encoding="utf-8")
        print(f"取り込み: {sys.argv[1]} -> {ICON_SVG.name}")
    svg = ICON_SVG.read_text(encoding="utf-8")

    def draw(size: int) -> Image.Image:
        return render(svg, size)

    draw(1024).save(HERE / "icon.png")

    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "icon.iconset"
        iconset.mkdir()
        for size in ICNS_SIZES:
            draw(size).save(iconset / f"icon_{size}x{size}.png")
            draw(size * 2).save(iconset / f"icon_{size}x{size}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(HERE / "icon.icns")],
                       check=True)

    images = [draw(size) for size in ICO_SIZES]
    images[-1].save(HERE / "icon.ico", format="ICO",
                    sizes=[(s, s) for s in ICO_SIZES], append_images=images[:-1])
    print("作成:", ", ".join(p.name for p in sorted(HERE.glob("icon.*"))))


if __name__ == "__main__":
    if shutil.which("iconutil") is None:
        raise SystemExit("iconutil が見つかりません。macOS で実行してください。")
    main()
