from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "linkedin"
SOURCE = OUT / "source" / "incident-response-backdrop.png"
SCENARIOS = ROOT / "docs" / "screenshots" / "01-scenarios.png"
APPROVAL = ROOT / "docs" / "screenshots" / "02-approval-gate.png"
HISTORY = ROOT / "docs" / "screenshots" / "03-verified-audit-trail.png"

W, H = 1200, 627
NAVY = "#06111f"
PANEL = "#0b1b2e"
WHITE = "#f5f8fc"
MUTED = "#9db0c5"
CYAN = "#42c9f5"
TEAL = "#34d6aa"
AMBER = "#f5ba55"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def rounded_image(image: Image.Image, size: tuple[int, int], radius: int) -> Image.Image:
    fitted = ImageOps.fit(image.convert("RGB"), size, method=Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    result.paste(fitted.convert("RGBA"), (0, 0), mask)
    return result


def add_brand(draw: ImageDraw.ImageDraw) -> None:
    draw.text((58, 42), "INCIDENT", font=font(21, True), fill=WHITE)
    draw.text((158, 42), "//", font=font(21, True), fill=CYAN)
    draw.text((181, 42), "COPILOT", font=font(21, True), fill=WHITE)


def add_pill(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, color: str) -> None:
    draw.rounded_rectangle(box, radius=18, fill="#0a2034", outline=color, width=2)
    text_box = draw.textbbox((0, 0), text, font=font(15, True))
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    x = box[0] + ((box[2] - box[0]) - text_width) // 2
    y = box[1] + ((box[3] - box[1]) - text_height) // 2 - 2
    draw.text((x, y), text, font=font(15, True), fill=color)


def make_cover() -> None:
    backdrop = ImageOps.fit(Image.open(SOURCE).convert("RGB"), (W, H), method=Image.Resampling.LANCZOS)
    backdrop = ImageEnhance.Contrast(backdrop).enhance(1.08)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pixels = overlay.load()
    for x in range(W):
        alpha = int(238 - (190 * x / W))
        for y in range(H):
            vertical = int(20 * abs((y / H) - 0.5) * 2)
            pixels[x, y] = (3, 12, 24, min(255, alpha + vertical))
    canvas = Image.alpha_composite(backdrop.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(canvas)

    add_brand(draw)
    draw.rounded_rectangle((927, 39, 1143, 78), radius=19, fill="#0a2034", outline="#1b6881", width=2)
    draw.text((954, 49), "PYTHON + JAVA", font=font(15, True), fill=CYAN)

    draw.text((58, 136), "AI-assisted incident response,", font=font(47, True), fill=WHITE)
    draw.text((58, 193), "with humans in command.", font=font(47, True), fill=WHITE)
    draw.text((61, 273), "Prometheus detects the signal. The copilot gathers evidence,", font=font(21), fill="#c2cfdd")
    draw.text((61, 306), "recommends a safe response and verifies recovery.", font=font(21), fill="#c2cfdd")

    stages = [
        ("DETECT", CYAN, 58, 165),
        ("INVESTIGATE", CYAN, 181, 322),
        ("APPROVE", AMBER, 338, 465),
        ("VERIFY", TEAL, 481, 592),
    ]
    for label, color, left, right in stages:
        add_pill(draw, (left, 393, right, 435), label, color)
    for x in (172, 329, 472):
        draw.line((x - 2, 414, x + 6, 414), fill="#52708a", width=2)
        draw.polygon(((x + 6, 409), (x + 14, 414), (x + 6, 419)), fill="#52708a")

    draw.text((59, 512), "PROMETHEUS  •  FASTAPI  •  POSTGRESQL  •  STREAMLIT  •  DOCKER", font=font(17, True), fill=MUTED)
    draw.text((59, 551), "A production-minded AI engineering portfolio project", font=font(18), fill="#d4dce6")
    canvas.convert("RGB").save(OUT / "01-incident-copilot-cover.png", quality=96)


def crop_focus(image_path: Path, crop: tuple[int, int, int, int]) -> Image.Image:
    image = Image.open(image_path).convert("RGB")
    return image.crop(crop)


def refresh_approval_screenshot_copy() -> None:
    """Keep the checked-in product screenshot aligned with the approval form copy."""
    image = Image.open(APPROVAL).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((1495, 1110, 2700, 1168), fill=(6, 16, 29))
    draw.text(
        (1522, 1124),
        "Reason for your decision",
        font=font(31),
        fill=(190, 203, 219),
    )
    draw.rectangle((1545, 1194, 2645, 1295), fill=(12, 27, 44))
    placeholder_font = font(23)
    draw.text(
        (1560, 1202),
        "Approve: Evidence supports rollback; release timing and healthy dependencies confirm it.",
        font=placeholder_font,
        fill=(132, 149, 168),
    )
    draw.text(
        (1560, 1243),
        "Reject: Dependency health is not confirmed; gather more evidence first.",
        font=placeholder_font,
        fill=(132, 149, 168),
    )
    image.save(APPROVAL, quality=96)


def make_feature() -> None:
    raw_backdrop = ImageOps.fit(Image.open(SOURCE).convert("RGB"), (W, H), method=Image.Resampling.LANCZOS)
    raw_backdrop = raw_backdrop.filter(ImageFilter.GaussianBlur(18))
    wash = Image.new("RGBA", (W, H), (3, 12, 24, 220))
    canvas = Image.alpha_composite(raw_backdrop.convert("RGBA"), wash)
    draw = ImageDraw.Draw(canvas)
    add_brand(draw)

    draw.text((58, 96), "Guardrails before action. Proof after.", font=font(40, True), fill=WHITE)
    draw.text((60, 151), "The model can recommend a change—but cannot execute it without an authorized human.", font=font(19), fill="#b8c7d6")

    approval_crop = crop_focus(APPROVAL, (1390, 250, 2860, 1510))
    history_crop = crop_focus(HISTORY, (1380, 180, 2860, 1880))
    left = rounded_image(approval_crop, (514, 342), 18)
    right = rounded_image(history_crop, (514, 342), 18)

    for x, card, label, accent in [
        (58, left, "01  HUMAN APPROVAL", AMBER),
        (628, right, "02  VERIFIED AUDIT TRAIL", TEAL),
    ]:
        draw.rounded_rectangle((x - 2, 215, x + 516, 564), radius=20, fill=PANEL, outline="#23415e", width=2)
        canvas.alpha_composite(card, (x, 220))
        draw.rounded_rectangle((x + 18, 199, x + 225, 231), radius=16, fill="#0c2238", outline=accent, width=2)
        draw.text((x + 34, 207), label, font=font(13, True), fill=accent)

    draw.text((58, 586), "Exact tool arguments", font=font(14, True), fill=CYAN)
    draw.text((245, 586), "•", font=font(14, True), fill="#57728b")
    draw.text((267, 586), "Role-aware approval", font=font(14, True), fill=AMBER)
    draw.text((446, 586), "•", font=font(14, True), fill="#57728b")
    draw.text((468, 586), "Idempotent execution", font=font(14, True), fill=CYAN)
    draw.text((658, 586), "•", font=font(14, True), fill="#57728b")
    draw.text((680, 586), "Deterministic recovery checks", font=font(14, True), fill=TEAL)
    canvas.convert("RGB").save(OUT / "02-approval-and-audit.png", quality=96)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for required in (SOURCE, SCENARIOS, APPROVAL, HISTORY):
        if not required.exists():
            raise FileNotFoundError(required)
    refresh_approval_screenshot_copy()
    make_cover()
    make_feature()
    print("Created LinkedIn assets in", OUT)
