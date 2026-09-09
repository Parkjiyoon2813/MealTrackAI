from datetime import date, datetime
import calendar


DATE_FORMAT = "%d-%m-%Y"


def get_today_string(current_date=None):
    current_date = current_date or date.today()
    return current_date.strftime(DATE_FORMAT)


def parse_date_string(date_str):
    if not date_str:
        return date.today()
    if isinstance(date_str, date):
        return date_str
    if isinstance(date_str, datetime):
        return date_str.date()
    return datetime.strptime(date_str, DATE_FORMAT).date()


def is_sunday(current_date=None):
    if current_date is None:
        target_date = date.today()
    elif isinstance(current_date, str):
        target_date = parse_date_string(current_date)
    elif isinstance(current_date, datetime):
        target_date = current_date.date()
    else:
        target_date = current_date
    return target_date.weekday() == 6


def get_greeting(current_time=None):
    current_time = current_time or datetime.now()
    current_hour = current_time.hour

    if current_hour < 12:
        return "Good Morning"
    if current_hour < 17:
        return "Good Afternoon"
    return "Good Evening"


def get_display_date(current_date=None):
    if current_date is None:
        target_date = date.today()
    elif isinstance(current_date, str):
        target_date = parse_date_string(current_date)
    elif isinstance(current_date, datetime):
        target_date = current_date.date()
    else:
        target_date = current_date
    return target_date.strftime("%A, %d %B %Y")


def get_completed_meals(meal_states):
    return sum(meal_states.values())


def parse_outside_dinner_amount(value):
    if not value:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def calculate_bill(meal_states, meal_prices, outside_dinner_amount=0, current_date=None):
    total_bill = 0

    for meal_name, price in meal_prices.items():
        if meal_states.get(meal_name) != 1:
            continue

        if meal_name == "Dinner" and is_sunday(current_date):
            total_bill += outside_dinner_amount
        else:
            total_bill += price

    return total_bill


def save_date_meal_record(
    cursor,
    connection,
    date_str,
    meal_states,
    bill,
    outside_dinner=0,
):
    if isinstance(date_str, (date, datetime)):
        date_str = date_str.strftime(DATE_FORMAT)

    cursor.execute(
        "SELECT date FROM meals WHERE date=?",
        (date_str,),
    )
    record = cursor.fetchone()

    breakfast = meal_states.get("Breakfast", 0)
    lunch = meal_states.get("Lunch", 0)
    dinner = meal_states.get("Dinner", 0)

    if record:
        cursor.execute(
            """
            UPDATE meals
            SET breakfast=?,
                lunch=?,
                dinner=?,
                outside_dinner=?,
                bill=?
            WHERE date=?
            """,
            (breakfast, lunch, dinner, outside_dinner, bill, date_str),
        )
    else:
        cursor.execute(
            """
            INSERT INTO meals
            (date, breakfast, lunch, dinner, outside_dinner, bill)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (date_str, breakfast, lunch, dinner, outside_dinner, bill),
        )

    connection.commit()


def save_meal_record(
    cursor,
    connection,
    meal_states,
    bill,
    outside_dinner=0,
    current_date=None,
):
    today = get_today_string(current_date)
    save_date_meal_record(
        cursor,
        connection,
        today,
        meal_states,
        bill,
        outside_dinner,
    )


def fetch_record_by_date(cursor, date_str):
    if isinstance(date_str, (date, datetime)):
        date_str = date_str.strftime(DATE_FORMAT)

    cursor.execute(
        """
        SELECT breakfast, lunch, dinner, outside_dinner, bill
        FROM meals
        WHERE date=?
        """,
        (date_str,),
    )

    return cursor.fetchone()


def fetch_today_record(cursor, current_date=None):
    today = get_today_string(current_date)
    return fetch_record_by_date(cursor, today)


def fetch_history_records(cursor):
    cursor.execute(
        """
        SELECT date, breakfast, lunch, dinner, outside_dinner, bill
        FROM meals
        ORDER BY substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2) DESC
        """
    )
    return cursor.fetchall()


def fetch_statistics(cursor):
    cursor.execute(
        """
        SELECT breakfast, lunch, dinner, bill
        FROM meals
        """
    )
    return cursor.fetchall()


def fetch_monthly_summary(cursor, meal_count, current_date=None):
    current_date = current_date or date.today()
    if isinstance(current_date, str):
        current_date = parse_date_string(current_date)
    current_month = current_date.strftime("%m")
    current_year = current_date.strftime("%Y")

    cursor.execute(
        """
        SELECT date, breakfast, lunch, dinner, bill
        FROM meals
        WHERE substr(date, 4, 2) = ?
        AND substr(date, 7, 4) = ?
        ORDER BY substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2) ASC
        """,
        (current_month, current_year),
    )
    records = cursor.fetchall()

    total_spent = sum(record[4] for record in records)
    total_meals = sum(record[1] + record[2] + record[3] for record in records)
    days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
    total_possible_meals = days_in_month * meal_count
    days_recorded = len(records)
    average_spending = total_spent / days_recorded if days_recorded > 0 else 0

    if records:
        highest_day = max(records, key=lambda record: record[4])
        lowest_day = min(records, key=lambda record: record[4])
    else:
        highest_day = None
        lowest_day = None

    return {
        "month_label": current_date.strftime("%B %Y"),
        "records": records,
        "total_spent": total_spent,
        "total_meals": total_meals,
        "total_possible_meals": total_possible_meals,
        "days_recorded": days_recorded,
        "average_spending": average_spending,
        "highest_day": highest_day,
        "lowest_day": lowest_day,
    }


def fetch_dashboard_totals(cursor, current_date=None):
    current_date = current_date or date.today()
    current_month = current_date.strftime("%m")
    current_year = current_date.strftime("%Y")

    cursor.execute(
        """
        SELECT bill
        FROM meals
        WHERE substr(date, 4, 2) = ?
        AND substr(date, 7, 4) = ?
        """,
        (current_month, current_year),
    )
    monthly_records = cursor.fetchall()

    total_month_spent = sum(record[0] for record in monthly_records)
    days_recorded = len(monthly_records)
    average_daily = total_month_spent / days_recorded if days_recorded > 0 else 0

    return total_month_spent, average_daily


def get_calendar_weeks(current_date=None):
    current_date = current_date or date.today()
    return calendar.monthcalendar(current_date.year, current_date.month)


def get_recorded_days(records):
    recorded_days = set()

    for record in records:
        day_value = record[0][:2]
        if day_value.isdigit():
            recorded_days.add(int(day_value))

    return recorded_days


def get_recent_spending_records(records, limit=6):
    recent_records = records[-limit:]
    return [
        {
            "date": record[0],
            "label": record[0][:2].lstrip("0") or "0",
            "bill": record[4],
        }
        for record in recent_records
    ]


def get_quick_insights(summary):
    insights = []

    if summary["days_recorded"] == 0:
        return [
            "Save today's meals to start building your monthly insights.",
            "A full week of records will make trends much more useful.",
            "Keep Sunday dinner tracked separately when it is an outside meal.",
        ]

    average_spending = summary["average_spending"]
    total_meals = summary["total_meals"]
    days_recorded = summary["days_recorded"]
    average_meals = total_meals / days_recorded if days_recorded else 0

    if average_meals >= 2.5:
        insights.append("You are keeping up with most of your meals this month.")
    elif average_meals >= 1.5:
        insights.append("Your meal tracking is steady, with room to get more consistent.")
    else:
        insights.append("Meal tracking is still sparse this month, so every saved day helps.")

    if average_spending <= 60:
        insights.append("Your average daily spending is currently on the lower side.")
    elif average_spending <= 90:
        insights.append("Your average daily spending looks balanced for the month so far.")
    else:
        insights.append("Your monthly average is trending higher, so dinner and outside meals matter most.")

    if summary["highest_day"] and summary["lowest_day"]:
        insights.append(
            f"Your spending range runs from ₹{summary['lowest_day'][4]} to ₹{summary['highest_day'][4]}."
        )

    return insights[:3]


def get_motivation_message(summary):
    if summary["days_recorded"] == 0:
        return "A small check-in today turns this dashboard into a useful habit."

    if summary["total_meals"] >= summary["days_recorded"] * 2:
        return "Your consistency is building momentum. Keep stacking clean, simple days."

    if summary["average_spending"] <= 80:
        return "You are doing well balancing meal tracking with spending control."

    return "Stay with it. Even one well-tracked day makes the monthly picture clearer."


def get_calendar_month(target_year, target_month):
    return calendar.monthcalendar(target_year, target_month)


def fetch_meal_type_distribution(cursor, current_date=None, meal_prices=None):
    current_date = current_date or date.today()
    if isinstance(current_date, str):
        current_date = parse_date_string(current_date)
    current_month = current_date.strftime("%m")
    current_year = current_date.strftime("%Y")

    cursor.execute(
        """
        SELECT date, breakfast, lunch, dinner, outside_dinner, bill
        FROM meals
        WHERE substr(date, 4, 2) = ?
        AND substr(date, 7, 4) = ?
        """,
        (current_month, current_year),
    )
    records = cursor.fetchall()

    bf_price = 30
    lu_price = 50
    dn_price = 30
    if meal_prices:
        bf_price = meal_prices.get("Breakfast", 30)
        lu_price = meal_prices.get("Lunch", 50)
        dn_price = meal_prices.get("Dinner", 30)

    breakfast_count = sum(r[1] for r in records)
    lunch_count = sum(r[2] for r in records)
    dinner_count = sum(r[3] for r in records)

    breakfast_spend = breakfast_count * bf_price
    lunch_spend = lunch_count * lu_price
    dinner_spend = 0

    for r in records:
        date_str, bf, lu, dn, out_dn, bill = r
        if dn == 1:
            if is_sunday(date_str) and out_dn > 0:
                dinner_spend += out_dn
            else:
                dinner_spend += dn_price

    total_spend = breakfast_spend + lunch_spend + dinner_spend

    return {
        "breakfast_count": breakfast_count,
        "lunch_count": lunch_count,
        "dinner_count": dinner_count,
        "breakfast_spend": breakfast_spend,
        "lunch_spend": lunch_spend,
        "dinner_spend": dinner_spend,
        "total_spend": total_spend,
        "total_meals": breakfast_count + lunch_count + dinner_count,
        "days_count": len(records),
    }


DEFAULT_NOTIFICATION_SETTINGS = {
    "notifications_enabled": "1",
    "breakfast_time": "10:00",
    "lunch_time": "14:30",
    "dinner_time": "22:00",
    "inactivity_check": "1",
    "inactivity_time": "21:30",
}


def send_system_notification(title, message):
    import subprocess
    import threading

    def _send():
        safe_title = title.replace("'", "''").replace('"', '`"')
        safe_message = message.replace("'", "''").replace('"', '`"')
        ps_cmd = f"""
        [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
        $objNotifyIcon = New-Object System.Windows.Forms.NotifyIcon
        $objNotifyIcon.Icon = [System.Drawing.SystemIcons]::Information
        $objNotifyIcon.BalloonTipIcon = "Info"
        $objNotifyIcon.BalloonTipTitle = "{safe_title}"
        $objNotifyIcon.BalloonTipText = "{safe_message}"
        $objNotifyIcon.Visible = $True
        $objNotifyIcon.ShowBalloonTip(5000)
        Start-Sleep -Seconds 6
        $objNotifyIcon.Dispose()
        """
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                capture_output=True,
                timeout=10,
            )
        except Exception:
            pass

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


def check_pending_reminders(cursor, current_time=None, sent_keys_today=None, settings=None):
    from database import get_setting

    if sent_keys_today is None:
        sent_keys_today = set()

    # Load notification settings
    if settings is None:
        settings = {}
        for k, def_val in DEFAULT_NOTIFICATION_SETTINGS.items():
            settings[k] = get_setting(cursor, k, def_val)

    if str(settings.get("notifications_enabled", "1")) != "1":
        return []

    now = current_time or datetime.now()
    now_hm = now.strftime("%H:%M")

    # Fetch today's record
    record = fetch_today_record(cursor, current_date=now.date())
    bf = record[0] if record else 0
    lu = record[1] if record else 0
    dn = record[2] if record else 0

    pending = []

    # 1. Breakfast Check
    bf_time = settings.get("breakfast_time", "10:00")
    if now_hm >= bf_time and bf == 0 and "breakfast" not in sent_keys_today:
        pending.append((
            "breakfast",
            "🍳 Breakfast Reminder",
            "Don't forget to mark your Breakfast in MealTrack AI!",
        ))

    # 2. Lunch Check
    lu_time = settings.get("lunch_time", "14:30")
    if now_hm >= lu_time and lu == 0 and "lunch" not in sent_keys_today:
        pending.append((
            "lunch",
            "🍛 Lunch Reminder",
            "Don't forget to mark your Lunch in MealTrack AI!",
        ))

    # 3. Dinner Check
    dn_time = settings.get("dinner_time", "22:00")
    if now_hm >= dn_time and dn == 0 and "dinner" not in sent_keys_today:
        pending.append((
            "dinner",
            "🌙 Dinner Reminder",
            "Don't forget to mark your Dinner in MealTrack AI!",
        ))

    # 4. Daily Inactivity Check (No meals recorded at all)
    inact_enabled = str(settings.get("inactivity_check", "1")) == "1"
    inact_time = settings.get("inactivity_time", "21:30")
    if inact_enabled and now_hm >= inact_time and (bf == 0 and lu == 0 and dn == 0) and "inactivity" not in sent_keys_today:
        pending.append((
            "inactivity",
            "⚠️ Missing Meals Alert",
            "No meals have been recorded for today yet. Take a moment to log them in MealTrack AI!",
        ))

    return pending


