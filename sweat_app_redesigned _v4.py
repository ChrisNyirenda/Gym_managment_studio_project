import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont , ImageOps
import treepoem
import os
import sqlite3
import random
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, LongTable, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# ---------------- SWEAT APP VISUAL DESIGN SYSTEM ----------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg": "#0B0D10", "surface": "#12161C", "surface_2": "#181D24",
    "surface_3": "#202630", "border": "#2B323D", "text": "#F4F5F7",
    "muted": "#98A2B3", "accent": "#F43F5E", "accent_hover": "#FB7185",
    "success": "#22C55E", "success_hover": "#34D399",
    "danger": "#EF4444", "danger_hover": "#F87171",
}
FONT = "Arial"

def _style_button(button, kind="secondary"):
    palettes = {
        "primary": (COLORS["accent"], COLORS["accent_hover"]),
        "success": (COLORS["success"], COLORS["success_hover"]),
        "danger": (COLORS["danger"], COLORS["danger_hover"]),
        "secondary": (COLORS["surface_3"], COLORS["border"]),
    }
    fg, hover = palettes.get(kind, palettes["secondary"])
    button.configure(fg_color=fg, hover_color=hover, corner_radius=10,
                     height=40, font=(FONT, 13, "bold"), border_width=0)
    return button

def _style_entry(entry, height=46):
    entry.configure(height=height, corner_radius=10, fg_color=COLORS["surface_2"],
                    border_color=COLORS["border"], border_width=1,
                    text_color=COLORS["text"], placeholder_text_color=COLORS["muted"],
                    font=(FONT, 13))
    return entry
conn = sqlite3.connect('sweat_new.db')  # This will create the file if it doesn't exist
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS comments
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT NOT NULL,
        comment TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

c.execute('''CREATE TABLE IF NOT EXISTS data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone INTEGER,
    address TEXT,
    barcode TEXT 
)''')
c.execute('''CREATE TABLE IF NOT EXISTS PracticeCredits(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    practice_type TEXT NOT NULL,
    credits INTEGER NOT NULL,
    barcode TEXT ,
    last_checkin TIMESTAMP, 
    customer_id INTEGERs
)''')
c.execute('''CREATE TABLE IF NOT EXISTS datetime (
    date TEXT NOT NULL,
    time timestamp NOT NULL,
    barcode TEXT NOT NULL
)''')

c.execute('''CREATE TABLE IF NOT EXISTS checkinHistory (
    datetime TIMESTAMP ,
    barcode  TEXT NOT NULL 
)''')

c.execute('''CREATE TABLE IF NOT EXISTS comments (
    comment TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    barcode TEXT NOT NULL
)''')




conn.commit()
conn.close()

    
db_path = "sweat_new.db"
logo_path = "logol.png"
try:
    import treepoem
    _HAS_TREEPOEM = True
except Exception:
    _HAS_TREEPOEM = False


def _load_fonts():
    bold_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "arialbd.ttf",
    ]
    regular_candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial.ttf",
        "arial.ttf",
    ]
    font_title = None
    font_name = None
    font_small = None
    font_tiny = None
    for p in bold_candidates:
        try:
            font_title = ImageFont.truetype(p, 28)
            break
        except Exception:
            continue
    for p in regular_candidates:
        try:
            font_name = ImageFont.truetype(p, 30)
            font_small = ImageFont.truetype(p, 16)
            font_tiny = ImageFont.truetype(p, 12)
            break
        except Exception:
            continue
    if font_title is None:
        font_title = ImageFont.load_default()
    if font_name is None:
        font_name = ImageFont.load_default()
    if font_small is None:
        font_small = ImageFont.load_default()
    if font_tiny is None:
        font_tiny = ImageFont.load_default()
    return font_title, font_name, font_small, font_tiny


def _draw_fallback_barcode(data: str, width: int, height: int):
    """Draw a simple bar pattern with plain PIL, used only when treepoem
    can't produce a real barcode (most commonly because Ghostscript isn't
    installed/on PATH on this machine — treepoem shells out to it).

    This is NOT a scannable barcode, just a visual placeholder so that
    card creation never crashes and a card image is always saved.
    """
    img = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(img)
    digits = ''.join(filter(str.isdigit, str(data))) or "0"
    n_bars = 50
    seq = (digits * ((n_bars // len(digits)) + 1))[:n_bars]
    bar_w = max(1, width // n_bars)
    x = 0
    for ch in seq:
        if int(ch) % 2 == 0:
            d.rectangle([x, 0, x + bar_w - 1, height - 1], fill=(10, 10, 10))
        x += bar_w
    return img


def create_card(first_name, last_name, email, phone, member_id, output_path=None):
    """Create a stylized membership card and embed a barcode for `member_id`.

    Uses `treepoem` to create a EAN-13 barcode when available; otherwise draws
    a Code128 barcode as a fallback.
    """
    # Default to cards folder with member_id as filename
    if output_path is None:
        output_path = f"cards/{first_name} {last_name}.png"
    # Card dimensions
    width, height = 600, 360

    # Colors
    black = (10, 10, 10)
    red = (225, 29, 72)
    white = (255, 255, 255)
    gray = (156, 163, 175)

    card = Image.new('RGB', (width, height), white)
    draw = ImageDraw.Draw(card)

    font_title, font_name, font_small, font_tiny = _load_fonts()

    # Header: try to load logo image and center it in the stripe
    logo_file = "logol.png"
    try:
        logo_img = Image.open(logo_file).convert("RGBA")
        # Fit logo into stripe height (leave small padding)
        max_logo_h = 120
        max_logo_w = width - 20
        logo_img = ImageOps.contain(logo_img, (max_logo_w, max_logo_h))
        lx = (width - logo_img.width) // 2
        ly = (64 - logo_img.height) // 2
        card.paste(logo_img, (lx, ly), logo_img)
    except Exception:
        # Fallback to text header if logo missing
        draw.text((48, 18), "SWEATCORE", fill=white, font=font_title)
        # MEMBER badge on right
        m_w, m_h = draw.textbbox((0, 0), "MEMBER", font=font_small)[2:]
        draw.text((width - 20 - m_w, 22), "MEMBER", fill=white, font=font_small)

    # Name and contact
    full_name = f"{first_name.upper()} {last_name.upper()}"
    draw.text((36, 100), full_name, fill=black, font=font_name, size=60)
    draw.text((36, 170), phone, fill=gray, font=font_name, size=100)

    # Member ID label removed - barcode will cover the base

    # Generate barcode image (ensure data is a string; handle missing treepoem)
    margin = 10
    desired_w = 400  # very wide across the card
    # Shorter barcode height (around 14-16% of card height)
    desired_h = 120

    barcode_img = None
    if _HAS_TREEPOEM:
        try:
            # Extract digits from member_id and pad/truncate to 13 for EAN-13
            digits_only = ''.join(filter(str.isdigit, str(member_id)))
            ean_data = digits_only[-13:].zfill(13) if digits_only else '0000000000000'
            barcode_img = treepoem.generate_barcode(
                barcode_type="ean13",
                data=ean_data
            ).convert("RGB")
        except Exception as e:
            print(f"EAN-13 barcode generation failed ({e}); trying Code128.")
            try:
                # Fallback to Code128 if EAN-13 fails
                barcode_img = treepoem.generate_barcode(
                    barcode_type="code128",
                    data=str(member_id)
                ).convert("RGB")
            except Exception as e2:
                print(f"Code128 barcode generation also failed ({e2}).")
                barcode_img = None

    if barcode_img is None:
        # treepoem needs Ghostscript installed and on PATH; if that's
        # missing (common on Windows) or treepoem itself isn't installed,
        # draw a placeholder instead of crashing so the card still saves.
        print("Using a locally-drawn placeholder barcode (treepoem/Ghostscript unavailable).")
        barcode_img = _draw_fallback_barcode(str(member_id), desired_w, desired_h)

    barcode_img = barcode_img.resize((desired_w, desired_h), resample=Image.LANCZOS)
    bx = (width - barcode_img.width) // 2
    # lift barcode up so it doesn't touch the bottom (lift value in px)
    lift_up = 15
    by = max(8, height - barcode_img.height - lift_up)
    card.paste(barcode_img, (bx, by))

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    card.save(output_path)
    return output_path




def checkin(barcode_input: str) -> str:
    conn = sqlite3.connect("sweat_new.db")
    c = conn.cursor()

    # Get stored date from database
    c.execute("SELECT date FROM datetime WHERE barcode = ?", (barcode_input,))
    record = c.fetchone()
    
    if record:
        # Convert strings to date objects
        stored_date = datetime.datetime.strptime(record[0], "%Y-%m-%d").date()
        current_date = datetime.datetime.now().date()  # Already a date object
        
        # Now subtraction will work
        date_difference = (current_date - stored_date).days

    if date_difference < 30:
            c.execute("SELECT * FROM PracticeCredits WHERE barcode = ?", (barcode_input,))
            record = c.fetchone()

            if record:
             credits = record[3]  # Assuming credits is the 4th column
             if credits > 0:
                new_credits = credits - 1
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute(
                    "UPDATE PracticeCredits SET credits = ?, last_checkin = ? WHERE barcode = ?",
                    (new_credits, now, barcode_input)
                )
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                time_str = datetime.datetime.now().strftime("%H:%M:%S")
                c.execute("INSERT INTO checkinHistory (datetime, barcode) VALUES (?, ?)", (now, barcode_input))
                c.execute("INSERT INTO datetime (barcode, date, time) VALUES (?, ?, ?)", (barcode_input, date_str, time_str))


                conn.commit()
                conn.close()
                return f"✅ Check-in successful! Remaining credits: {new_credits}"
             else:
                conn.close()
                return "⚠️ No credits remaining. Please recharge."
            
            else:
                conn.close()
                return "❌ Barcode not found."
    else:
        conn.close()
        return "❌ Your credits have been paused. Please try again later."
    
def refresh_data_display(frame):
    # Clear previous widgets
    for widget in frame.winfo_children():
        widget.destroy()

    columns, rows = fetch_data()
    # Display column headers
    for col_idx, col_name in enumerate(columns):
        label = ctk.CTkLabel(frame, text=col_name, font=("Arial", 12, "bold"))
        label.grid(row=0, column=col_idx, padx=5, pady=2)
    # Display rows
    for row_idx, row in enumerate(rows, start=1):
        for col_idx, value in enumerate(row):
            label = ctk.CTkLabel(frame, text=str(value), font=("Arial", 12))
            label.grid(row=row_idx, column=col_idx, padx=5, pady=2)

def fetch_data():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM data")
    rows = c.fetchall()
    columns = [description[0] for description in c.description]
    conn.close()
    
    return columns, rows

def fetch_practice_credits_by_barcode(barcode):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("PRAGMA table_info(PracticeCredits)")
    credit_columns = [info[1] for info in c.fetchall()]
    c.execute("SELECT * FROM PracticeCredits WHERE barcode = ?", (barcode,))
    credits = c.fetchall()
    conn.close()
    return credit_columns, credits

def print_checkin_history(barcode: str):
    """
    Generate PDF for customer history.
    - Returns a success string with the filename.
    - Raises an exception on error (caught by UI).
    - Automatically opens the folder on success.
    """
    # 1. Fetch Customer Info
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM data WHERE barcode = ?", (barcode,))
    customer = c.fetchone()
    
    if not customer:
        conn.close()
        raise ValueError(f"No customer found for barcode: {barcode}")

    c.execute("PRAGMA table_info(data)")
    data_cols = [info[1] for info in c.fetchall()]

    # 2. Fetch Practice Credits
    c.execute("SELECT practice_type, credits FROM PracticeCredits WHERE barcode = ?", (barcode,))
    credits_rows = c.fetchall()

    # 3. Fetch Check-ins (Unique Set)
    unique_checkins = set()
    
    # Source A: datetime table
    c.execute("SELECT date, time FROM datetime WHERE barcode = ?", (barcode,))
    for row in c.fetchall():
        unique_checkins.add(row)
    
    # Source B: checkinHistory table
    try:
        c.execute("SELECT datetime FROM checkinHistory WHERE barcode = ?", (barcode,))
        for row in c.fetchall():
            dt_str = str(row[0])
            if " " in dt_str:
                unique_checkins.add(tuple(dt_str.split(" ", 1)))
            else:
                unique_checkins.add((dt_str, ""))
    except sqlite3.OperationalError:
        pass 

    conn.close()

    # Sort data
    sorted_checkins = sorted(list(unique_checkins), key=lambda x: (x[0], x[1]), reverse=True)

    # --- PDF CONSTRUCTION ---
    os.makedirs("prints", exist_ok=True)
    name = customer[data_cols.index('name')] if 'name' in data_cols else 'customer'
    filename = f"{name}_history.pdf"
    pdf_path = os.path.join("prints", filename)

    doc = SimpleDocTemplate(
        pdf_path, 
        pagesize=A4, 
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('MainTitle', parent=styles['Title'], fontSize=22, textColor=colors.HexColor("#2C3E50"), spaceAfter=12)
    story.append(Paragraph("Customer Check-in History", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2C3E50"), spaceAfter=15))

    # Details
    story.append(Paragraph("<b>Customer Details</b>", styles["Heading3"]))
    info_data = []
    for idx, col in enumerate(data_cols):
        val = customer[idx] if customer[idx] is not None else "N/A"
        info_data.append([
            Paragraph(f"<b>{col.replace('_', ' ').upper()}:</b>", styles['Normal']), 
            Paragraph(str(val), styles['Normal'])
        ])
    
    info_table = Table(info_data, colWidths=[1.8*inch, 4*inch])
    info_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    story.append(info_table)
    story.append(Spacer(1, 20))

    # Credits
    story.append(Paragraph("<b>Practice Credits Remaining</b>", styles["Heading3"]))
    if credits_rows:
        cred_data = [["PRACTICE TYPE", "CREDITS"]]
        for pt, cr in credits_rows:
            cred_data.append([str(pt), str(cr)])
        ct = Table(cred_data, colWidths=[3.5*inch, 1.5*inch])
        ct.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#BDC3C7")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (1,0), (1,-1), 'CENTER'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(ct)
    else:
        story.append(Paragraph("No credits found on record.", styles['Italic']))
    
    story.append(Spacer(1, 25))

    # Logs
    story.append(Paragraph("<b>Check-in Activity Log</b>", styles["Heading3"]))
    if sorted_checkins:
        history_data = [["DATE", "TIME", "STATUS"]]
        for d, tme in sorted_checkins:
            history_data.append([str(d), str(tme), "VERIFIED"])

        ht = LongTable(history_data, colWidths=[2*inch, 2*inch, 1.5*inch], repeatRows=1)
        ht.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D5DBDB")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(ht)
    else:
        story.append(Paragraph("No activity recorded for this barcode.", styles['Italic']))

    doc.build(story)

    # Automatically open the folder for convenience (non-blocking)
    try:
        os.startfile("prints")
    except Exception:
        pass # Ignore if on non-Windows or fails

    return f"PDF Generated: {filename}"


def recharge_credits(barcode: str, amount_or_type: str):
    """
    Recharge practice credits. 
    Returns a success message string if successful.
    Raises an exception if something goes wrong (which the UI will catch).
    """
    val = amount_or_type.strip()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Ensure table exists
    c.execute('''CREATE TABLE IF NOT EXISTS PracticeCredits
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, practice_type TEXT, barcode TEXT, credits INTEGER)''')

    mapping = {
        "FLEX 2X": 2,
        "STANDARD 4X 50$": 4,
        "STANDARD 8X 80$": 8,
        "STANDARD 12X 100$": 12,
        "UPGRADE 4X 50$": 4,
        "UPGRADE 8X 80$": 8,
        "UPGRADE 12X 100$": 12,
    }

    amount = None
    if val.isdigit():
        amount = int(val)
        c.execute("UPDATE PracticeCredits SET credits = credits + ? WHERE barcode = ?", (amount, barcode))
        if c.rowcount == 0:
            c.execute("INSERT INTO PracticeCredits (practice_type, barcode, credits) VALUES (?, ?, ?)", ("DEFAULT", barcode, amount))
    
    elif val in mapping:
        amount = mapping[val]
        c.execute("UPDATE PracticeCredits SET credits = credits + ? WHERE barcode = ? AND practice_type = ?", (amount, barcode, val))
        if c.rowcount == 0:
            c.execute("INSERT INTO PracticeCredits (practice_type, barcode, credits) VALUES (?, ?, ?)", (val, barcode, amount))
    
    else:
        # Try to extract a number from the string
        import re
        nums = re.findall(r"\d+", val)
        if nums:
            amount = int(nums[0])
            c.execute("UPDATE PracticeCredits SET credits = credits + ? WHERE barcode = ?", (amount, barcode))
            if c.rowcount == 0:
                c.execute("INSERT INTO PracticeCredits (practice_type, barcode, credits) VALUES (?, ?, ?)", ("DEFAULT", barcode, amount))
        else:
            conn.close()
            # We raise an error here so the UI knows to show Red Text
            raise ValueError("Invalid recharge value.")

    conn.commit()
    conn.close()

    # Refresh UI if app exists
    if 'app' in globals() and hasattr(app, 'refresh_home_table'):
        try:
            app.refresh_home_table()
        except Exception:
            pass

    # Return the message to be displayed in the Green Label
    return f"Success! Recharged {amount} credits."

def fetch_checkins_by_barcode(barcode):
    """Fetch check-in data (date, time) from datetime table in sweat_new.db"""
    conn = sqlite3.connect("sweat_new.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT date, time 
            FROM datetime 
            WHERE barcode = ? 
            ORDER BY date DESC, time DESC
        """, (barcode,))
        
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print("Database error:", e)
        rows = []
    finally:
        conn.close()

    return rows

def build_profile_page(parent, customer_data, columns, app):
    """Build the customer-profile view inside `parent` (an in-window page
    frame) instead of a separate popup window. `app` is the App instance,
    used to navigate back to other pages and to refresh the home table.
    """
    # Initialize database tables
    initialize_database()

    ctk.CTkButton(
        parent, text="← Back to Home", fg_color=COLORS["surface_3"], hover_color=COLORS["accent"],
        command=app.show_home
    ).pack(anchor="w", padx=20, pady=(10, 0))

    # Main container
    main_frame = ctk.CTkFrame(parent, fg_color=COLORS["surface"], corner_radius=18, border_width=1, border_color=COLORS["border"])
    main_frame.pack(padx=20, pady=20, fill="both", expand=True)
    
    main_frame.grid_rowconfigure(0, weight=1)  
    main_frame.grid_rowconfigure(1, weight=3)  
    main_frame.grid_columnconfigure(0, weight=1)
    main_frame.grid_columnconfigure(1, weight=1)
    
    # Profile section
    profile_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["surface_2"], corner_radius=16, border_width=1, border_color=COLORS["border"])
    profile_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
    
    # Configure profile frame grid
    for i in range(30):
        profile_frame.grid_rowconfigure(i, weight=1)
    for j in range(7):
        profile_frame.grid_columnconfigure(j, weight=1)

    num_cols = 7
    row_num = 0

    # Display profile info
    for i in range(0, len(columns), num_cols):
        for j in range(num_cols):
            idx = i + j
            if idx < len(columns):
                col = columns[idx]
                value = customer_data[idx]
                label = ctk.CTkLabel(profile_frame, text=f"{col}: {value}", font=("Arial", 13))
                label.grid(row=row_num, column=j, padx=10, pady=5, sticky="nsew")
        row_num += 1

    # Practice credits
    barcode = customer_data[columns.index("barcode")]
    credit_columns, credits = fetch_practice_credits_by_barcode(barcode)

    if credits:
        header = ctk.CTkLabel(profile_frame, text="Practice Credits for this customer:", font=("Arial", 14, "bold"))
        header.grid(row=row_num, column=0, columnspan=len(credit_columns), padx=10, pady=10, sticky="w")
        row_num += 1

        for col_idx, col_name in enumerate(credit_columns):
            col_label = ctk.CTkLabel(profile_frame, text=col_name, font=("Arial", 12, "bold"))
            col_label.grid(row=row_num, column=col_idx, padx=5, pady=2, sticky="nsew")
        row_num += 1

        for credit in credits:
            for col_idx, value in enumerate(credit):
                val_label = ctk.CTkLabel(profile_frame, text=str(value), font=("Arial", 12))
                val_label.grid(row=row_num, column=col_idx, padx=5, pady=2, sticky="nsew")
            row_num += 1
    else:
        label = ctk.CTkLabel(profile_frame, text="No practice credits found.", font=("Arial", 13, "italic"))
        label.grid(row=row_num, column=0, columnspan=num_cols, padx=10, pady=10, sticky="w")
        row_num += 1
    status_label = ctk.CTkLabel(profile_frame, text="", text_color="green")
    status_label.grid(row=row_num + 1, column=2, columnspan=2, pady=5)
    # Controls row
    label_bonusdays = ctk.CTkLabel(profile_frame, text="Bonus Days:", font=("Arial", 14, "bold"))
    label_bonusdays.grid(row=row_num, column=1, padx=(20,10), pady=10, sticky="w")

    entry_bonusdays = ctk.CTkEntry(profile_frame, placeholder_text="RECHARGE CREDITS")
    entry_bonusdays.grid(row=row_num, column=2, padx=10, pady=10, sticky="ew")

    def apply_bonus():
        bonus_days = entry_bonusdays.get()
        if not bonus_days:
            return

        try:
            success_msg = recharge_credits(barcode, bonus_days)
            
            
            status_label.configure(text=success_msg, text_color="green")
            entry_bonusdays.delete(0, "end")
            status_label.after(3000, lambda: status_label.configure(text=""))

        except Exception as e:
            status_label.configure(text=f"Error: {e}", text_color="red")
            status_label.after(5000, lambda: status_label.configure(text=""))
   
    button_bonusdays = ctk.CTkButton(profile_frame, text="Apply", fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"] , command=apply_bonus)
    button_bonusdays.grid(row=row_num, column=3, padx=10, pady=10, sticky="ew")
    
    button_edit = ctk.CTkButton(profile_frame, text="Edit", fg_color=COLORS["success"], hover_color=COLORS["success_hover"], command=lambda: app.show_edit_profile_page(customer_data, columns))
    button_edit.grid(row=row_num, column=4, padx=10, pady=10, sticky="ew")
    # Wrapper function to handle printing and update the status label
    def print_history_action(barcode):
        try:
            # Call the function and get the success message
            msg = print_checkin_history(barcode)
            
            # Update label to GREEN
            status_label.configure(text=msg, text_color="green")
            
            # Clear message after 3 seconds
            status_label.after(3000, lambda: status_label.configure(text=""))
            
        except Exception as e:
            # Update label to RED on error
            status_label.configure(text=f"Print Error: {e}", text_color="red")
            status_label.after(5000, lambda: status_label.configure(text=""))

    # Update the button to use the wrapper function
    button_printcheckinhistroy = ctk.CTkButton(
        profile_frame, 
        text="Print History", 
        fg_color=COLORS["surface_3"], hover_color=COLORS["accent"], 
        command=lambda: print_history_action(barcode)
    )
    button_printcheckinhistroy.grid(row=row_num, column=5, padx=10, pady=10, sticky="ew")
    
    def delete_profile(): 
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("DELETE FROM data WHERE barcode = ?", (barcode,))
            c.execute("DELETE FROM PracticeCredits WHERE barcode = ?", (barcode,))
            c.execute("DELETE FROM comments WHERE barcode = ?", (barcode,))
            c.execute("DELETE FROM datetime WHERE barcode = ?", (barcode,))
            conn.commit()
            conn.close()
            app.show_home()
            app.refresh_home_table()
        except sqlite3.Error as e:
            print(f"Error deleting profile: {e}")

    button_close = ctk.CTkButton(profile_frame, text="DELETE", fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"], command=delete_profile)
    button_close.grid(row=row_num, column=6, padx=10, pady=10, sticky="ew")
    
    # Check-ins section (left half)
    checkins_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["surface"], corner_radius=16, border_width=1, border_color=COLORS["border"])
    checkins_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    
    checkins_frame.grid_rowconfigure(0, weight=0)  
    checkins_frame.grid_rowconfigure(1, weight=1)  
    checkins_frame.grid_columnconfigure(0, weight=1)
    
    checkins_header = ctk.CTkLabel(checkins_frame, text="Customer Check-ins", font=("Arial", 16, "bold"))
    checkins_header.grid(row=0, column=0, padx=10, pady=10, sticky="w")
    
    scrollable_frame = ctk.CTkScrollableFrame(checkins_frame)
    scrollable_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    scrollable_frame.grid_columnconfigure(0, weight=1)

    # Fetch check-ins from DB
    checkin_data = fetch_checkins_by_barcode(barcode)
    
    if checkin_data:
        headers = ["Date", "Time", "Status"]
        for col_idx, header in enumerate(headers):
            header_label = ctk.CTkLabel(scrollable_frame, text=header, font=("Arial", 12, "bold"))
            header_label.grid(row=0, column=col_idx, padx=5, pady=5, sticky="w")

        for row_idx, (date_val, time_val) in enumerate(checkin_data, start=1):
            date_label = ctk.CTkLabel(scrollable_frame, text=str(date_val), font=("Arial", 11))
            date_label.grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")

            time_label = ctk.CTkLabel(scrollable_frame, text=str(time_val), font=("Arial", 11))
            time_label.grid(row=row_idx, column=1, padx=5, pady=2, sticky="w")

            status_label = ctk.CTkLabel(scrollable_frame, text="Checked In", font=("Arial", 11))
            status_label.grid(row=row_idx, column=2, padx=5, pady=2, sticky="w")
    else:
        no_checkins_label = ctk.CTkLabel(
            scrollable_frame, 
            text="No check-ins found for this customer.", 
            font=("Arial", 13, "italic")
        )
        no_checkins_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    # === Comments section (right half) ===
    comments_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["surface"], corner_radius=16, border_width=1, border_color=COLORS["border"])
    comments_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
    comments_frame.grid_rowconfigure(1, weight=1)  # ✅ make list area expandable
    comments_frame.grid_columnconfigure(0, weight=1)

    comments_header = ctk.CTkLabel(comments_frame, text="Customer Comments", font=("Arial", 16, "bold"))
    comments_header.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    # === Scrollable area for previous comments ===
    comments_list = ctk.CTkScrollableFrame(comments_frame)
    comments_list.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
    comments_list.grid_columnconfigure(0, weight=1)

    # === Input box for new comment ===
    comments_text = ctk.CTkTextbox(comments_frame, width=200, height=100)
    comments_text.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

    def load_comments(barcode):
        """Load and display previous comments for this customer."""
        try:
            for widget in comments_list.winfo_children():
                widget.destroy()  # clear old list before reloading

            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Check if comments table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comments'")
            if not c.fetchone():
                # Create table if it doesn't exist
                c.execute('''CREATE TABLE IF NOT EXISTS comments
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             barcode TEXT NOT NULL,
                             comment TEXT NOT NULL,
                             created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                conn.commit()
                print("Comments table created")
                return
            
            c.execute("SELECT comment, created_at FROM comments WHERE barcode=? ORDER BY id DESC", (barcode,))
            all_comments = c.fetchall()
            conn.close()

            if all_comments:
                for row_idx, (comment_text, created_at) in enumerate(all_comments):
                    comment_label = ctk.CTkLabel(
                        comments_list,
                        text=f"[{created_at}] {comment_text}",
                        font=("Arial", 12),
                        wraplength=350,  # ✅ wraps text nicely
                        justify="left"
                    )
                    comment_label.grid(row=row_idx, column=0, sticky="w", padx=5, pady=2)
            else:
                no_comments_label = ctk.CTkLabel(comments_list, text="No comments yet.", font=("Arial", 12, "italic"))
                no_comments_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
                
        except Exception as e:
            print(f"Error loading comments: {e}")
            error_label = ctk.CTkLabel(comments_list, text="Error loading comments", font=("Arial", 12, "italic"))
            error_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    def on_com(barcode):
        """Save new comment to DB and refresh list."""
        try:
            comment = comments_text.get("1.0", "end-1c").strip()  # Fixed: use "end-1c" instead of ctk.END
            if comment:
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                
                # Ensure table exists
                c.execute('''CREATE TABLE IF NOT EXISTS comments
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             barcode TEXT NOT NULL,
                             comment TEXT NOT NULL,
                             created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                
                c.execute("INSERT INTO comments (comment, barcode, created_at) VALUES (?, ?, ?)", 
                         (comment, barcode, time))
                conn.commit()
                conn.close()
                comments_text.delete("1.0", "end")  # clear input
                load_comments(barcode)  # refresh list
        except Exception as e:
            print(f"Error saving comment: {e}")

    save_comment_button = ctk.CTkButton(
        comments_frame, 
        text="Save Comment", 
        fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
        command=lambda: on_com(barcode)
    )
    save_comment_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

    # ✅ load comments when profile opens
    load_comments(barcode)

def initialize_database():
    """Initialize all required database tables"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        tables = {
            'comments': '''
                CREATE TABLE IF NOT EXISTS comments
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 barcode TEXT NOT NULL,
                 comment TEXT NOT NULL,
                 created_at DATETIME DEFAULT CURRENT_TIMESTAMP)
            ''',
            'checkins': '''
                CREATE TABLE IF NOT EXISTS checkins
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 barcode TEXT NOT NULL,
                 checkin_date DATE NOT NULL,
                 checkin_time TIME NOT NULL,
                 created_at DATETIME DEFAULT CURRENT_TIMESTAMP)
            '''
        }
        
        for table_name, create_sql in tables.items():
            c.execute(create_sql)
            print(f"Table '{table_name}' created/verified successfully")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error initializing database: {e}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Multi-Page App")
       
        # 🔄 Dynamic window size based on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{int(screen_width * 0.9)}x{int(screen_height * 0.9)}")
        self.resizable(True, True)
        
        # Auto-refresh variables
        self.auto_refresh = True
        self.refresh_interval = 10000  # 10 seconds
        
        self._barcode_after_id = None
        
        self.configure(fg_color=COLORS["bg"])
        nav_frame = ctk.CTkFrame(self, height=72, fg_color=COLORS["surface"],
                                 corner_radius=0, border_width=0)
        nav_frame.pack(side="top", fill="x")
        nav_frame.pack_propagate(False)

        brand = ctk.CTkFrame(nav_frame, fg_color="transparent")
        brand.pack(side="left", padx=(22, 18), pady=10)
        ctk.CTkLabel(brand, text="SWEAT", font=(FONT, 20, "bold"),
                     text_color=COLORS["text"]).pack(side="left")
        ctk.CTkLabel(brand, text=" / MANAGEMENT", font=(FONT, 10, "bold"),
                     text_color=COLORS["accent"]).pack(side="left", padx=(4, 0), pady=(7, 0))

        for label_text, command in [
            ("Home", self.show_home), ("Add Person", self.show_add_person),
            ("Recharge", self.show_recharge_page), ("Search", self.on_search)
        ]:
            ctk.CTkButton(nav_frame, text=label_text, command=command,
                          fg_color="transparent", hover_color=COLORS["surface_3"],
                          text_color=COLORS["muted"], corner_radius=9,
                          height=40, font=(FONT, 12, "bold")).pack(side="left", padx=3, pady=16)

        ctk.CTkButton(nav_frame, text="EXIT", command=self.quit,
                      fg_color=COLORS["surface_2"], hover_color=COLORS["danger"],
                      text_color=COLORS["muted"], corner_radius=9, width=72,
                      height=38, font=(FONT, 11, "bold")).pack(side="right", padx=20, pady=17)

        self.page_container = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.page_container.pack(fill="both", expand=True)
        self.pages = {}
        self.show_home()
        
        # Start auto-refresh
        self.start_auto_refresh()

    def start_auto_refresh(self):
        """Start automatic refresh timer"""
        if self.auto_refresh:
            self.after(self.refresh_interval, self.auto_refresh_timer)

    def auto_refresh_timer(self):
        """Auto-refresh timer callback"""
        if self.auto_refresh:
            # Only refresh if we're on the home page
            if "home" in self.pages and self.pages["home"].winfo_ismapped():
                self.refresh_home_table()
                print("Auto-refreshed table")
            
            # Restart timer
            self.after(self.refresh_interval, self.auto_refresh_timer)

    def global_refresh(self):
        """Global refresh function"""
        if "home" in self.pages and self.pages["home"].winfo_ismapped():
            self.refresh_home_table()
        print("Manual refresh triggered")

    def clear_pages(self):
        for page in self.pages.values():
            page.pack_forget()

    def _show_dynamic_page(self, key, build_fn):
        """Show a page whose content depends on data and must be rebuilt
        every time (e.g. a specific customer's profile), instead of the
        cached, built-once pages like Home/Add Person/Search.

        `build_fn(frame)` should populate the given frame with widgets.
        """
        self.clear_pages()
        # Drop any previous instance of this dynamic page so it doesn't
        # accumulate stale widgets/data in memory.
        old_frame = self.pages.get(key)
        if old_frame is not None:
            try:
                old_frame.destroy()
            except Exception:
                pass
        frame = ctk.CTkScrollableFrame(self.page_container)
        build_fn(frame)
        self.pages[key] = frame
        frame.pack(fill="both", expand=True)

    def show_profile_page(self, customer_data, columns):
        """Show a customer's profile as an in-window page (no popup)."""
        self._show_dynamic_page(
            "profile",
            lambda frame: build_profile_page(frame, customer_data, columns, self),
        )

    def show_profile_page_by_barcode(self, barcode):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM data WHERE barcode = ?", (barcode,))
        customer_data = c.fetchone()
        c.execute("PRAGMA table_info(data)")
        columns = [info[1] for info in c.fetchall()]
        conn.close()
        if customer_data:
            self.show_profile_page(customer_data, columns)
        else:
            self.show_home()

    def show_edit_profile_page(self, customer_data, columns):
        """Show an in-window edit form for a customer, replacing the old
        edit_profile() popup window."""

        def build(frame):
            ctk.CTkButton(
                frame, text="← Back to Profile", fg_color=COLORS["surface_3"], hover_color=COLORS["accent"],
                command=lambda: self.show_profile_page(customer_data, columns)
            ).pack(anchor="w", padx=20, pady=(10, 0))

            form = ctk.CTkFrame(frame, fg_color=COLORS["surface"], corner_radius=16, border_width=1, border_color=COLORS["border"])
            form.pack(padx=20, pady=20, fill="both", expand=True)
            form.grid_columnconfigure(1, weight=1)

            entries = {}
            for i, col in enumerate(columns):
                ctk.CTkLabel(form, text=f"{col}:").grid(row=i, column=0, padx=10, pady=5, sticky="w")
                entry = _style_entry(ctk.CTkEntry(form))
                entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                entry.insert(0, str(customer_data[i]))
                entries[col] = entry

            status_label = ctk.CTkLabel(form, text="")
            status_label.grid(row=len(columns) + 2, column=0, columnspan=2, pady=5)

            def save_changes():
                updated_data = [entries[col].get() for col in columns]
                try:
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    update_query = "UPDATE data SET " + ", ".join([f"{col} = ?" for col in columns]) + " WHERE id = ?"
                    c.execute(update_query, updated_data + [customer_data[0]])
                    conn.commit()
                    conn.close()
                    self.refresh_home_table()
                    barcode_value = updated_data[columns.index("barcode")]
                    self.show_profile_page_by_barcode(barcode_value)
                except sqlite3.Error as e:
                    status_label.configure(text=f"Error saving changes: {e}", text_color="red")

            ctk.CTkButton(form, text="Save Changes", command=save_changes).grid(
                row=len(columns), column=0, columnspan=2, pady=10, sticky="ew"
            )

            def create_card_from_entries():
                try:
                    create_card(
                        first_name=entries.get("name").get(),
                        last_name=entries.get("last_name").get(),
                        email=entries.get("email").get(),
                        phone=entries.get("phone").get(),
                        member_id=entries.get("barcode").get(),
                    )
                    status_label.configure(text="Membership card created.", text_color="green")
                except Exception as e:
                    status_label.configure(text=f"Failed to create card: {e}", text_color="red")

            ctk.CTkButton(form, text="Create New Membership Card", command=create_card_from_entries).grid(
                row=len(columns) + 1, column=0, columnspan=2, pady=6, sticky="ew"
            )

        self._show_dynamic_page("edit_profile", build)

    def show_home(self):
        self.clear_pages()
        if "home" not in self.pages:
            frame = ctk.CTkFrame(self.page_container, fg_color=COLORS["bg"])
            frame.pack(fill="both", expand=True)

            hero = ctk.CTkFrame(frame, fg_color="transparent")
            hero.pack(fill="x", padx=34, pady=(30, 16))
            left = ctk.CTkFrame(hero, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(left, text="Good to see you.", font=(FONT, 28, "bold"),
                         text_color=COLORS["text"]).pack(anchor="w")
            ctk.CTkLabel(left, text="Manage members, check-ins and credits from one place.",
                         font=(FONT, 13), text_color=COLORS["muted"]).pack(anchor="w", pady=(4, 0))
            try:
                logo_image = ctk.CTkImage(light_image=Image.open("logol.png"),
                                          dark_image=Image.open("logol.png"), size=(190, 46))
                ctk.CTkLabel(hero, image=logo_image, text="").pack(side="right", padx=12)
            except Exception:
                pass

            checkin_frame = ctk.CTkFrame(frame, fg_color=COLORS["surface"], corner_radius=18,
                                         border_width=1, border_color=COLORS["border"])
            checkin_frame.pack(fill="x", padx=34, pady=(0, 18))
            head = ctk.CTkFrame(checkin_frame, fg_color="transparent")
            head.pack(fill="x", padx=24, pady=(20, 4))
            ctk.CTkLabel(head, text="QUICK CHECK-IN", font=(FONT, 11, "bold"),
                         text_color=COLORS["accent"]).pack(side="left")
            ctk.CTkLabel(head, text="Scan a member barcode to use one credit",
                         font=(FONT, 11), text_color=COLORS["muted"]).pack(side="right")

            row = ctk.CTkFrame(checkin_frame, fg_color="transparent")
            row.pack(fill="x", padx=24, pady=(8, 20))
            self.entry_barcode = _style_entry(ctk.CTkEntry(row, placeholder_text="Scan or enter barcode"))
            self.entry_barcode.pack(side="left", fill="x", expand=True)
            self.entry_barcode.bind("<Return>", self.auto_checkin)
            self.entry_barcode.bind("<KeyRelease>", self.handle_barcode_input)
            btn = _style_button(ctk.CTkButton(row, text="CHECK IN", command=self.check_in_manual), "primary")
            btn.configure(width=125)
            btn.pack(side="left", padx=(12, 0))
            self.result_label = ctk.CTkLabel(checkin_frame, text="", font=(FONT, 12, "bold"))
            self.result_label.pack(pady=(0, 15))

            table_card = ctk.CTkFrame(frame, fg_color=COLORS["surface"], corner_radius=18,
                                      border_width=1, border_color=COLORS["border"])
            table_card.pack(padx=34, pady=(0, 28), fill="both", expand=True)
            table_head = ctk.CTkFrame(table_card, fg_color="transparent")
            table_head.pack(fill="x", padx=22, pady=(18, 10))
            ctk.CTkLabel(table_head, text="MEMBERS", font=(FONT, 17, "bold"),
                         text_color=COLORS["text"]).pack(side="left")
            ctk.CTkLabel(table_head, text="Live member directory", font=(FONT, 11),
                         text_color=COLORS["muted"]).pack(side="left", padx=10)
            self.table_frame = ctk.CTkScrollableFrame(
                table_card, fg_color=COLORS["surface"],
                scrollbar_button_color=COLORS["surface_3"],
                scrollbar_button_hover_color=COLORS["border"])
            self.table_frame.pack(padx=16, pady=(0, 16), fill="both", expand=True)
            self.load_home_table()
            self.pages["home"] = frame
        self.pages["home"].pack(fill="both", expand=True)

    def load_home_table(self):
        """Load the member directory with the redesigned visual style."""
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        columns, rows = fetch_data()
        for col, col_name in enumerate(columns):
            self.table_frame.grid_columnconfigure(col, weight=1)
            ctk.CTkLabel(self.table_frame, text=str(col_name).upper(),
                         font=(FONT, 10, "bold"), text_color=COLORS["muted"],
                         fg_color=COLORS["surface_3"], corner_radius=6
                         ).grid(row=0, column=col, padx=3, pady=(3, 8), sticky="ew")
        profile_col=len(columns)
        ctk.CTkLabel(self.table_frame, text="ACTION", font=(FONT, 10, "bold"),
                     text_color=COLORS["muted"], fg_color=COLORS["surface_3"],
                     corner_radius=6, width=110).grid(row=0,column=profile_col,padx=3,pady=(3,8),sticky="ew")
        for row_idx,row_data in enumerate(rows,start=1):
            for col_idx,value in enumerate(row_data):
                ctk.CTkLabel(self.table_frame, text=str(value) if value is not None else "—",
                             font=(FONT,12), text_color=COLORS["text"],
                             fg_color=COLORS["surface_2"], corner_radius=6, anchor="w"
                             ).grid(row=row_idx,column=col_idx,padx=3,pady=2,sticky="ew")
            ctk.CTkButton(self.table_frame,text="VIEW",width=100,height=34,
                          fg_color=COLORS["surface_3"],hover_color=COLORS["accent"],
                          text_color=COLORS["text"],corner_radius=8,font=(FONT,11,"bold"),
                          command=lambda data=row_data:self.show_profile_page(data,columns)
                          ).grid(row=row_idx,column=profile_col,padx=3,pady=2,sticky="ew")

    def refresh_home_table(self, frame=None):
        """Refresh the home page table"""
        self.load_home_table()
        print("Table refreshed!")

    def auto_checkin(self, event):
        """Handle barcode scanner input and refresh table"""
        barcode = self.entry_barcode.get().strip()
        if barcode:
            result = checkin(barcode)
            self.flash_result(result, duration=1500)
            self.entry_barcode.delete(0, ctk.END)
            # Refresh table after check-in
            self.refresh_home_table()

    def handle_barcode_input(self, event):
        """Called on every key release in the barcode entry. Debounces then
        triggers the automatic check-in if the barcode looks complete.
        """
        # Cancel any pending scheduled processing
        if getattr(self, '_barcode_after_id', None):
            try:
                self.after_cancel(self._barcode_after_id)
            except Exception:
                pass

        # Schedule processing after a short delay (debounce)
        self._barcode_after_id = self.after(250, self._process_barcode_input)

    def _process_barcode_input(self):
        """Process the barcode input after debounce. If barcode seems complete
        (13+ digits) it triggers the same logic as manual check-in.
        Adjust the length check if your barcodes differ in size.
        """
        self._barcode_after_id = None
        barcode = self.entry_barcode.get().strip()
        if not barcode:
            return

        # Heuristic: auto-trigger when barcode looks like a numeric EAN-13 (13 digits)
        if barcode.isdigit() and len(barcode) >= 13:
            result = checkin(barcode)
            self.flash_result(result, duration=2000)
            self.entry_barcode.delete(0, ctk.END)
            self.refresh_home_table()

    def check_in_manual(self):
        """Manual check-in with refresh"""
        barcode = self.entry_barcode.get().strip()
        if barcode:
            result = checkin(barcode)
            self.flash_result(result, duration=2000)
            self.entry_barcode.delete(0, ctk.END)
            # Refresh table after check-in
            self.refresh_home_table()

    def flash_result(self, message: str, duration: int = 2000):
        """Show `message` inline in the result label (no popup window) and
        clear it again after `duration` ms."""
        is_error = message.lower().startswith(("error", "invalid", "no ", "not found"))
        self.result_label.configure(text=message, text_color="red" if is_error else "green")
        self.result_label.after(duration, lambda: self.result_label.configure(text=""))

    def show_add_person(self):
        self.clear_pages()
        if "add_person" not in self.pages:
            frame = ctk.CTkFrame(self.page_container, fg_color=COLORS["bg"])
            frame.pack(pady=28, padx=34, fill="both", expand=True)
            ctk.CTkLabel(frame, text="REGISTER", font=("Arial", 20, "bold")).pack(pady=20)
            label_name = ctk.CTkLabel(frame, text="Name:")
            label_name.pack(pady=10)
            entry_name = _style_entry(ctk.CTkEntry(frame, placeholder_text="Enter your name"))
            entry_name.pack(pady=10)

            labe_lastl = ctk.CTkLabel(frame, text="Last Name:")
            labe_lastl.pack(pady=10)
            entry_last_name = _style_entry(ctk.CTkEntry(frame, placeholder_text="Enter your last name"))
            entry_last_name.pack(pady=10)
            label_email = ctk.CTkLabel(frame, text="Email:")
            label_email.pack(pady=10)
            entry_email = _style_entry(ctk.CTkEntry(frame, placeholder_text="Enter your email"))
            entry_email.pack(pady=10)
            label_phone = ctk.CTkLabel(frame, text="Phone:")
            label_phone.pack(pady=10)
            entry_phone = _style_entry(ctk.CTkEntry(frame, placeholder_text="Enter your phone number"))
            entry_phone.pack(pady=10)
            address_label = ctk.CTkLabel(frame, text="Address:")
            address_label.pack(pady=10)
            entry_address = _style_entry(ctk.CTkEntry(frame, placeholder_text="Enter your address"))
            entry_address.pack(pady=10)
            labe_practicetype = ctk.CTkLabel(frame, text="Practice Type:")
            labe_practicetype.pack(pady=10)
            entry_practice_type = ctk.CTkComboBox(frame, values=["FLEX 2X", "STANDARD 4X 50€", "STANDARD 8X 80€", "STANDARD 12X 100€", "UPGRADE 4X 50€", "UPGRADE 8X 80€"])
            entry_practice_type.pack(pady=10)
            
            result_label = ctk.CTkLabel(frame, text="")
            result_label.pack(pady=10)
            
            def on_add():
                def _compute_ean13_check_digit(num12: str) -> str:
                    """Compute EAN-13 check digit for a 12-digit numeric string."""
                    if len(num12) != 12 or not num12.isdigit():
                        raise ValueError("EAN-13 base must be 12 numeric digits")
                    digits = [int(d) for d in num12]
                    sum_odd = sum(digits[i] for i in range(0, 12, 2))
                    sum_even = sum(digits[i] for i in range(1, 12, 2))
                    total = sum_odd + sum_even * 3
                    check = (10 - (total % 10)) % 10
                    return str(check)

                def generate_random_ean13() -> str:
                    """Generate a unique valid EAN-13 barcode (13 digits) and ensure uniqueness in DB."""
                    conn = sqlite3.connect('sweat_new.db')
                    c = conn.cursor()
                    try:
                        while True:
                            base12 = str(random.randint(10**11, 10**12 - 1))
                            check = _compute_ean13_check_digit(base12)
                            candidate = base12 + check
                            c.execute("SELECT 1 FROM data WHERE barcode = ?", (candidate,))
                            if c.fetchone() is None:
                                return candidate
                    finally:
                        conn.close()
        
                # Get credits based on practice type
                practice_type = entry_practice_type.get()
                if practice_type == "FLEX 2X":
                    credits = 2
                elif practice_type == "STANDARD 4X 50":
                    credits = 4
                elif practice_type == "STANDARD 8X 80":
                    credits = 8
                elif practice_type == "STANDARD 12X 100$":
                    credits = 12
                elif practice_type == "UPGRADE 4X 50$":
                    credits = 16
                elif practice_type == "UPGRADE 8X 80$":
                    credits = 20

                else:
                    credits = 0

                barcode = generate_random_ean13()
                conn = sqlite3.connect('sweat_new.db')
                c = conn.cursor()
                c.execute('''INSERT INTO practicecredits (practice_type, barcode, credits) VALUES (?, ?, ?)''', (
                    practice_type,
                    barcode,
                    credits
                ))
                c.execute('''INSERT INTO datetime (date, time, barcode) VALUES (?, ?, ?)''', (
                    datetime.datetime.now().strftime("%Y-%m-%d"),
                    datetime.datetime.now().strftime("%H:%M:%S"),
                    barcode
                ))
                c.execute("INSERT INTO data (name, last_name, email, phone, address, barcode) VALUES (?, ?, ?, ?, ?, ?)", (
                    entry_name.get(),
                    entry_last_name.get(),
                    entry_email.get(),
                    entry_phone.get(),
                    entry_address.get(),
                    barcode
                ))
                c.execute('''INSERT INTO checkinHistory (barcode, datetime) VALUES (?, ?)''', (
                    barcode,
                    datetime.datetime.now().date() 
                ))
                conn.commit()
                conn.close()
                
               
                create_card(
                    entry_name.get(),
                    entry_last_name.get(),
                    entry_email.get(),
                    entry_phone.get(),
                    barcode,
                )
                result_label.configure(text="Person added!", text_color="green")
                entry_name.delete(0, ctk.END)
                entry_last_name.delete(0, ctk.END)
                entry_email.delete(0, ctk.END)
                entry_phone.delete(0, ctk.END)
                entry_address.delete(0, ctk.END)
                
                # Refresh home table after adding person
                self.refresh_home_table()
                
            button_add = ctk.CTkButton(frame, text="Add Person", command=on_add)
            button_add.pack(pady=20)
            self.pages["add_person"] = frame
        self.pages["add_person"].pack(fill="both", expand=True)

    def show_recharge_page(self):
        self.clear_pages()
        if "recharge" not in self.pages:
            frame = ctk.CTkFrame(self.page_container, fg_color=COLORS["bg"])
            ctk.CTkLabel(frame, text="Recharge Page", font=("Arial", 20, "bold")).pack(pady=20)
            label_barcode = ctk.CTkLabel(frame, text="Enter Barcode:")
            label_barcode.pack(pady=10)
            entry_barcode = _style_entry(ctk.CTkEntry(frame))
            entry_barcode.pack(pady=10)
            label_credits = ctk.CTkLabel(frame, text="Enter Credits to Recharge:")
            label_credits.pack(pady=10)
            entry_credits = _style_entry(ctk.CTkEntry(frame))
            entry_credits.pack(pady=10)
            label_instant_recharge = ctk.CTkLabel(frame, text="Instant Recharge:")
            label_instant_recharge.pack(pady=10)
            entry_practice_type = ctk.CTkComboBox(frame, values=["FLEX 2X", "STANDARD 4X 50€", "STANDARD 8X 80€", "STANDARD 12X 100€" , "UPGRADE 4X 50€", "UPGRADE 8X 80€"])
            entry_practice_type.pack(pady=10)
            


            result_label = ctk.CTkLabel(frame, text="")
            result_label.pack(pady=10)
            def on_insntant_recharge() :
              barcode = entry_barcode.get()
              practice_type = entry_practice_type.get()
              if practice_type == "FLEX 2X":
                        credits = 2
              elif practice_type == "STANDARD 4X 50€":
                        credits = 4
              elif practice_type == "STANDARD 8X 80€":
                        credits = 8
              elif practice_type == "STANDARD 12X 100€":
                        credits = 12
                                            
              elif practice_type == "UPGRADE 4X 50€":
                        credits = 4
              elif practice_type == "UPGRADE 8X 80€":
                        credits = 8
              else:
                 credits = 0
                 result_label.configure(text="Please select a valid practice type", text_color="red")
                 return
              if barcode and credits:
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    c.execute("UPDATE PracticeCredits SET credits = credits + ? WHERE barcode = ? AND practice_type  = ?", (credits, barcode , practice_type))
                    conn.commit()
                    conn.close()
                    result_label.configure(text=f"Recharged {credits} credits for {barcode}.", text_color="green")
              else:
                    result_label.configure(text="Please enter valid barcode and credits.", text_color="red")
              
              
            def on_recharge():
                datetime_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


                    
                barcode = entry_barcode.get()
                credits = entry_credits.get()
                if barcode and credits.isdigit():
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    c.execute("UPDATE PracticeCredits SET credits = credits + ? WHERE barcode = ?", (int(credits), barcode))
                    c.execute("UPDATE datetime SET date = ?, time = ? WHERE barcode = ?", (datetime_str.split()[0], datetime_str.split()[1], barcode))

                    conn.commit()
                    conn.close()
                    result_label.configure(text=f"Recharged {credits} credits for {barcode}.", text_color="green")
                else:
                    result_label.configure(text="Please enter valid barcode and credits.", text_color="red")

            button_recharge = ctk.CTkButton(frame, text="RECHARGE", command=on_recharge ,height = 40 , width = 200 )
            button_recharge.pack(pady=20)
            button_instant_recharge = ctk.CTkButton(frame , text = "INSTANT RECHARGE" , command = on_insntant_recharge , height = 40 , width = 200 )
            button_instant_recharge.pack(pady=20)
            

            self.pages["recharge"] = frame
        self.pages["recharge"].pack(fill="both", expand=True)

    def on_search(self):
            self.clear_pages()
            if "search" not in self.pages:
                frame = ctk.CTkFrame(self.page_container, fg_color=COLORS["bg"])
                frame.pack(pady=28, padx=34, fill="both", expand=True)
                
                # Search UI elements
                label = ctk.CTkLabel(frame, text="Search Person", font=("Arial", 20, "bold"))
                label.pack(pady=20)
                
                entry_search = _style_entry(ctk.CTkEntry(frame, placeholder_text="Enter name or barcode"))
                entry_search.pack(pady=10)
                
                result_label = ctk.CTkLabel(frame, text="")
                result_label.pack(pady=10)
                
                # Results frame
                frame_search = ctk.CTkScrollableFrame(frame)
                frame_search.pack(pady=20, padx=20, fill="both", expand=True)
                
                def perform_search():
                    # Get search query
                    query = entry_search.get().strip()
                    
                    if not query:
                        result_label.configure(text="Please enter a search term", text_color="red")
                        return
                    
                    # Clear previous results
                    for widget in frame_search.winfo_children():
                        widget.destroy()
                    
                    # Database search
                    try:
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        c.execute('''SELECT * FROM data WHERE name LIKE ? OR barcode LIKE ?''', 
                                (f"%{query}%", f"%{query}%"))
                        results = c.fetchall()
                        
                        # Get column names
                        c.execute("PRAGMA table_info(data)")
                        columns = [col[1] for col in c.fetchall()]
                        conn.close()
                        
                        # Display results
                        if results:
                            result_label.configure(text=f"Found {len(results)} result(s)", text_color="green")
                            
                            # Create headers
                            for col_idx, col_name in enumerate(columns):
                                header = ctk.CTkLabel(frame_search, text=col_name, font=("Arial", 12, "bold"))
                                header.grid(row=0, column=col_idx, padx=5, pady=2, sticky="w")
                            
                            # Add profile header
                            profile_header = ctk.CTkLabel(frame_search, text="Profile", font=("Arial", 12, "bold"))
                            profile_header.grid(row=0, column=len(columns), padx=5, pady=2, sticky="w")
                            
                            # Display each result
                            for row_idx, result in enumerate(results, start=1):
                                for col_idx, value in enumerate(result):
                                    cell_label = ctk.CTkLabel(frame_search, text=str(value), font=("Arial", 11))
                                    cell_label.grid(row=row_idx, column=col_idx, padx=5, pady=2, sticky="w")
                                
                                # Add view profile button
                                profile_btn = ctk.CTkButton(
                                    frame_search,
                                    text="View Profile",
                                    fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
                                    command=lambda data=result: self.show_profile_page(data, columns)
                                )
                                profile_btn.grid(row=row_idx, column=len(columns), padx=5, pady=2)
                                
                        else:
                            result_label.configure(text="No results found", text_color="red")
                            no_results = ctk.CTkLabel(frame_search, text="No matching records found.", font=("Arial", 14, "italic"))
                            no_results.pack(pady=20)
                            
                    except sqlite3.Error as e:
                        result_label.configure(text=f"Database error: {e}", text_color="red")
                
                search_button = ctk.CTkButton(frame, text="Search", command=perform_search)
                search_button.pack(pady=10)
                
                self.pages["search"] = frame
            
            self.pages["search"].pack(fill="both", expand=True)

        
        



if __name__ == "__main__":
    app = App()
    app.mainloop()