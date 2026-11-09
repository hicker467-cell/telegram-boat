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
    """Loads crisp, modern typography for English titles, headers, and numbers."""
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
    """Standardizes test name into a clean, professional English/Hindi title."""
    s = raw_name.strip()
    if "MAT" in s and "01" in s: return "MAT Full Mock Test - 01 (90 Questions)"
    if "MAT" in s and "02" in s: return "MAT Full Mock Test - 02 (90 Questions)"
    if "MAT" in s and "03" in s: return "MAT Full Mock Test - 03 (90 Questions)"
    if "SAT" in s and "01" in s: return "SAT Full Mock Test - 01 (90 Questions)"
    if "SAT" in s and "02" in s: return "SAT Full Mock Test - 02 (90 Questions)"
    if "SAT" in s and "03" in s: return "SAT Full Mock Test - 03 (90 Questions)"
    if "विज्ञान" in s and "सामाजिक" not in s:
        num = "".join([c for c in s if c.isdigit()])[:2] or "01"
        return f"Science Practice Test - Set {num} (50 Questions)"
    if "सामाजिक" in s or "सा. विज्ञान" in s:
        num = "".join([c for c in s if c.isdigit()])[:2] or "01"
        return f"Social Science Practice Test - Set {num} (50 Questions)"
    if "तर्कशक्ति" in s or "मानसिक" in s:
        num = "".join([c for c in s if c.isdigit()])[:2] or "01"
        return f"Mental Ability (MAT) - Set {num} (50 Questions)"
    if "गणित" in s:
        num = "".join([c for c in s if c.isdigit()])[:2] or "01"
        return f"Mathematics Practice Test - Set {num} (50 Questions)"
    return s

def generate_result_card(
    test_name: str,
    total_q: int,
    top_students: list,
    attempted_q: int = None,
    total_participants: int = None
) -> io.BytesIO:
    """
    Generates a high-resolution, branded result card for Sagar Coaching Centre.
    Displays Top 20 rankers with accurate accuracy percentages and premium typography.
    """
    width = 1200
    row_height = 50
    display_students = top_students[:20] if top_students else []
    num_rows = max(len(display_students), 3)

    if not total_participants:
        total_participants = len(top_students) if top_students else len(display_students)

    header_height = 185
    meta_height = 65
    table_header_h = 42
    footer_height = 95
    table_y = header_height + meta_height + 15
    height = table_y + table_header_h + (num_rows * row_height) + footer_height

    # Deep Navy Slate Canvas
    img = Image.new("RGB", (width, height), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)

    # Modern Premium Fonts (Segoe UI for English / Numbers, Nirmala for Hindi)
    title_font = get_latin_font(38, is_bold=True)
    subtitle_font = get_latin_font(21, is_bold=True)
    author_font = get_hindi_font(18, is_bold=False)
    info_font = get_latin_font(19, is_bold=True)
    th_font = get_latin_font(18, is_bold=True)
    row_font = get_hindi_font(19, is_bold=False)
    score_font = get_latin_font(19, is_bold=True)
    avatar_font = get_hindi_font(16, is_bold=True)
    book_font = get_hindi_font(19, is_bold=True)
    footer_contact_font = get_hindi_font(18, is_bold=False)

    # Header Background
    draw.rectangle([(0, 0), (width, header_height)], fill=(24, 32, 47))
    # Gold Accent Line below header
    draw.rectangle([(0, header_height - 5), (width, header_height)], fill=(234, 179, 8))

    # Draw Circular Logo
    logo_placed = False
    if os.path.exists(LOGO_PATH):
        try:
            logo_img = Image.open(LOGO_PATH).convert("RGBA")
            logo_size = 135
            logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            img.paste(logo_img, (55, 25), mask=logo_img.split()[3])
            logo_placed = True
        except Exception as e:
            print("Logo error:", e)

    # Header Typography
    text_x = 215 if logo_placed else (width // 2)
    align_mode = "lm" if logo_placed else "mm"

    # Subtitle with "Top 20 Out of X Students"
    if total_participants and total_participants > len(display_students):
        sub_text = f"NMMS SCHOLARSHIP EXAM • TOP 20 (OUT OF {total_participants} STUDENTS)"
    else:
        sub_text = f"NMMS SCHOLARSHIP EXAM • TOP RANKERS ({total_participants} STUDENTS)"

    draw.text((text_x, 46), "SAGAR COACHING CENTRE", font=title_font, fill=(255, 255, 255), anchor=align_mode)
    draw.text((text_x, 94), sub_text, font=subtitle_font, fill=(234, 179, 8), anchor=align_mode)
    draw.text((text_x, 138), "📍 Bhagwanpur (Supaul, Bihar)   |   ✍️ सागर सर (7+ वर्ष का अनुभव)", font=author_font, fill=(148, 163, 184), anchor=align_mode)

    # Meta Bar (Test Details)
    meta_box_y = header_height + 15
    draw.rounded_rectangle([(50, meta_box_y), (width - 50, meta_box_y + 44)], radius=8, fill=(30, 41, 59))
    clean_title = clean_test_title(test_name)
    date_str = datetime.now().strftime("%d-%m-%Y")
    
    if attempted_q and attempted_q < total_q:
        q_label = f"Questions: {attempted_q}/{total_q}"
    else:
        q_label = f"Total Questions: {total_q}"

    info_str = f"📝 {clean_title}   •   👥 {total_participants} Students   •   🎯 {q_label}   •   📅 {date_str}"
    draw.text((width // 2, meta_box_y + 22), info_str, font=info_font, fill=(226, 232, 240), anchor="mm")

    # Table Header Box
    table_x = 50
    table_w = width - (table_x * 2)
    th_y = meta_box_y + 55
    draw.rounded_rectangle([(table_x, th_y), (table_x + table_w, th_y + 38)], radius=6, fill=(30, 41, 59))

    # Columns:
    # Rank (70px) | Avatar (40px) | Name (380px) | Score (180px) | Accuracy (160px) | Avg Speed (180px)
    draw.text((table_x + 35, th_y + 19), "RANK", font=th_font, fill=(148, 163, 184), anchor="mm")
    draw.text((table_x + 130, th_y + 19), "STUDENT NAME", font=th_font, fill=(148, 163, 184), anchor="lm")
    draw.text((table_x + 580, th_y + 19), "SCORE", font=th_font, fill=(148, 163, 184), anchor="mm")
    draw.text((table_x + 785, th_y + 19), "ACCURACY", font=th_font, fill=(148, 163, 184), anchor="mm")
    draw.text((table_x + 980, th_y + 19), "AVG SPEED", font=th_font, fill=(148, 163, 184), anchor="mm")

    # Table Rows
    y = th_y + 45
    effective_total = attempted_q if (attempted_q and attempted_q > 0) else total_q

    avatar_size = 34

    for i, student in enumerate(display_students):
        bg_color = (24, 32, 47) if i % 2 == 0 else (19, 26, 38)
        border_fill = None
        if i == 0: border_fill = (234, 179, 8)       # Gold
        elif i == 1: border_fill = (203, 213, 225)   # Silver
        elif i == 2: border_fill = (217, 119, 6)     # Bronze

        row_h = 42
        draw.rounded_rectangle([(table_x, y), (table_x + table_w, y + row_h)], radius=6, fill=bg_color)
        if border_fill:
            draw.rectangle([(table_x, y), (table_x + 6, y + row_h)], fill=border_fill)

        # Rank
        medals = ["🥇 #1", "🥈 #2", "🥉 #3"]
        rank_text = medals[i] if i < len(medals) else f"#{i+1}"
        rank_color = (234, 179, 8) if i < 3 else (203, 213, 225)
        draw.text((table_x + 35, y + (row_h // 2)), rank_text, font=score_font, fill=rank_color, anchor="mm")

        # Name & Circular DP Avatar
        s_name = str(student.get("name", "Student")).strip()
        av_bytes = student.get("avatar_bytes")
        av_img = None
        if av_bytes:
            av_img = make_photo_avatar(av_bytes, size=avatar_size)
        if not av_img:
            av_img = make_fallback_avatar(s_name, size=avatar_size, font=avatar_font)

        # Paste circular avatar before name
        av_x = table_x + 80
        av_y = y + ((row_h - avatar_size) // 2)
        img.paste(av_img, (av_x, av_y), mask=av_img.split()[3])

        # Student Name text
        display_name = s_name
        if len(display_name) > 24:
            display_name = display_name[:22] + ".."
        name_x = av_x + avatar_size + 12
        draw.text((name_x, y + (row_h // 2)), display_name, font=row_font, fill=(255, 255, 255), anchor="lm")

        # Score
        score_val = student.get("score", 0)
        draw.text((table_x + 580, y + (row_h // 2)), f"{score_val} / {effective_total}", font=score_font, fill=(56, 189, 248), anchor="mm")

        # Accuracy (%) — accurately calculated per student
        pct = student.get("accuracy")
        if pct is None:
            pct = (score_val / effective_total * 100) if effective_total > 0 else 0
        draw.text((table_x + 785, y + (row_h // 2)), f"{pct:.1f}%", font=score_font, fill=(74, 222, 128), anchor="mm")

        # Avg Speed
        avg_time = student.get("avg_time", 0.0)
        draw.text((table_x + 980, y + (row_h // 2)), f"{avg_time:.1f}s / Q", font=score_font, fill=(244, 114, 182), anchor="mm")

        y += row_height

    # Footer Branding (Zero mention of "order" / clean and prestigious)
    footer_box_y = height - 85
    draw.line([(50, footer_box_y), (width - 50, footer_box_y)], fill=(51, 65, 85), width=1)
    
    # Book Credit Line (Author: Sagar Sir, 7+ Years Experience)
    draw.text(
        (width // 2, footer_box_y + 22),
        "📖 सभी प्रश्न 'सागर सर' (7+ वर्ष अनुभव) द्वारा रचित NMMS पुस्तक से लिए गए हैं",
        font=book_font,
        fill=(253, 224, 71),  # gold-300
        anchor="mm"
    )
    # Contact & Centre Line
    draw.text(
        (width // 2, footer_box_y + 54),
        "🏛️ सागर कोचिंग सेन्टर, भगवानपुर (सुपौल, बिहार)   •   📞 संपर्क: +91 91101 13671",
        font=footer_contact_font,
        fill=(203, 213, 225),  # slate-300
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
    Generates a personalized Certificate / Topper Card for Rank 1, 2, or 3.
    Features large circular avatar, metallic laurels, statistics, and official branding.
    """
    width, height = 900, 1150
    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # slate-900
    draw = ImageDraw.Draw(img)

    # Rank specifics
    if total_participants and total_participants > 1:
        out_of_str = f" (OUT OF {total_participants} STUDENTS)"
    else:
        out_of_str = ""

    if rank == 1:
        medal_title = f"🥇 1st RANK{out_of_str}"
        accent_color = (234, 179, 8)     # Gold
        accent_light = (253, 224, 71)
        award_name = "CERTIFICATE OF EXCELLENCE"
    elif rank == 2:
        medal_title = f"🥈 2nd RANK{out_of_str}"
        accent_color = (203, 213, 225)   # Silver
        accent_light = (241, 245, 249)
        award_name = "CERTIFICATE OF MERIT"
    else:
        medal_title = f"🥉 3rd RANK{out_of_str}"
        accent_color = (217, 119, 6)     # Bronze
        accent_light = (251, 191, 36)
        award_name = "CERTIFICATE OF MERIT"

    # Outer Decorative Double Borders
    draw.rounded_rectangle([(18, 18), (width - 18, height - 18)], radius=16, outline=accent_color, width=2)
    draw.rounded_rectangle([(26, 26), (width - 26, height - 26)], radius=12, outline=(51, 65, 85), width=1)

    # Fonts
    brand_font = get_latin_font(30, is_bold=True)
    award_font = get_latin_font(18, is_bold=True)
    name_font = get_hindi_font(34, is_bold=True)
    test_font = get_latin_font(19, is_bold=True)
    stat_lbl_font = get_latin_font(16, is_bold=True)
    stat_val_font = get_latin_font(28, is_bold=True)
    footer_font = get_hindi_font(18, is_bold=False)

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

    # Student Large Profile Photo (140x140) with Metallic Ring
    avatar_size = 140
    av_x = (width - avatar_size) // 2
    av_y = header_y
    av_bytes = student.get("avatar_bytes")
    av_img = None
    if av_bytes:
        av_img = make_photo_avatar(av_bytes, size=avatar_size)
    if not av_img:
        av_img = make_fallback_avatar(student.get("name", "Student"), size=avatar_size, font=get_hindi_font(46, is_bold=True))

    # Outer glowing ring
    draw.ellipse([(av_x - 6, av_y - 6), (av_x + avatar_size + 6, av_y + avatar_size + 6)], outline=accent_color, width=4)
    img.paste(av_img, (av_x, av_y), mask=av_img.split()[3])

    # Rank Badge pill under photo
    badge_y = av_y + avatar_size + 24
    badge_w = 480
    badge_h = 44
    draw.rounded_rectangle([((width - badge_w) // 2, badge_y), ((width + badge_w) // 2, badge_y + badge_h)], radius=22, fill=(24, 32, 47), outline=accent_color, width=2)
    draw.text((width // 2, badge_y + 22), medal_title, font=get_latin_font(19, is_bold=True), fill=accent_light, anchor="mm")

    # Student Name
    name_y = badge_y + 60
    s_name = str(student.get("name", "Student")).strip()
    draw.text((width // 2, name_y), s_name, font=name_font, fill=(255, 255, 255), anchor="mm")

    # Test Name & Total Participants
    test_y = name_y + 40
    clean_title = clean_test_title(test_name)
    if total_participants:
        test_info_str = f"{clean_title}   •   Total Participants: {total_participants}"
    else:
        test_info_str = clean_title
    draw.text((width // 2, test_y), test_info_str, font=test_font, fill=(148, 163, 184), anchor="mm")

    # Metrics Strip (3 Modern Boxes: Score, Accuracy, Speed)
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
        draw.rounded_rectangle([(bx, stat_y), (bx + box_w, stat_y + box_h)], radius=12, fill=(30, 41, 59), outline=(51, 65, 85), width=1)
        draw.text((bx + box_w // 2, stat_y + 26), label, font=stat_lbl_font, fill=(148, 163, 184), anchor="mm")
        draw.text((bx + box_w // 2, stat_y + 64), val, font=stat_val_font, fill=val_col, anchor="mm")

    # Footer Branding
    footer_y = height - 120
    draw.line([(60, footer_y), (width - 60, footer_y)], fill=(51, 65, 85), width=1)
    draw.text(
        (width // 2, footer_y + 28),
        "📖 प्रश्न स्रोत: 'सागर सर' (7+ वर्ष अनुभव) द्वारा रचित NMMS पुस्तक",
        font=get_hindi_font(19, is_bold=True),
        fill=(253, 224, 71),
        anchor="mm"
    )
    draw.text(
        (width // 2, footer_y + 62),
        "🏛️ सागर कोचिंग सेन्टर, भगवानपुर (सुपौल, बिहार)   •   📞 संपर्क: +91 91101 13671",
        font=footer_font,
        fill=(203, 213, 225),
        anchor="mm"
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
