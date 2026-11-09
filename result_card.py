import io
import os
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
    """Loads clean Devanagari typography for Hindi text and student names."""
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

def make_photo_avatar(photo_bytes, size=34):
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

def make_fallback_avatar(name: str, size=34, font=None):
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
    Standardizes test name into a clean title WITHOUT revealing set numbers to students.
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

def draw_vector_rank_badge(draw, x, y, rank, font_bold, font_cell):
    """
    Draws custom vector metallic shields for Top 3 and pills for others.
    Completely eliminates missing glyph / [] square box errors.
    """
    if rank == 1:
        # Metallic Gold Shield
        draw.ellipse([(x - 17, y - 17), (x + 17, y + 17)], fill=(234, 179, 8), outline=(254, 240, 138), width=2)
        draw.text((x, y), "1", font=font_bold, fill=(15, 23, 42), anchor="mm")
    elif rank == 2:
        # Metallic Silver Shield
        draw.ellipse([(x - 17, y - 17), (x + 17, y + 17)], fill=(203, 213, 225), outline=(248, 250, 252), width=2)
        draw.text((x, y), "2", font=font_bold, fill=(15, 23, 42), anchor="mm")
    elif rank == 3:
        # Metallic Bronze Shield
        draw.ellipse([(x - 17, y - 17), (x + 17, y + 17)], fill=(217, 119, 6), outline=(251, 191, 36), width=2)
        draw.text((x, y), "3", font=font_bold, fill=(255, 255, 255), anchor="mm")
    else:
        # Slate Pill Badge
        draw.rounded_rectangle([(x - 17, y - 14), (x + 17, y + 14)], radius=6, fill=(30, 45, 88), outline=(51, 65, 85), width=1)
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
    Features vector medals, modern metric capsules, zero empty space, and no set numbers.
    """
    width = 1200
    row_height = 52
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

    # Deep Midnight Slate Canvas (#0B132B)
    img = Image.new("RGB", (width, height), color=(11, 19, 43))
    draw = ImageDraw.Draw(img)

    # Fonts
    title_font = get_latin_font(34, is_bold=True)
    subtitle_font = get_latin_font(19, is_bold=True)
    author_font = get_hindi_font(18, is_bold=False)
    info_font = get_latin_font(17, is_bold=True)
    th_font = get_latin_font(16, is_bold=True)
    name_font = get_hindi_font(19, is_bold=False)
    badge_bold = get_latin_font(18, is_bold=True)
    badge_cell = get_latin_font(16, is_bold=True)
    cell_font = get_latin_font(17, is_bold=True)
    footer_gold = get_hindi_font(18, is_bold=True)
    footer_sub = get_hindi_font(16, is_bold=False)

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
    draw.text((text_x, 126), "Bhagwanpur (Supaul, Bihar)   •   Mentor: Sagar Sir (7+ Years Experience)", font=author_font, fill=(148, 163, 184), anchor=align_mode)

    # Meta Bar Strip (Fills horizontal space perfectly with no empty dead zones)
    meta_box_y = header_height + 15
    draw.rounded_rectangle([(45, meta_box_y), (width - 45, meta_box_y + 48)], radius=10, fill=(22, 34, 70), outline=(37, 52, 98), width=1)
    
    clean_title = clean_test_title(test_name)
    date_str = datetime.now().strftime("%d-%m-%Y")
    
    draw.text((70, meta_box_y + 24), f"TEST: {clean_title.upper()}", font=info_font, fill=(255, 255, 255), anchor="lm")
    draw.text((width - 70, meta_box_y + 24), f"TOTAL CANDIDATES: {total_participants} STUDENTS   |   DATE: {date_str}", font=info_font, fill=(234, 179, 8), anchor="rm")

    # Table Header Box
    table_x = 45
    table_w = width - (table_x * 2)
    th_box_y = meta_box_y + 58
    draw.rounded_rectangle([(table_x, th_box_y), (table_x + table_w, th_box_y + 40)], radius=8, fill=(30, 45, 88))

    # Columns coordinates:
    draw.text((table_x + 45, th_box_y + 20), "RANK", font=th_font, fill=(203, 213, 225), anchor="mm")
    draw.text((table_x + 115, th_box_y + 20), "STUDENT NAME", font=th_font, fill=(203, 213, 225), anchor="lm")
    draw.text((table_x + 595, th_box_y + 20), "SCORE", font=th_font, fill=(203, 213, 225), anchor="mm")
    draw.text((table_x + 785, th_box_y + 20), "ACCURACY", font=th_font, fill=(203, 213, 225), anchor="mm")
    draw.text((table_x + 975, th_box_y + 20), "AVG SPEED", font=th_font, fill=(203, 213, 225), anchor="mm")

    # Table Rows
    row_y = th_box_y + 48
    effective_total = attempted_q if (attempted_q and attempted_q > 0) else total_q
    avatar_size = 34

    for i, student in enumerate(display_students):
        bg_color = (19, 29, 61) if i % 2 == 0 else (15, 24, 52)
        border_fill = None
        if i == 0: border_fill = (234, 179, 8)       # Gold
        elif i == 1: border_fill = (203, 213, 225)   # Silver
        elif i == 2: border_fill = (217, 119, 6)     # Bronze

        row_h = 46
        draw.rounded_rectangle([(table_x, row_y), (table_x + table_w, row_y + row_h)], radius=8, fill=bg_color)
        if border_fill:
            draw.rectangle([(table_x, row_y), (table_x + 5, row_y + row_h)], fill=border_fill)

        # Vector Rank Badge (Zero missing glyphs)
        draw_vector_rank_badge(draw, table_x + 45, row_y + (row_h // 2), i + 1, badge_bold, badge_cell)

        # Avatar
        s_name = str(student.get("name", "Student")).strip()
        av_bytes = student.get("avatar_bytes")
        av_img = None
        if av_bytes:
            av_img = make_photo_avatar(av_bytes, size=avatar_size)
        if not av_img:
            av_img = make_fallback_avatar(s_name, size=avatar_size, font=get_latin_font(16, is_bold=True))

        av_x = table_x + 90
        av_y = row_y + ((row_h - avatar_size) // 2)
        img.paste(av_img, (av_x, av_y), mask=av_img.split()[3])

        # Name Text
        display_name = s_name
        if len(display_name) > 24:
            display_name = display_name[:22] + ".."
        name_x = av_x + avatar_size + 12
        draw.text((name_x, row_y + (row_h // 2)), display_name, font=name_font, fill=(255, 255, 255), anchor="lm")

        # Score Capsule
        score_val = student.get("score", 0)
        draw.rounded_rectangle([(table_x + 535, row_y + 8), (table_x + 655, row_y + 38)], radius=6, fill=(22, 34, 70), outline=(56, 189, 248), width=1)
        draw.text((table_x + 595, row_y + (row_h // 2)), f"{score_val} / {effective_total}", font=cell_font, fill=(56, 189, 248), anchor="mm")

        # Accuracy Capsule
        pct = student.get("accuracy")
        if pct is None:
            pct = (score_val / effective_total * 100) if effective_total > 0 else 0
        draw.rounded_rectangle([(table_x + 725, row_y + 8), (table_x + 845, row_y + 38)], radius=6, fill=(22, 34, 70), outline=(74, 222, 128), width=1)
        draw.text((table_x + 785, row_y + (row_h // 2)), f"{pct:.1f}%", font=cell_font, fill=(74, 222, 128), anchor="mm")

        # Speed Capsule
        avg_time = student.get("avg_time", 0.0)
        draw.rounded_rectangle([(table_x + 915, row_y + 8), (table_x + 1035, row_y + 38)], radius=6, fill=(22, 34, 70), outline=(244, 114, 182), width=1)
        draw.text((table_x + 975, row_y + (row_h // 2)), f"{avg_time:.1f}s / Q", font=cell_font, fill=(244, 114, 182), anchor="mm")

        row_y += row_height

    # Footer
    footer_y = height - 90
    draw.line([(45, footer_y), (width - 45, footer_y)], fill=(37, 52, 98), width=1)
    draw.text(
        (width // 2, footer_y + 28),
        "सभी प्रश्न 'सागर सर' (7+ वर्ष अनुभव) द्वारा रचित NMMS पुस्तक से लिए गए हैं",
        font=footer_gold,
        fill=(234, 179, 8),
        anchor="mm"
    )
    draw.text(
        (width // 2, footer_y + 60),
        "सागर कोचिंग सेन्टर, भगवानपुर (सुपौल, बिहार)   •   संपर्क: +91 91101 13671",
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
    total_participants: int = None
) -> io.BytesIO:
    """
    Generates a personalized Certificate / Topper Card for Rank 1, 2, or 3 (Design A Gold Edition).
    Features large circular avatar, clean vector laurels, zero missing glyphs, and Sagar Sir's blessings.
    """
    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(11, 19, 43))  # Royal Navy
    draw = ImageDraw.Draw(img)

    # Rank specifics
    if total_participants and total_participants > 1:
        out_of_str = f" (OUT OF {total_participants} STUDENTS)"
    else:
        out_of_str = ""

    if rank == 1:
        medal_title = f"1st RANK{out_of_str}  *  GOLD TOPPER"
        accent_color = (234, 179, 8)     # Gold
        accent_light = (253, 224, 71)
        award_name = "CERTIFICATE OF EXCELLENCE"
    elif rank == 2:
        medal_title = f"2nd RANK{out_of_str}  *  SILVER TOPPER"
        accent_color = (203, 213, 225)   # Silver
        accent_light = (241, 245, 249)
        award_name = "CERTIFICATE OF MERIT"
    else:
        medal_title = f"3rd RANK{out_of_str}  *  BRONZE TOPPER"
        accent_color = (217, 119, 6)     # Bronze
        accent_light = (251, 191, 36)
        award_name = "CERTIFICATE OF MERIT"

    # Outer Double Borders
    draw.rounded_rectangle([(18, 18), (width - 18, height - 18)], radius=16, outline=accent_color, width=2)
    draw.rounded_rectangle([(26, 26), (width - 26, height - 26)], radius=12, outline=(37, 52, 98), width=1)

    # Fonts
    brand_font = get_latin_font(30, is_bold=True)
    award_font = get_latin_font(18, is_bold=True)
    name_font = get_hindi_font(34, is_bold=True)
    test_font = get_latin_font(19, is_bold=True)
    stat_lbl_font = get_latin_font(16, is_bold=True)
    stat_val_font = get_latin_font(28, is_bold=True)
    wishes_font = get_hindi_font(18, is_bold=True)
    footer_font = get_hindi_font(17, is_bold=False)

    # Header with Logo
    header_y = 55
    if os.path.exists(LOGO_PATH):
        try:
            logo_img = Image.open(LOGO_PATH).convert("RGBA")
            logo_size = 90
            logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            img.paste(logo_img, ((width - logo_size) // 2, header_y), mask=logo_img.split()[3])
            header_y += logo_size + 15
        except Exception:
            header_y += 30

    draw.text((width // 2, header_y), "SAGAR COACHING CENTRE", font=brand_font, fill=(255, 255, 255), anchor="mm")
    header_y += 35
    draw.text((width // 2, header_y), "NMMS SCHOLARSHIP EXAMINATION", font=get_latin_font(20, is_bold=True), fill=accent_light, anchor="mm")
    header_y += 30
    draw.text((width // 2, header_y), award_name, font=award_font, fill=(148, 163, 184), anchor="mm")
    header_y += 24

    # Accent Divider
    draw.line([(width // 2 - 140, header_y), (width // 2 + 140, header_y)], fill=accent_color, width=2)
    header_y += 35

    # Student Large Profile Photo (140x140)
    avatar_size = 140
    av_x = (width - avatar_size) // 2
    av_y = header_y
    av_bytes = student.get("avatar_bytes")
    av_img = None
    if av_bytes:
        av_img = make_photo_avatar(av_bytes, size=avatar_size)
    if not av_img:
        av_img = make_fallback_avatar(student.get("name", "Student"), size=avatar_size, font=get_hindi_font(46, is_bold=True))

    draw.ellipse([(av_x - 6, av_y - 6), (av_x + avatar_size + 6, av_y + avatar_size + 6)], outline=accent_color, width=4)
    img.paste(av_img, (av_x, av_y), mask=av_img.split()[3])

    # Rank Badge pill under photo
    badge_y = av_y + avatar_size + 24
    badge_w = 520
    badge_h = 44
    draw.rounded_rectangle([((width - badge_w) // 2, badge_y), ((width + badge_w) // 2, badge_y + badge_h)], radius=22, fill=(19, 29, 61), outline=accent_color, width=2)
    draw.text((width // 2, badge_y + 22), medal_title, font=get_latin_font(18, is_bold=True), fill=accent_light, anchor="mm")

    # Student Name
    name_y = badge_y + 60
    s_name = str(student.get("name", "Student")).strip()
    draw.text((width // 2, name_y), s_name, font=name_font, fill=(255, 255, 255), anchor="mm")

    # Test Name & Total Participants (No set number leaked)
    test_y = name_y + 40
    clean_title = clean_test_title(test_name)
    if total_participants:
        test_info_str = f"{clean_title}   •   Total Candidates: {total_participants}"
    else:
        test_info_str = clean_title
    draw.text((width // 2, test_y), test_info_str, font=test_font, fill=(148, 163, 184), anchor="mm")

    # Metrics Strip
    stat_y = test_y + 45
    box_w = 230
    box_h = 95
    spacing = 25
    total_stat_w = (box_w * 3) + (spacing * 2)
    start_x = (width - total_stat_w) // 2

    effective_total = attempted_q if (attempted_q and attempted_q > 0) else total_q
    score_val = student.get("score", 0)
    acc_val = student.get("accuracy", 0.0)
    speed_val = student.get("avg_time", 0.0)

    stats_data = [
        ("SCORE", f"{score_val} / {effective_total}", (56, 189, 248)),
        ("ACCURACY", f"{acc_val:.1f}%", (74, 222, 128)),
        ("AVG SPEED", f"{speed_val:.1f}s", (244, 114, 182)),
    ]

    for i, (label, val, val_col) in enumerate(stats_data):
        bx = start_x + (i * (box_w + spacing))
        draw.rounded_rectangle([(bx, stat_y), (bx + box_w, stat_y + box_h)], radius=12, fill=(22, 34, 70), outline=(37, 52, 98), width=1)
        draw.text((bx + box_w // 2, stat_y + 26), label, font=stat_lbl_font, fill=(148, 163, 184), anchor="mm")
        draw.text((bx + box_w // 2, stat_y + 64), val, font=stat_val_font, fill=val_col, anchor="mm")

    # Best Wishes Ribbon
    wishes_y = stat_y + box_h + 26
    wishes_box_w = 720
    wishes_box_h = 65
    draw.rounded_rectangle([((width - wishes_box_w) // 2, wishes_y), ((width + wishes_box_w) // 2, wishes_y + wishes_box_h)], radius=12, fill=(19, 29, 61), outline=accent_color, width=1)
    
    draw.text(
        (width // 2, wishes_y + 22),
        "आपके उज्ज्वल भविष्य एवं NMMS में चयन की हार्दिक शुभकामनाएं!",
        font=wishes_font,
        fill=(253, 224, 71),
        anchor="mm"
    )
    draw.text(
        (width // 2, wishes_y + 46),
        "— सागर सर एवं समस्त सागर कोचिंग परिवार, भगवानपुर",
        font=get_hindi_font(15, is_bold=False),
        fill=(203, 213, 225),
        anchor="mm"
    )

    # Footer
    footer_y = height - 110
    draw.line([(60, footer_y), (width - 60, footer_y)], fill=(37, 52, 98), width=1)
    draw.text(
        (width // 2, footer_y + 25),
        "प्रश्न स्रोत: 'सागर सर' (7+ वर्ष अनुभव) द्वारा रचित NMMS पुस्तक",
        font=get_hindi_font(18, is_bold=True),
        fill=(253, 224, 71),
        anchor="mm"
    )
    draw.text(
        (width // 2, footer_y + 58),
        "सागर कोचिंग सेन्टर, भगवानपुर (सुपौल, बिहार)   •   संपर्क: +91 91101 13671",
        font=footer_font,
        fill=(203, 213, 225),
        anchor="mm"
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
