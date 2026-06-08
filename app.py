from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_file,
    session,
    url_for
)

import psycopg2
import psycopg2.extras
import pandas as pd
import qrcode
import io
import os

from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = "apollo_secret_key_2026"

# =====================================================
# IST TIMEZONE
# =====================================================

IST = pytz.timezone("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)

# =====================================================
# STAFF MASTER LIST
# =====================================================

staff_list = [
    "Rajesh Kumar (Branch Manager)",
    "Pandi Selvi (SCO)",
    "Manikandan (Marketing Manager)",
    "Fredrick (Marketing & Software Trainer)",
    "Jaswin Singh (Software Trainer)",
    "Pradeepa Dharshini (Accounts Trainer)",
    "Manimegalai Lakshmi (Multimedia & Accounts Trainer)",
    "Sinisha (Software Trainer)",
    "Jeyamena (Software Trainer)",
    "Swathi (Telecaller)",
    "Shailaja (Telecaller)",
    "Nagalakshmi (Telecaller)",
    "Varshana (Telecaller)"
]

# =====================================================
# DATABASE CONNECTION
# =====================================================

def get_conn():
    database_url = os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    return conn

# =====================================================
# CREATE TABLE
# =====================================================

def create_table():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            name TEXT,
            date TEXT,
            check_in TEXT,
            check_out TEXT,
            attendance_status TEXT,
            checkout_status TEXT,
            permission_time TEXT,
            reason TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

create_table()

# =====================================================
# AUTO EXPIRE PENDING CHECKOUTS AFTER 12 HOURS
# =====================================================

def auto_expire_checkouts():
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, date, check_in FROM attendance
            WHERE checkout_status = 'Pending Checkout'
        """)
        rows = cursor.fetchall()
        now = now_ist()
        for row in rows:
            id_, date_, check_in_ = row
            if check_in_ and check_in_ != "-":
                try:
                    check_in_dt = datetime.strptime(
                        f"{date_} {check_in_}", "%d-%m-%Y %I:%M %p"
                    )
                    check_in_dt = IST.localize(check_in_dt)
                    if (now - check_in_dt).total_seconds() > 12 * 3600:
                        cursor.execute("""
                            UPDATE attendance
                            SET checkout_status = '-'
                            WHERE id = %s
                        """, (id_,))
                except:
                    pass
        conn.commit()
        cursor.close()
        conn.close()
    except:
        pass

# =====================================================
# LOGIN
# =====================================================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@app.route("/manager-login", methods=["GET", "POST"])
def manager_login():
    error = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect("/dashboard")
        else:
            error = "Invalid Username or Password"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/manager-login")

# =====================================================
# QR CODE — STAFF ATTENDANCE
# =====================================================

@app.route("/qr/attendance")
def qr_attendance():
    base_url = request.host_url.rstrip("/")
    attendance_url = f"{base_url}/"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )
    qr.add_data(attendance_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a237e", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# =====================================================
# QR CODE — MANAGER DASHBOARD
# =====================================================

@app.route("/qr/dashboard")
def qr_dashboard():
    base_url = request.host_url.rstrip("/")
    dashboard_url = f"{base_url}/manager-login"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )
    qr.add_data(dashboard_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#b71c1c", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# =====================================================
# QR DISPLAY PAGE
# =====================================================

@app.route("/qr-display")
def qr_display():
    return render_template("qr_display.html")

# =====================================================
# HOME PAGE / ATTENDANCE ENTRY
# =====================================================

@app.route("/", methods=["GET", "POST"])
def index():
    success = request.args.get("success")

    if request.method == "POST":
        name = request.form["name"]
        status = request.form["status"]
        permission_time = request.form.get("permission_time", "-")
        reason = request.form.get("reason", "-")

        current_date = now_ist().strftime("%d-%m-%Y")
        current_time = now_ist().strftime("%I:%M %p")

        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM attendance
            WHERE name=%s AND date=%s
        """, (name, current_date))
        existing = cursor.fetchone()

        # CHECK IN
        if status == "Check In":
            if not existing:
                cursor.execute("""
                    INSERT INTO attendance
                    (name, date, check_in, check_out, attendance_status, checkout_status, permission_time, reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    name, current_date, current_time,
                    "-", "Present", "Pending Checkout", "-", "-"
                ))

        # CHECK OUT
        elif status == "Check Out":
            if existing:
                cursor.execute("""
                    UPDATE attendance
                    SET check_out=%s,
                        attendance_status='Present',
                        checkout_status='Checked Out'
                    WHERE name=%s AND date=%s
                """, (current_time, name, current_date))
            else:
                cursor.execute("""
                    INSERT INTO attendance
                    (name, date, check_in, check_out, attendance_status, checkout_status, permission_time, reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    name, current_date, "-",
                    current_time, "Present", "Checked Out", "-", "-"
                ))

        # HALF DAY
        elif status == "Half Day":
            if not existing:
                cursor.execute("""
                    INSERT INTO attendance
                    (name, date, check_in, check_out, attendance_status, checkout_status, permission_time, reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    name, current_date, current_time,
                    "-", "Half Day", "-", "-", "-"
                ))

        # PERMISSION
        elif status == "Permission":
            if not existing:
                cursor.execute("""
                    INSERT INTO attendance
                    (name, date, check_in, check_out, attendance_status, checkout_status, permission_time, reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    name, current_date, "-",
                    "-", "Permission", "-", permission_time, reason
                ))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/?success=1")

    return render_template("index.html", staff_list=staff_list, success=success)

# =====================================================
# DELETE RECORD
# =====================================================

@app.route("/delete/<int:id>")
def delete_record(id):
    if not session.get("logged_in"):
        return redirect("/manager-login")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/dashboard")

# =====================================================
# DASHBOARD
# =====================================================

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/manager-login")

    auto_expire_checkouts()

    conn = get_conn()
    cursor = conn.cursor()

    current_month = now_ist().strftime("%B")
    current_year = now_ist().strftime("%Y")
    current_date = now_ist().strftime("%d-%m-%Y")

    selected_month = request.args.get("month", current_month)
    selected_date = request.args.get("date", "")

    cursor.execute("SELECT * FROM attendance ORDER BY id DESC")
    db_records = cursor.fetchall()

    records = []
    available_dates = []

    for row in db_records:
        try:
            row_date = row[2]
            row_month = datetime.strptime(row_date, "%d-%m-%Y").strftime("%B")
            if row_month == selected_month:
                if row_date not in available_dates:
                    available_dates.append(row_date)
                if selected_date == "" or row_date == selected_date:
                    records.append(row)
        except:
            pass

    # COUNTS
    total_staff = len(staff_list)
    present_count = 0
    absent_count = 0
    permission_count = 0
    halfday_count = 0
    pending_count = 0
    checkedout_count = 0

    today_staff = {}
    for row in records:
        today_staff[row[1]] = row

    for staff in staff_list:
        if staff not in today_staff:
            absent_count += 1
        else:
            status = today_staff[staff][5]
            checkout = today_staff[staff][6]
            if status == "Present" and checkout == "Pending Checkout":
                present_count += 1
                pending_count += 1
            elif status == "Present" and checkout == "Checked Out":
                present_count += 1
                checkedout_count += 1
            elif status == "Permission":
                permission_count += 1
            elif status == "Half Day":
                halfday_count += 1

    months = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ]

    current_index = months.index(current_month)
    all_months = []
    for i, month in enumerate(months):
        all_months.append({
            "name": month,
            "enabled": i <= current_index
        })

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        records=records,
        total_staff=total_staff,
        present_count=present_count,
        absent_count=absent_count,
        permission_count=permission_count,
        halfday_count=halfday_count,
        pending_count=pending_count,
        checkedout_count=checkedout_count,
        current_date=current_date,
        all_months=all_months,
        selected_month=selected_month,
        selected_date=selected_date,
        available_dates=sorted(available_dates, reverse=True),
        current_year=current_year
    )

# =====================================================
# EXCEL EXPORT
# =====================================================

@app.route("/export")
def export_excel():
    if not session.get("logged_in"):
        return redirect("/manager-login")

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, date, check_in, check_out,
               attendance_status, checkout_status,
               permission_time, reason
        FROM attendance
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    df = pd.DataFrame(rows, columns=[
        "Name", "Date", "Check In", "Check Out",
        "Attendance Status", "Checkout Status",
        "Permission Time", "Reason"
    ])

    file_name = f"{now_ist().strftime('%B')}_Attendance_Report.xlsx"
    df.to_excel(file_name, index=False)

    return send_file(file_name, as_attachment=True)

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
