import io
import os
import re
import math
import unicodedata
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")
LOCAL_HINDI_FONT = os.path.join(BASE_DIR, "nirmala.ttc")
LOCAL_LATIN_FONT = os.path.join(BASE_DIR, "segoeuib.ttf")

AVATAR_COLORS = [
    (59, 130, 246),   # Blue
    (16, 185, 129),   # Emerald
    (245, 158, 11),   # Amber
    (139, 92, 246),   # Purple
    (236, 72, 153),   # Pink
    (20, 184, 166),   # Teal
    (239, 68, 68),    # Red
    (99, 102, 241),   # Indigo
]

def clean_fancy_unicode(name: str) -> str:
    """Converts fancy Mathematical alphanumeric characters, regional indicator symbols, and circled letters to clean text."""
    norm = unicodedata.normalize('NFKD', str(name))
    res = []
    for ch in norm:
        code = ord(ch)
        if 0x1F1E6 <= code <= 0x1F1FF:  # Regional Indicator Symbols (Flags)
            res.append(chr(ord('A') + (code - 0x1F1E6)))
        elif 0x24B6 <= code <= 0x24CF:  # Circled A-Z
            res.append(chr(ord('A') + (code - 0x24B6)))
        elif 0x24D0 <= code <= 0x24E9:  # Circled a-z
            res.append(chr(ord('a') + (code - 0x24D0)))
        elif code in [0x200B, 0x200C, 0x200D, 0xFEFF]:  # Zero width spaces
            continue
        else:
            res.append(ch)
    cleaned = ''.join(res)
    filtered = re.sub(r'[^\w\s\u0900-\u097F\.\-\'\&]', '', cleaned)
    return ' '.join(filtered.split())

def resolve_student_name(student: dict) -> str:
    """Robustly resolves student name, handling stylized fonts, only-emojis, and fallbacks."""
    raw_name = str(student.get("name", "")).strip()
    cleaned = clean_fancy_unicode(raw_name)
    if len(cleaned) >= 2:
        return cleaned
    username = str(student.get("username", "")).lstrip("@").strip()
    if username and len(username) >= 2:
        return username.replace("_", " ").title()
    return "Student"

def draw_star(draw, cx, cy, r_out, r_in, fill):
    """Draws a crisp anti-aliased 5-point star vector without font dependency."""
    points = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        angle = i * math.pi / 5 - math.pi / 2
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=fill)

def create_radial_gradient_background(width, height, top_color, center_color, bottom_color):
    """Creates a high-end luxury radial spotlight gradient background."""
    base = Image.new("RGB", (width, height), bottom_color)
    draw = ImageDraw.Draw(base)
    for y in range(height):
        factor = y / height
        r = int(top_color[0] * (1 - factor) + bottom_color[0] * factor)
        g = int(top_color[1] * (1 - factor) + bottom_color[1] * factor)
        b = int(top_color[2] * (1 - factor) + bottom_color[2] * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    spotlight = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(spotlight)
    cx, cy = width // 2, int(height * 0.36)
    max_radius = int(width * 0.55)
    for r in range(max_radius, 0, -6):
        alpha = int(45 * (1 - (r / max_radius) ** 1.5))
        s_draw.ellipse(
            [(cx - r, cy - int(r * 0.85)), (cx + r, cy + int(r * 0.85))],
            fill=(center_color[0], center_color[1], center_color[2], alpha)
        )
    return Image.alpha_composite(base.convert("RGBA"), spotlight).convert("RGB")

def make_circular_avatar(img_or_initial, size=130, ring_color=(234, 179, 8), ring_width=4):
    """Creates a circular profile picture with metallic ring and fallback monogram."""
    scale = 2
    full_s = size * scale
    avatar_canvas = Image.new("RGBA", (full_s, full_s), (0, 0, 0, 0))
    mask = Image.new("L", (full_s, full_s), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.ellipse([(0, 0), (full_s, full_s)], fill=255)

    loaded = False
    if isinstance(img_or_initial, Image.Image):
        try:
            img_resized = img_or_initial.convert("RGBA").resize((full_s, full_s), Image.Resampling.LANCZOS)
            avatar_canvas.paste(img_resized, (0, 0), mask=mask)
            loaded = True
        except Exception:
            loaded = False
    elif isinstance(img_or_initial, (bytes, bytearray)) and len(img_or_initial) > 0:
        try:
            im = Image.open(io.BytesIO(img_or_initial)).convert("RGBA")
            min_dim = min(im.size)
            left = (im.width - min_dim) // 2
            top = (im.height - min_dim) // 2
            im = im.crop((left, top, left + min_dim, top + min_dim))
            img_resized = im.resize((full_s, full_s), Image.Resampling.LANCZOS)
            avatar_canvas.paste(img_resized, (0, 0), mask=mask)
            loaded = True
        except Exception:
            loaded = False

    if not loaded:
        initial = str(img_or_initial)[0].upper() if img_or_initial else "S"
        bg_draw = ImageDraw.Draw(avatar_canvas)
        bg_draw.ellipse([(0, 0), (full_s, full_s)], fill=(30, 58, 138, 255))
        font = get_latin_font(int(size * 0.52 * scale), is_bold=True)
        bg_draw.text((full_s // 2, full_s // 2), initial, font=font, fill=(255, 255, 255, 255), anchor="mm")

    ring_draw = ImageDraw.Draw(avatar_canvas)
    for w_i in range(ring_width * scale):
        ring_draw.ellipse([(w_i, w_i), (full_s - w_i - 1, full_s - w_i - 1)], outline=ring_color + (255,))

    return avatar_canvas.resize((size, size), Image.Resampling.LANCZOS)

def get_latin_font(size: int, is_bold: bool = True):
    """Loads crisp typography for English headers, numbers, and capsules."""
    candidates = [
        LOCAL_LATIN_FONT,
        "C:/Windows/Fonts/segoeuib.ttf" if is_bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if is_bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if is_bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def get_hindi_font(size: int, is_bold: bool = False):
    """Loads clean typography for Hindi text and student names."""
    candidates = [
        LOCAL_HINDI_FONT,
        "C:/Windows/Fonts/Nirmala.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, index=0)
            except Exception:
                continue
    return ImageFont.load_default()

def make_photo_avatar(photo_bytes, size=36):
    """Crops real Telegram DP into a circular avatar with border."""
    try:
        im = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        min_dim = min(im.size)
        left = (im.width - min_dim) // 2
        top = (im.height - min_dim) // 2
        im = im.crop((left, top, left + min_dim, top + min_dim))
        im = im.resize((size, size), Image.Resampling.LANCZOS)
        
        mask = Image.new("L", (size, size), 0)
        d = ImageDraw.Draw(mask)
        d.ellipse((0, 0, size, size), fill=255)
        
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(im, (0, 0), mask=mask)
        
        d_out = ImageDraw.Draw(out)
        d_out.ellipse((0, 0, size - 1, size - 1), outline=(255, 255, 255, 180), width=1)
        return out
    except Exception:
        return None

def make_fallback_avatar(name: str, size=36, font=None):
    """Draws a colorful initial badge when user has no Telegram profile photo."""
    initial = (name.strip()[:1] if name.strip() else "S").upper()
    color_idx = abs(hash(name)) % len(AVATAR_COLORS)
    bg_color = AVATAR_COLORS[color_idx]

    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, size, size), fill=bg_color)
    d.ellipse((0, 0, size - 1, size - 1), outline=(255, 255, 255, 180), width=1)
    
    if font:
        d.text((size // 2, size // 2), initial, font=font, fill=(255, 255, 255), anchor="mm")
    return im

def clean_test_title(raw_name: str) -> str:
    """
    Standardizes test name into a clean, simple title WITHOUT revealing set numbers.
    E.g. 'MAT मॉक सेट 01' -> 'MAT Full Mock Test (90 Questions)'
    """
    s = raw_name.strip()
    if "MAT" in s or "मानसिक" in s or "तर्कशक्ति" in s:
        if "90" in s or "मॉक" in s or "Mock" in s:
            return "MAT Full Mock Test (90 Questions)"
        return "Mental Ability Practice Test (50 Questions)"
    if "SAT" in s:
        return "SAT Full Mock Test (90 Questions)"
    if "विज्ञान" in s and "सामाजिक" not in s:
        return "Science Practice Test (50 Questions)"
    if "सामाजिक" in s or "सा. विज्ञान" in s:
        return "Social Science Practice Test (50 Questions)"
    if "गणित" in s:
        return "Mathematics Practice Test (50 Questions)"
    return "NMMS Scholarship Practice Test"

def draw_verified_medal(draw, x, y, rank, font_bold, font_cell):
    """
    Draws authentic metallic verified medals for Rank 1 (Gold), Rank 2 (Silver), Rank 3 (Bronze).
    Features concentric metallic rings and crisp rank numerals. Zero [] errors.
    """
    if rank == 1:
        # Metallic Verified Gold Medal
        draw.ellipse([(x - 20, y - 20), (x + 20, y + 20)], fill=(234, 179, 8), outline=(254, 240, 138), width=2)
        draw.ellipse([(x - 16, y - 16), (x + 16, y + 16)], outline=(180, 83, 9), width=1)
        draw.text((x, y), "1", font=font_bold, fill=(15, 23, 42), anchor="mm")
    elif rank == 2:
        # Metallic Verified Silver Medal
        draw.ellipse([(x - 20, y - 20), (x + 20, y + 20)], fill=(203, 213, 225), outline=(248, 250, 252), width=2)
        draw.ellipse([(x - 16, y - 16), (x + 16, y + 16)], outline=(100, 116, 139), width=1)
        draw.text((x, y), "2", font=font_bold, fill=(15, 23, 42), anchor="mm")
    elif rank == 3:
        # Metallic Verified Bronze Medal
        draw.ellipse([(x - 20, y - 20), (x + 20, y + 20)], fill=(217, 119, 6), outline=(251, 191, 36), width=2)
        draw.ellipse([(x - 16, y - 16), (x + 16, y + 16)], outline=(146, 64, 14), width=1)
        draw.text((x, y), "3", font=font_bold, fill=(255, 255, 255), anchor="mm")
    else:
        # Clean Slate Pill Badge
        draw.rounded_rectangle([(x - 18, y - 15), (x + 18, y + 15)], radius=7, fill=(30, 45, 88), outline=(51, 65, 85), width=1)
        draw.text((x, y), str(rank), font=font_cell, fill=(148, 163, 184), anchor="mm")

def generate_result_card(
    test_name: str,
    total_q: int,
    top_students: list,
    attempted_q: int = None,
    total_participants: int = None
) -> io.BytesIO:
    """
    Generates a high-resolution, branded result card (Design A - Royal Navy & Gold).
    Spacious vertical gaps for names, verified medals, clean modern wording, and zero set numbers.
    """
    width = 1200
    row_height = 56
    display_students = top_students[:20] if top_students else []
    num_rows = max(len(display_students), 3)

    if not total_participants:
        total_participants = len(top_students) if top_students else len(display_students)

    header_height = 175
    meta_height = 60
    table_header_h = 42
    footer_height = 100
    th_y = header_height + meta_height + 15
    height = th_y + table_header_h + (num_rows * row_height) + footer_height

    # Deep Midnight Navy Slate Canvas (#0B132B)
    img = Image.new("RGB", (width, height), color=(11, 19, 43))
    draw = ImageDraw.Draw(img)

    # Fonts
    title_font = get_latin_font(34, is_bold=True)
    subtitle_font = get_latin_font(19, is_bold=True)
    sub_tag_font = get_latin_font(17, is_bold=False)
    info_font = get_latin_font(17, is_bold=True)
    th_font = get_latin_font(16, is_bold=True)
    name_font = get_hindi_font(20, is_bold=False)
    badge_bold = get_latin_font(18, is_bold=True)
    badge_cell = get_latin_font(16, is_bold=True)
    cell_font = get_latin_font(17, is_bold=True)
    footer_gold = get_latin_font(18, is_bold=True)
    footer_sub = get_hindi_font(17, is_bold=False)

    # Header Background
    draw.rectangle([(0, 0), (width, header_height)], fill=(19, 29, 61))
    draw.rectangle([(0, header_height - 5), (width, header_height)], fill=(234, 179, 8))

    # Logo
    logo_placed = False
    if os.path.exists(LOGO_PATH):
        try:
            logo_img = Image.open(LOGO_PATH).convert("RGBA")
            logo_size = 130
            logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            img.paste(logo_img, (50, 22), mask=logo_img.split()[3])
            logo_placed = True
        except Exception as e:
            print("Logo error:", e)

    # Header Typography
    text_x = 205 if logo_placed else (width // 2)
    align_mode = "lm" if logo_placed else "mm"

    draw.text((text_x, 42), "SAGAR COACHING CENTRE", font=title_font, fill=(255, 255, 255), anchor=align_mode)
    draw.text((text_x, 88), "NMMS SCHOLARSHIP EXAM  |  OFFICIAL MERIT LIST", font=subtitle_font, fill=(234, 179, 8), anchor=align_mode)
    draw.text((text_x, 126), "Bhagwanpur (Supaul, Bihar)   •   Mentor: Sagar Sir (7+ Years Exp.)", font=sub_tag_font, fill=(148, 163, 184), anchor=align_mode)

    # Meta Bar Strip (Full Width Balance)
    meta_box_y = header_height + 15
    draw.rounded_rectangle([(45, meta_box_y), (width - 45, meta_box_y + 48)], radius=10, fill=(22, 34, 70), outline=(37, 52, 98), width=1)
    
    clean_title = clean_test_title(test_name)
    date_str = datetime.now().strftime("%d-%m-%Y")
    
    draw.text((70, meta_box_y + 24), f"TEST: {clean_title.upper()}", font=info_font, fill=(255, 255, 255), anchor="lm")
    draw.text((width - 70, meta_box_y + 24), f"TOTAL STUDENTS: {total_participants}   |   DATE: {date_str}", font=info_font, fill=(234, 179, 8), anchor="rm")

    # Table Header Box
    table_x = 45
    table_w = width - (table_x * 2)
    th_box_y = meta_box_y + 58
    draw.rounded_rectangle([(table_x, th_box_y), (table_x + table_w, th_box_y + 40)], radius=8, fill=(30, 45, 88))

    draw.text((table_x + 45, th_box_y + 20), "RANK", font=th_font, fill=(203, 213, 225), anchor="mm")
    draw.text((table_x + 120, th_box_y + 20), "STUDENT NAME", font=th_font, fill=(203, 213, 225), anchor="lm")
    draw.text((table_x + 595, th_box_y + 20), "SCORE", font=th_font, fill=(203, 213, 225), anchor="mm")
    draw.text((table_x + 785, th_box_y + 20), "ACCURACY", font=th_font, fill=(203, 213, 225), anchor="mm")
    draw.text((table_x + 975, th_box_y + 20), "AVG SPEED", font=th_font, fill=(203, 213, 225), anchor="mm")

    # Table Rows (Roomy 56px row height for generous vertical breathing space)
    row_y = th_box_y + 48
    effective_total = attempted_q if (attempted_q and attempted_q > 0) else total_q
    avatar_size = 36

    for i, student in enumerate(display_students):
        bg_color = (19, 29, 61) if i % 2 == 0 else (15, 24, 52)
        border_fill = None
        if i == 0: border_fill = (234, 179, 8)       # Gold
        elif i == 1: border_fill = (203, 213, 225)   # Silver
        elif i == 2: border_fill = (217, 119, 6)     # Bronze

        row_h = 48
        draw.rounded_rectangle([(table_x, row_y), (table_x + table_w, row_y + row_h)], radius=8, fill=bg_color)
        if border_fill:
            draw.rectangle([(table_x, row_y), (table_x + 5, row_y + row_h)], fill=border_fill)

        # Verified Metallic Medal Badge
        draw_verified_medal(draw, table_x + 45, row_y + (row_h // 2), i + 1, badge_bold, badge_cell)

        # Avatar
        s_name = resolve_student_name(student)
        av_bytes = student.get("avatar_bytes")
        av_img = None
        if av_bytes:
            av_img = make_photo_avatar(av_bytes, size=avatar_size)
        if not av_img:
            av_img = make_fallback_avatar(s_name, size=avatar_size, font=get_latin_font(17, is_bold=True))

        av_x = table_x + 92
        av_y = row_y + ((row_h - avatar_size) // 2)
        img.paste(av_img, (av_x, av_y), mask=av_img.split()[3])

        # Name Text with generous 16px horizontal spacing
        display_name = s_name
        if len(display_name) > 24:
            display_name = display_name[:22] + ".."
        name_x = av_x + avatar_size + 16
        draw.text((name_x, row_y + (row_h // 2)), display_name, font=name_font, fill=(255, 255, 255), anchor="lm")

        # Score Capsule
        score_val = student.get("score", 0)
        draw.rounded_rectangle([(table_x + 535, row_y + 8), (table_x + 655, row_y + 40)], radius=7, fill=(22, 34, 70), outline=(56, 189, 248), width=1)
        draw.text((table_x + 595, row_y + (row_h // 2)), f"{score_val} / {effective_total}", font=cell_font, fill=(56, 189, 248), anchor="mm")

        # Accuracy Capsule
        pct = student.get("accuracy")
        if pct is None:
            pct = (score_val / effective_total * 100) if effective_total > 0 else 0
        draw.rounded_rectangle([(table_x + 725, row_y + 8), (table_x + 845, row_y + 40)], radius=7, fill=(22, 34, 70), outline=(74, 222, 128), width=1)
        draw.text((table_x + 785, row_y + (row_h // 2)), f"{pct:.1f}%", font=cell_font, fill=(74, 222, 128), anchor="mm")

        # Speed Capsule
        avg_time = student.get("avg_time", 0.0)
        draw.rounded_rectangle([(table_x + 915, row_y + 8), (table_x + 1035, row_y + 40)], radius=7, fill=(22, 34, 70), outline=(244, 114, 182), width=1)
        draw.text((table_x + 975, row_y + (row_h // 2)), f"{avg_time:.1f}s / Q", font=cell_font, fill=(244, 114, 182), anchor="mm")

        row_y += row_height

    # Footer (Simple, Modern, Clean Language)
    footer_y = height - 90
    draw.line([(45, footer_y), (width - 45, footer_y)], fill=(37, 52, 98), width=1)
    draw.text(
        (width // 2, footer_y + 26),
        "NMMS Special Book by Sagar Sir (7+ Years Exp.)",
        font=footer_gold,
        fill=(234, 179, 8),
        anchor="mm"
    )
    draw.text(
        (width // 2, footer_y + 58),
        "Sagar Coaching Centre, Bhagwanpur (Supaul)   •   Call / WhatsApp: +91 91101 13671",
        font=footer_sub,
        fill=(203, 213, 225),
        anchor="mm"
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf

def generate_topper_card(
    student: dict,
    rank: int,
    test_name: str,
    total_q: int,
    attempted_q: int = None,
    total_participants: int = None,
    avatar_bytes: bytes = None
) -> io.BytesIO:
    """
    Generates a royal masterclass Topper Certificate Card (900 x 910 px) with 3D floral corners,
    circular metallic DP avatar, 3D ribbon medal, clean typography (zero [] boxes), and polite messaging.
    """
    width, height = 900, 910

    # Color Themes based on Rank
    if rank == 1:
        accent_color = (234, 179, 8)     # Pure Gold
        accent_light = (253, 224, 71)    # Bright Gold
        glow_center = (45, 40, 15)       # Golden spotlight
        award_name = "CERTIFICATE OF EXCELLENCE"
        rank_label = "1st RANK TOPPER"
        medal_file = os.path.join(BASE_DIR, "assets", "medal_gold.png")
        corner_file = os.path.join(BASE_DIR, "assets", "corner_gold.png")
    elif rank == 2:
        accent_color = (203, 213, 225)   # Platinum Silver
        accent_light = (241, 245, 249)
        glow_center = (30, 45, 70)       # Silver-blue spotlight
        award_name = "CERTIFICATE OF MERIT"
        rank_label = "2nd RANK TOPPER"
        medal_file = os.path.join(BASE_DIR, "assets", "medal_silver.png")
        corner_file = os.path.join(BASE_DIR, "assets", "corner_silver.png")
    else:
        accent_color = (217, 119, 6)     # Bronze Gold
        accent_light = (251, 191, 36)
        glow_center = (45, 28, 15)       # Bronze spotlight
        award_name = "CERTIFICATE OF ACHIEVEMENT"
        rank_label = "3rd RANK TOPPER"
        medal_file = os.path.join(BASE_DIR, "assets", "medal_bronze.png")
        corner_file = os.path.join(BASE_DIR, "assets", "corner_bronze.png")

    # Background: Royal Navy with Spotlight Gradient
    top_navy = (10, 18, 42)
    bottom_navy = (7, 12, 28)
    img = create_radial_gradient_background(width, height, top_navy, glow_center, bottom_navy)
    draw = ImageDraw.Draw(img)

    # Dual Certificate Borders
    draw.rounded_rectangle([(24, 24), (width - 24, height - 24)], radius=16, outline=accent_color, width=2)
    draw.rounded_rectangle([(32, 32), (width - 32, height - 32)], radius=12, outline=(accent_color[0]//2, accent_color[1]//2, accent_color[2]//2), width=1)

    # 4 Corner Royal Floral Ornaments
    if os.path.exists(corner_file):
        try:
            c_base = Image.open(corner_file).convert("RGBA")
            c_size = 135
            c_base = c_base.resize((c_size, c_size), Image.Resampling.LANCZOS)

            # Top-Left
            img.paste(c_base, (22, 22), mask=c_base.split()[3])
            # Top-Right
            c_tr = c_base.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            img.paste(c_tr, (width - 22 - c_size, 22), mask=c_tr.split()[3])
            # Bottom-Left
            c_bl = c_base.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            img.paste(c_bl, (22, height - 22 - c_size), mask=c_bl.split()[3])
            # Bottom-Right
            c_br = c_base.transpose(Image.Transpose.ROTATE_180)
            img.paste(c_br, (width - 22 - c_size, height - 22 - c_size), mask=c_br.split()[3])
        except Exception:
            pass

    # Top Header Logo
    logo_size = 72
    if os.path.exists(LOGO_PATH):
        try:
            l_img = Image.open(LOGO_PATH).convert("RGBA").resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            lx = (width - logo_size) // 2
            ly = 46
            draw.ellipse([(lx - 4, ly - 4), (lx + logo_size + 4, ly + logo_size + 4)], outline=accent_color, width=2)
            img.paste(l_img, (lx, ly), mask=l_img.split()[3])
        except Exception:
            pass

    # Institute Title & Subtitles
    ty = 138
    curr_year = datetime.now().year
    curr_session = f"{curr_year}-{str(curr_year + 1)[-2:]}"
    draw.text((width // 2, ty), "SAGAR COACHING CENTRE, BHAGWANPUR", font=get_latin_font(23, is_bold=True), fill=accent_light, anchor="mm")
    draw.text((width // 2, ty + 26), f"NMMS SCHOLARSHIP EXAMINATION - {curr_session}", font=get_latin_font(14, is_bold=True), fill=(148, 163, 184), anchor="mm")
    draw.text((width // 2, ty + 52), award_name, font=get_latin_font(18, is_bold=True), fill=accent_color, anchor="mm")

    # Divider line
    div_w = 260
    draw.line([(width // 2 - div_w // 2, ty + 70), (width // 2 + div_w // 2, ty + 70)], fill=accent_color, width=1)

    # Centerpiece: Student Avatar + 3D Medal Showcase
    avatar_y = ty + 155
    avatar_size = 130
    clean_name = resolve_student_name(student)
    av_data = avatar_bytes or student.get("avatar_bytes")
    avatar_item = av_data if av_data else clean_name
    av_circle = make_circular_avatar(avatar_item, size=avatar_size, ring_color=accent_color, ring_width=4)

    av_x = (width - avatar_size) // 2
    img.paste(av_circle, (av_x, avatar_y - avatar_size // 2), mask=av_circle.split()[3])

    # Place 3D Medal Emblem right beside/overlapping bottom-right
    if os.path.exists(medal_file):
        try:
            m_img = Image.open(medal_file).convert("RGBA")
            medal_h = 100
            m_ratio = medal_h / m_img.height
            medal_w = int(m_img.width * m_ratio)
            m_resized = m_img.resize((medal_w, medal_h), Image.Resampling.LANCZOS)

            m_x = av_x + avatar_size - int(medal_w * 0.45)
            m_y = avatar_y + (avatar_size // 2) - int(medal_h * 0.70)
            img.paste(m_resized, (m_x, m_y), mask=m_resized.split()[3])
        except Exception:
            pass

    # Rank Title Capsule Pill with Vector Stars
    pill_y = avatar_y + (avatar_size // 2) + 48
    pill_w = 320
    pill_h = 36
    draw.rounded_rectangle(
        [(width // 2 - pill_w // 2, pill_y - pill_h // 2), (width // 2 + pill_w // 2, pill_y + pill_h // 2)],
        radius=18,
        fill=(19, 29, 61),
        outline=accent_color,
        width=2
    )
    p_font = get_latin_font(16, is_bold=True)
    draw.text((width // 2, pill_y), rank_label, font=p_font, fill=accent_light, anchor="mm")
    p_bbox = draw.textbbox((width // 2, pill_y), rank_label, font=p_font, anchor="mm")
    draw_star(draw, p_bbox[0] - 16, pill_y, 7, 3.5, fill=accent_color)
    draw_star(draw, p_bbox[2] + 16, pill_y, 7, 3.5, fill=accent_color)

    # Student Name (Clean, Box-Free, Pure Typography)
    name_y = pill_y + 46
    draw.text((width // 2, name_y), clean_name, font=get_hindi_font(34, is_bold=True), fill=(255, 255, 255), anchor="mm")

    # Test details & metadata
    test_y = name_y + 34
    clean_title = clean_test_title(test_name)
    date_str = datetime.now().strftime("%d %b %Y")
    if total_participants:
        info_text = f"{clean_title}   •   {date_str}   •   Total Students: {total_participants}"
    else:
        info_text = f"{clean_title}   •   {date_str}"
    draw.text((width // 2, test_y), info_text, font=get_latin_font(14, is_bold=True), fill=(148, 163, 184), anchor="mm")

    # 3 Performance Stat Boxes
    effective_total = attempted_q if (attempted_q and attempted_q > 0) else total_q
    score_val = student.get("score", 0)
    acc_val = student.get("accuracy", 0.0)
    speed_val = student.get("avg_time", 0.0)

    stats_data = [
        ("SCORE", f"{score_val} / {effective_total}", (56, 189, 248)),
        ("ACCURACY", f"{acc_val:.1f}%", (74, 222, 128)),
        ("AVG SPEED", f"{speed_val:.1f}s", (244, 114, 182))
    ]

    stat_y = test_y + 32
    box_w, box_h = 236, 85
    spacing = 16
    total_stat_w = (box_w * 3) + (spacing * 2)
    start_x = (width - total_stat_w) // 2

    for i, (label, val, val_col) in enumerate(stats_data):
        bx = start_x + (i * (box_w + spacing))
        draw.rounded_rectangle([(bx, stat_y), (bx + box_w, stat_y + box_h)], radius=10, fill=(22, 34, 68), outline=(51, 65, 85), width=1)
        draw.text((bx + box_w // 2, stat_y + 24), label, font=get_latin_font(14, is_bold=True), fill=(148, 163, 184), anchor="mm")
        draw.text((bx + box_w // 2, stat_y + 57), val, font=get_latin_font(26, is_bold=True), fill=val_col, anchor="mm")

    # Congratulations / Wishes box
    wishes_y = stat_y + box_h + 24
    w_box_w = 720
    w_box_h = 56
    draw.rounded_rectangle([((width - w_box_w) // 2, wishes_y), ((width + w_box_w) // 2, wishes_y + w_box_h)], radius=10, fill=(18, 28, 56), outline=accent_color, width=1)
    draw.text((width // 2, wishes_y + 18), "Best Wishes for Your Bright Future & NMMS Scholarship!", font=get_latin_font(15, is_bold=True), fill=accent_light, anchor="mm")
    draw.text((width // 2, wishes_y + 38), "— Sagar Sir  •  Sagar Coaching Centre, Bhagwanpur", font=get_hindi_font(13, is_bold=False), fill=(203, 213, 225), anchor="mm")

    # Official Footer
    footer_y = wishes_y + w_box_h + 20
    draw.text((width // 2, footer_y + 18), "NMMS Special Book by Sagar Sir (7+ Years Exp.)", font=get_latin_font(13, is_bold=True), fill=(148, 163, 184), anchor="mm")
    draw.text((width // 2, footer_y + 38), "Sagar Coaching Centre, Bhagwanpur (Supaul)   •   Call / WhatsApp: +91 91101 13671", font=get_latin_font(13, is_bold=True), fill=accent_light, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
