import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BOT_DIR))
import result_card

COVER_SRC = Path(r"C:\Users\sudhi\.gemini\antigravity\brain\ad320b36-2b75-4f53-86da-c59e8efdf70d\.user_uploaded\media_1794374257110_68708ca5.png")
OUT_PATH = BOT_DIR / "assets" / "promo_poster.png"

def build_promo_poster():
    W, H = 1200, 650
    canvas = result_card.create_radial_gradient_background(W, H, (15, 23, 42), (30, 58, 138), (11, 17, 32)).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # Royal double gold border
    draw.rounded_rectangle([(18, 18), (W - 18, H - 18)], radius=24, outline=(234, 179, 8, 220), width=4)
    draw.rounded_rectangle([(30, 30), (W - 30, H - 30)], radius=18, outline=(234, 179, 8, 90), width=2)

    # Gold corners
    corner_path = BOT_DIR / "assets" / "corner_gold.png"
    if corner_path.exists():
        c_img = Image.open(corner_path).convert("RGBA").resize((95, 95), Image.Resampling.LANCZOS)
        canvas.paste(c_img, (20, 20), c_img)
        canvas.paste(c_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (W - 115, 20), c_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
        canvas.paste(c_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM), (20, H - 115), c_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
        canvas.paste(c_img.transpose(Image.Transpose.ROTATE_180), (W - 115, H - 115), c_img.transpose(Image.Transpose.ROTATE_180))

    font_path = str(BOT_DIR / "segoeuib.ttf")
    f_tag = ImageFont.truetype(font_path, 19)
    f_title = ImageFont.truetype(font_path, 38)
    f_sub = ImageFont.truetype(font_path, 22)
    f_bullet = ImageFont.truetype(font_path, 20)
    f_cta = ImageFont.truetype(font_path, 20)
    f_badge = ImageFont.truetype(font_path, 15)
    f_pill2 = ImageFont.truetype(font_path, 13)
    f_small = ImageFont.truetype(font_path, 15)
    f_app = ImageFont.truetype(font_path, 14)

    # Left Panel: Book Cover Showcase
    card_x1, card_y1, card_x2, card_y2 = 60, 62, 395, 586
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([(card_x1 + 10, card_y1 + 12), (card_x2 + 10, card_y2 + 12)], radius=22, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas = Image.alpha_composite(canvas, shadow)
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle([(card_x1, card_y1), (card_x2, card_y2)], radius=20, fill=(22, 34, 62, 240), outline=(234, 179, 8, 200), width=3)

    # Book cover
    if COVER_SRC.exists():
        cover = Image.open(COVER_SRC).convert("RGBA")
        cw0, ch0 = cover.size
        cover = cover.crop((2, 16, cw0, ch0))
        cw, ch = 265, 375
        cover_res = cover.resize((cw, ch), Image.Resampling.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2, percent=135, threshold=2))
        bx = (card_x1 + card_x2 - cw) // 2
        by = card_y1 + 20
        draw.rounded_rectangle([(bx + 7, by + 7), (bx + cw + 7, by + ch + 7)], radius=8, fill=(226, 232, 240, 230))
        draw.rounded_rectangle([(bx - 3, by - 3), (bx + cw + 3, by + ch + 3)], radius=8, fill=(250, 204, 21, 255))
        canvas.paste(cover_res, (bx, by), cover_res)

    # Pricing & Delivery Pill (Clean Latin typography - 0 tofu boxes!)
    pill_y1 = card_y1 + 405
    draw.rounded_rectangle([(card_x1 + 12, pill_y1), (card_x2 - 12, pill_y1 + 34)], radius=17, fill=(234, 179, 8, 255))
    p_txt = "GUIDE BOOK: ₹350  |  PRACTICE SET: ₹150"
    tw = draw.textlength(p_txt, font=f_badge)
    draw.text(((card_x1 + card_x2 - tw) / 2, pill_y1 + 7), p_txt, font=f_badge, fill=(15, 23, 42))

    pill_y2 = pill_y1 + 42
    draw.rounded_rectangle([(card_x1 + 12, pill_y2), (card_x2 - 12, pill_y2 + 32)], radius=16, fill=(16, 185, 129, 230))
    p_txt2 = "ALL INDIA SPEED POST HOME DELIVERY"
    tw2 = draw.textlength(p_txt2, font=f_pill2)
    draw.text(((card_x1 + card_x2 - tw2) / 2, pill_y2 + 7), p_txt2, font=f_pill2, fill=(255, 255, 255))

    # Right Panel
    rx = 435
    logo_path = BOT_DIR / "logo.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA").resize((52, 52), Image.Resampling.LANCZOS)
        canvas.paste(logo, (rx, 60), logo)
        hdr_x = rx + 62
    else:
        hdr_x = rx

    draw.text((hdr_x, 60), "SAGAR COACHING CENTRE • SAGAR SIR", font=f_tag, fill=(250, 204, 21))
    draw.text((hdr_x, 86), "INDIA'S NO. 1 NMMS CHANNEL  |  www.sagarcoaching.tech", font=f_badge, fill=(186, 230, 253))

    draw.text((rx, 134), "NMMS 2027-28 BATCH & BOOKS", font=f_title, fill=(255, 255, 255))
    draw.text((rx, 178), "4 EXPERT TEACHERS • DAILY LIVE CLASSES", font=f_sub, fill=(250, 204, 21))
    draw.line([(rx, 214), (W - 55, 214)], fill=(234, 179, 8, 120), width=2)

    bullets = [
        ("4 Teachers Special Live Class", "MAT, Science, SST & Maths Live Classes"),
        ("Daily 2 Live Quizzes in Paid Batch", "5:30 PM (30Q Mix) & 8:30 PM (50Q Speed)"),
        ("Official Book ₹350 • Practice Set ₹150", "2,741+ Official PYQs with Solutions"),
        ("Top 20 Merit List & Daily Certificates", "Daily Gold, Silver & Bronze Medals"),
    ]

    py = 230
    for left_lbl, right_lbl in bullets:
        draw.rounded_rectangle([(rx, py), (W - 55, py + 48)], radius=12, fill=(30, 41, 59, 210), outline=(59, 130, 246, 130), width=1)
        draw.ellipse([(rx + 14, py + 15), (rx + 32, py + 33)], fill=(16, 185, 129))
        draw.text((rx + 44, py + 11), left_lbl, font=f_bullet, fill=(255, 255, 255))
        rw = draw.textlength(right_lbl, font=f_small)
        draw.text((W - 75 - rw, py + 14), right_lbl, font=f_small, fill=(147, 197, 253))
        py += 58

    # Bottom CTA Bar
    cta_y1, cta_y2 = 475, 532
    draw.rounded_rectangle([(rx, cta_y1), (W - 55, cta_y2)], radius=16, fill=(245, 158, 11))
    cta_txt = "ORDER BOOK / JOIN COURSE  |  WhatsApp: +91 91101 13671"
    ctw = draw.textlength(cta_txt, font=f_cta)
    draw.text(((rx + W - 55 - ctw) / 2, cta_y1 + 16), cta_txt, font=f_cta, fill=(15, 23, 42))

    # Sub-bar for App
    app_y1, app_y2 = 544, 586
    draw.rounded_rectangle([(rx, app_y1), (W - 55, app_y2)], radius=14, fill=(15, 23, 42, 230), outline=(234, 179, 8, 140), width=1)
    app_txt = "Sagar Sir App on Google Play Store  •  YouTube: Sagar Coaching Centre"
    atw = draw.textlength(app_txt, font=f_app)
    draw.text(((rx + W - 55 - atw) / 2, app_y1 + 11), app_txt, font=f_app, fill=(203, 213, 225))

    out_rgb = canvas.convert("RGB")
    out_rgb.save(OUT_PATH, quality=95)
    print("Promo poster generated successfully:", OUT_PATH)

if __name__ == "__main__":
    build_promo_poster()
