from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_file,
    session
)

import sqlite3
import pandas as pd

from datetime import datetime

app = Flask(__name__)

app.secret_key = "apollo_secret_key_2026"

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
# DATABASE
# =====================================================

def create_table():

    conn = sqlite3.connect("attendance.db")

    cursor = conn.cursor()

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS attendance(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT,

        date TEXT,

        check_in TEXT,

        check_out TEXT,

        attendance_status TEXT,

        permission_time TEXT,

        reason TEXT

    )

    """)

    conn.commit()
    conn.close()

create_table()

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

        if (
            username == ADMIN_USERNAME
            and
            password == ADMIN_PASSWORD
        ):

            session["logged_in"] = True

            return redirect("/dashboard")

        else:

            error = "Invalid Username or Password"

    return render_template(
        "login.html",
        error=error
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/manager-login")

# =====================================================
# HOME PAGE / ATTENDANCE ENTRY
# =====================================================

@app.route("/", methods=["GET", "POST"])
def index():

    success = request.args.get("success")

    if request.method == "POST":

        name = request.form["name"]

        status = request.form["status"]

        permission_time = request.form.get(
            "permission_time",
            "-"
        )

        reason = request.form.get(
            "reason",
            "-"
        )

        current_date = datetime.now().strftime(
            "%d-%m-%Y"
        )

        current_time = datetime.now().strftime(
            "%I:%M %p"
        )

        conn = sqlite3.connect("attendance.db")

        cursor = conn.cursor()

        cursor.execute("""

        SELECT *

        FROM attendance

        WHERE name=?
        AND date=?

        """, (

            name,
            current_date

        ))

        existing = cursor.fetchone()

        # =================================
        # CHECK IN
        # =================================

        if status == "Check In":

            if not existing:

                cursor.execute("""

                INSERT INTO attendance(

                    name,
                    date,
                    check_in,
                    check_out,
                    attendance_status,
                    permission_time,
                    reason

                )

                VALUES (?, ?, ?, ?, ?, ?, ?)

                """, (

                    name,
                    current_date,
                    current_time,
                    "-",
                    "Pending Checkout",
                    "-",
                    "-"

                ))

        # =================================
        # CHECK OUT
        # =================================

        elif status == "Check Out":

            if existing:

                cursor.execute("""

                UPDATE attendance

                SET

                check_out=?,
                attendance_status='Present'

                WHERE

                name=?
                AND date=?

                """, (

                    current_time,
                    name,
                    current_date

                ))

            else:

                cursor.execute("""

                INSERT INTO attendance(

                    name,
                    date,
                    check_in,
                    check_out,
                    attendance_status,
                    permission_time,
                    reason

                )

                VALUES (?, ?, ?, ?, ?, ?, ?)

                """, (

                    name,
                    current_date,
                    "-",
                    current_time,
                    "Present",
                    "-",
                    "-"

                ))
                # =================================
        # HALF DAY
        # =================================

        elif status == "Half Day":

            if not existing:

                cursor.execute("""

                INSERT INTO attendance(

                    name,
                    date,
                    check_in,
                    check_out,
                    attendance_status,
                    permission_time,
                    reason

                )

                VALUES (?, ?, ?, ?, ?, ?, ?)

                """, (

                    name,
                    current_date,
                    current_time,
                    "-",
                    "Half Day",
                    "-",
                    "-"

                ))

        # =================================
        # PERMISSION
        # =================================

        elif status == "Permission":

            if not existing:

                cursor.execute("""

                INSERT INTO attendance(

                    name,
                    date,
                    check_in,
                    check_out,
                    attendance_status,
                    permission_time,
                    reason

                )

                VALUES (?, ?, ?, ?, ?, ?, ?)

                """, (

                    name,
                    current_date,
                    "-",
                    "-",
                    "Permission",
                    permission_time,
                    reason

                ))

        conn.commit()
        conn.close()

        return redirect("/?success=1")

    return render_template(

        "index.html",

        staff_list=staff_list,

        success=success

    )

# =====================================================
# DELETE RECORD
# =====================================================

@app.route("/delete/<int:id>")
def delete_record(id):

    if not session.get("logged_in"):

        return redirect("/manager-login")

    conn = sqlite3.connect("attendance.db")

    cursor = conn.cursor()

    cursor.execute(

        "DELETE FROM attendance WHERE id=?",

        (id,)

    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# =====================================================
# DASHBOARD
# =====================================================

@app.route("/dashboard")
def dashboard():

    if not session.get("logged_in"):

        return redirect("/manager-login")

    conn = sqlite3.connect("attendance.db")

    cursor = conn.cursor()

    current_month = datetime.now().strftime("%B")

    current_year = datetime.now().strftime("%Y")

    selected_month = request.args.get(
    "month",
    current_month)
    
    selected_date = request.args.get(
    "date",
    "")

    cursor.execute("""

    SELECT *

    FROM attendance

    ORDER BY id DESC

    """)

    db_records = cursor.fetchall()

    records = []
    available_dates = []
    for row in db_records:
        try:
            row_date = row[2]
            row_month = datetime.strptime(row_date,"%d-%m-%Y").strftime("%B")
            if row_month == selected_month:
                if row_date not in available_dates:
                    available_dates.append(row_date)
                if (selected_date == "" or row_date == selected_date):
                    records.append(row)
        except:
            pass

    # =====================================
    # DASHBOARD COUNTS
    # =====================================

    total_staff = len(staff_list)

    present_count = 0
    absent_count = 0
    permission_count = 0
    halfday_count = 0
    pending_count = 0

    today_staff = {}

    for row in records:

        today_staff[row[1]] = row

    for staff in staff_list:

        if staff not in today_staff:

            absent_count += 1

        else:

            status = today_staff[staff][5]

            if status == "Present":

                present_count += 1

            elif status == "Permission":

                permission_count += 1

            elif status == "Half Day":

                halfday_count += 1

            elif status == "Pending Checkout":

                pending_count += 1

    months = [

        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December"

    ]

    current_index = months.index(current_month)

    all_months = []

    for i, month in enumerate(months):

        all_months.append({

            "name": month,

            "enabled": i <= current_index

        })

    current_date = datetime.now().strftime(
        "%d-%m-%Y"
    )

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

        current_date=current_date,

        all_months=all_months,

        selected_month=selected_month,

selected_date=selected_date,

available_dates=sorted(
    available_dates,
    reverse=True
),

current_year=current_year

    )

# =====================================================
# EXCEL EXPORT
# =====================================================

@app.route("/export")
def export_excel():

    if not session.get("logged_in"):

        return redirect("/manager-login")

    conn = sqlite3.connect("attendance.db")

    query = """

    SELECT

    name,
    date,
    check_in,
    check_out,
    attendance_status,
    permission_time,
    reason

    FROM attendance

    """

    df = pd.read_sql_query(
        query,
        conn
    )

    conn.close()

    current_month = datetime.now().strftime(
        "%B"
    )

    file_name = (

        f"{current_month}_Attendance_Report.xlsx"

    )

    df.to_excel(
        file_name,
        index=False
    )

    return send_file(

        file_name,

        as_attachment=True

    )

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    app.run(host='0.0.0.0', port=10000)