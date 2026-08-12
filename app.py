import customtkinter as ctk
import sqlite3
from datetime import date, datetime
import calendar

# ---------------- DESIGN SYSTEM ----------------

BG_COLOR = "#0B0818"          # Main background
CARD_COLOR = "#161126"        # Cards / panels
CARD_HOVER = "#21183A"        # Hover state
PRIMARY_COLOR = "#7C3AED"     # Main purple
PRIMARY_HOVER = "#6D28D9"     # Darker purple
SUCCESS_COLOR = "#22C55E"     # Completed meals
WARNING_COLOR = "#F59E0B"     # Spending / attention
DANGER_COLOR = "#F43F5E"      # Missed / warning
TEXT_COLOR = "#F8FAFC"        # Main text
MUTED_TEXT = "#A1A1AA"        # Secondary text
BORDER_COLOR = "#2D2445"      # Subtle borders


connection = sqlite3.connect("meals.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS meals(
    date TEXT PRIMARY KEY,
    breakfast INTEGER,
    lunch INTEGER,
    dinner INTEGER,
    outside_dinner INTEGER DEFAULT 0,
    bill INTEGER
)
""")

connection.commit()
try:
    cursor.execute(
        "ALTER TABLE meals ADD COLUMN outside_dinner INTEGER DEFAULT 0"
    )
    connection.commit()
except sqlite3.OperationalError:
    pass

bill = 0

# Dashboard card references
dashboard_bill_value = None
dashboard_meals_value = None
dashboard_month_value = None
dashboard_average_value = None
#-------------------functions----------------------

def save_record():

    today = date.today().strftime("%d-%m-%Y")

    breakfast = checkboxes["Breakfast"].get()
    lunch = checkboxes["Lunch"].get()
    dinner = checkboxes["Dinner"].get()

    outside_dinner = 0

    if date.today().weekday() == 6:
        if outside_dinner_entry.get():
            outside_dinner = int(outside_dinner_entry.get())

    cursor.execute(
        "SELECT * FROM meals WHERE date=?",
        (today,)
    )

    record = cursor.fetchone()

    if record:
        cursor.execute("""
            UPDATE meals
            SET breakfast=?,
            lunch=?,
            dinner=?,
            outside_dinner=?,
            bill=?
            WHERE date=?
        """, ((breakfast, lunch, dinner, outside_dinner, bill, today)))

    else:
        cursor.execute("""
        INSERT INTO meals
        (date, breakfast, lunch, dinner, outside_dinner, bill)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (today, breakfast, lunch, dinner, outside_dinner, bill))

    connection.commit()

    print("Record Saved!")


def load_today_record():

    today = date.today().strftime("%d-%m-%Y")

    cursor.execute(
        """
        SELECT breakfast, lunch, dinner, outside_dinner, bill
        FROM meals
        WHERE date=?
        """,
        (today,)
    )

    record = cursor.fetchone()

    if record:

        breakfast, lunch, dinner, saved_outside_dinner, saved_bill = record

        # Load saved checkbox states
        if breakfast == 1:
            checkboxes["Breakfast"].select()

        if lunch == 1:
            checkboxes["Lunch"].select()

        if dinner == 1:
            checkboxes["Dinner"].select()

        # Load saved Sunday outside dinner amount
        if date.today().weekday() == 6:

            outside_dinner_entry.delete(0, "end")

            if saved_outside_dinner > 0:
                outside_dinner_entry.insert(
                    0,
                    str(saved_outside_dinner)
                )

        # Load saved bill
        global bill

        bill = saved_bill

        bill_label.configure(
            text=f"₹{saved_bill}"
        )

        # Load completed meal count
        completed_meals = breakfast + lunch + dinner

        meal_count_label.configure(
            text=f"Meals Completed: {completed_meals} / {len(meals)}"
        )
    update_dashboard_cards()

def show_history():

    cursor.execute("""
        SELECT date, breakfast, lunch, dinner, bill
        FROM meals
        ORDER BY date DESC
    """)

    records = cursor.fetchall()
    total_spent = sum(record[4] for record in records)

    # Create history panel inside the main window
    history_frame = ctk.CTkFrame(
        app,
        width=700,
        height=400
    )

    history_frame.place(
        relx=0.5,
        rely=0.5,
        anchor="center"
    )

    # Title
    title = ctk.CTkLabel(
        history_frame,
        text="Meal History",
        font=("Arial", 24, "bold")
    )

    title.pack(pady=20)

    # Table headings
    heading = ctk.CTkLabel(
        history_frame,
        text="Date          Meals Completed          Bill",
        font=("Arial", 15, "bold")
    )

    heading.pack(pady=10)

    # Display records
    for record in records:

        date_value, breakfast, lunch, dinner, bill_value = record

        completed = breakfast + lunch + dinner

        row_text = (
            f"{date_value}          "
            f"{completed} / 3          "
            f"₹{bill_value}"
        )

        row = ctk.CTkLabel(
            history_frame,
            text=row_text,
            font=("Arial", 14)
        )

        row.pack(pady=8)

    total_label = ctk.CTkLabel(
        history_frame,
        text=f"Total Spent: ₹{total_spent}",
        font=("Arial", 16, "bold")
        )

    total_label.pack(pady=10)

    
    # Close button
    close_button = ctk.CTkButton(
        history_frame,
        text="Close",
        command=history_frame.destroy
    )

    close_button.pack(pady=20)


def show_statistics():

    cursor.execute("""
        SELECT breakfast, lunch, dinner, bill
        FROM meals
    """)

    records = cursor.fetchall()

    total_days = len(records)

    total_meals = 0
    total_spending = 0

    for record in records:

        breakfast, lunch, dinner, bill_value = record

        total_meals += breakfast + lunch + dinner
        total_spending += bill_value

    total_possible_meals = total_days * 3

    if total_days > 0:
        average_meals = total_meals / total_days
        average_spending = total_spending / total_days
    else:
        average_meals = 0
        average_spending = 0

    print("Total Days:", total_days)
    print("Total Meals:", total_meals, "/", total_possible_meals)
    print("Average Meals per Day:", average_meals)
    print("Total Spending: ₹", total_spending)
    print("Average Daily Spending: ₹", average_spending)


def show_monthly_summary():

    today = date.today()

    current_month = today.strftime("%m")
    current_year = today.strftime("%Y")

    # Get all records from the current month
    cursor.execute(
        """
        SELECT date, breakfast, lunch, dinner, bill
        FROM meals
        WHERE substr(date, 4, 2) = ?
        AND substr(date, 7, 4) = ?
        ORDER BY date ASC
        """,
        (current_month, current_year)
    )

    records = cursor.fetchall()

    # Calculate summary
    total_spent = sum(record[4] for record in records)

    total_meals = sum(
        record[1] + record[2] + record[3]
        for record in records
    )

    days_in_month = calendar.monthrange(
        today.year,
        today.month
    )[1]

    total_possible_meals = days_in_month * len(meals)

    days_recorded = len(records)

    if days_recorded > 0:
        average_spending = total_spent / days_recorded
    else:
        average_spending = 0

    # Highest and lowest spending days
    if records:
        highest_day = max(records, key=lambda record: record[4])
        lowest_day = min(records, key=lambda record: record[4])
    else:
        highest_day = None
        lowest_day = None

    # Create summary popup inside main window
    summary_frame = ctk.CTkFrame(
        app,
        width=500,
        height=500
    )

    summary_frame.place(
        relx=0.5,
        rely=0.5,
        anchor="center"
    )

    # Title
    title = ctk.CTkLabel(
        summary_frame,
        text="Monthly Summary",
        font=("Arial", 24, "bold")
    )

    title.pack(pady=(20, 15))

    # Month
    month_label = ctk.CTkLabel(
        summary_frame,
        text=today.strftime("%B %Y"),
        font=("Arial", 16)
    )

    month_label.pack(pady=5)

    # Total spent
    total_label = ctk.CTkLabel(
        summary_frame,
        text=f"Total Spent: ₹{total_spent}",
        font=("Arial", 16, "bold")
    )

    total_label.pack(pady=8)

    # Average spending
    average_label = ctk.CTkLabel(
        summary_frame,
        text=f"Average / Day: ₹{average_spending:.2f}",
        font=("Arial", 16)
    )

    average_label.pack(pady=8)

    # Meals completed
    meals_label = ctk.CTkLabel(
        summary_frame,
        text=f"Meals Completed: {total_meals} / {total_possible_meals}",
        font=("Arial", 16)
    )

    meals_label.pack(pady=8)

    # Days recorded
    days_label = ctk.CTkLabel(
        summary_frame,
        text=f"Days Recorded: {days_recorded}",
        font=("Arial", 16)
    )

    days_label.pack(pady=8)

    # Highest spending day
    if highest_day:

        highest_label = ctk.CTkLabel(
            summary_frame,
            text=f"Highest Spending: {highest_day[0]}  ₹{highest_day[4]}",
            font=("Arial", 15)
        )

        highest_label.pack(pady=8)

    # Lowest spending day
    if lowest_day:

        lowest_label = ctk.CTkLabel(
            summary_frame,
            text=f"Lowest Spending: {lowest_day[0]}  ₹{lowest_day[4]}",
            font=("Arial", 15)
        )

        lowest_label.pack(pady=8)

    # Close button
    close_button = ctk.CTkButton(
        summary_frame,
        text="Close",
        command=summary_frame.destroy
    )

    close_button.pack(pady=20)


def update_dashboard_cards():

    today = date.today()

    # Today's values
    completed_meals = sum(
        checkboxes[meal].get()
        for meal in meals
    )

    # Monthly values
    current_month = today.strftime("%m")
    current_year = today.strftime("%Y")

    cursor.execute(
        """
        SELECT bill
        FROM meals
        WHERE substr(date, 4, 2) = ?
        AND substr(date, 7, 4) = ?
        """,
        (current_month, current_year)
    )

    monthly_records = cursor.fetchall()

    total_month_spent = sum(
        record[0] for record in monthly_records
    )

    days_recorded = len(monthly_records)

    if days_recorded > 0:
        average_daily = total_month_spent / days_recorded
    else:
        average_daily = 0

    # Update dashboard
    if dashboard_bill_value:
        dashboard_bill_value.configure(
            text=f"₹{bill}"
        )

    if dashboard_meals_value:
        dashboard_meals_value.configure(
            text=f"{completed_meals} / {len(meals)}"
        )

    if dashboard_month_value:
        dashboard_month_value.configure(
            text=f"₹{total_month_spent}"
        )

    if dashboard_average_value:
        dashboard_average_value.configure(
            text=f"₹{average_daily:.2f}"
        )

def update_bill():

    global bill

    bill = 0
    completed_meals = 0

    today = date.today()

    for meal, price in meals.items():

        if checkboxes[meal].get() == 1:

            completed_meals += 1

            # Sunday dinner is bought outside
            if meal == "Dinner" and today.weekday() == 6:

                amount = outside_dinner_entry.get()

                if amount:
                    bill += int(amount)

            else:
                bill += price

    bill_label.configure(text=f"₹{bill}")

    meal_count_label.configure(
        text=f"Meals Completed: {completed_meals} / {len(meals)}"
    )
    update_dashboard_cards()


meals = {
    "Breakfast": 30,
    "Lunch": 50,
    "Dinner": 30
}

checkboxes = {}
# set apprearance mode
ctk.set_appearance_mode("dark")

# Create main application window
app = ctk.CTk()
app.configure(fg_color=BG_COLOR)

# set window title
app.title("MealTrack AI")

# set window size
app.geometry("600x400")

# ------------HEADER FRAME-----------
header_frame = ctk.CTkFrame(
    app,
    fg_color=CARD_COLOR,
    corner_radius=18,
    border_width=1,
    border_color=BORDER_COLOR
)

header_frame.pack(fill = "x", padx = 20, pady = 20)

# ---------------- HEADER CONTENT ----------------

header_content = ctk.CTkFrame(
    header_frame,
    fg_color="transparent"
)

header_content.pack(
    fill="x",
    padx=25,
    pady=20
)


# Left side
header_left = ctk.CTkFrame(
    header_content,
    fg_color="transparent"
)

header_left.pack(
    side="left",
    fill="both",
    expand=True
)

# Determine greeting based on current time

current_hour = datetime.now().hour

if current_hour < 12:
    greeting = "Good Morning"
elif current_hour < 17:
    greeting = "Good Afternoon"
else:
    greeting = "Good Evening"


# Create today's date text

today = date.today()
date_text = today.strftime("%A, %d %B %Y")
# Greeting
greeting_label = ctk.CTkLabel(
    header_left,
    text=f"{greeting}, Sowmya! 👋",
    font=("Arial", 28, "bold"),
    text_color=TEXT_COLOR
)

greeting_label.pack(
    anchor="w"
)


# Subtitle
subtitle_label = ctk.CTkLabel(
    header_left,
    text="Track your meals, control your spending, live better.",
    font=("Arial", 14),
    text_color=MUTED_TEXT
)

subtitle_label.pack(
    anchor="w",
    pady=(5, 0)
)


# Right side
header_right = ctk.CTkFrame(
    header_content,
    fg_color=PRIMARY_COLOR,
    corner_radius=12
)

header_right.pack(
    side="right",
    padx=(20, 0),
    pady=5
)


# Date
date_label = ctk.CTkLabel(
    header_right,
    text=date_text,
    font=("Arial", 14, "bold"),
    text_color=TEXT_COLOR
)

date_label.pack(
    padx=18,
    pady=10
)

# ---------------- DASHBOARD SUMMARY ----------------

dashboard_frame = ctk.CTkFrame(
    app,
    fg_color="transparent"
)

dashboard_frame.pack(
    fill="x",
    padx=20,
    pady=(0, 10)
)


# Today's Bill Card
bill_card = ctk.CTkFrame(
    dashboard_frame,
    fg_color=CARD_COLOR,
    corner_radius=16,
    border_width=1,
    border_color=BORDER_COLOR
)

bill_card.pack(
    side="left",
    fill="both",
    expand=True,
    padx=5
)

ctk.CTkLabel(
    bill_card,
    text="Today's Bill",
    font=("Arial", 13),
    text_color=MUTED_TEXT
).pack(
    anchor="w",
    padx=15,
    pady=(15, 3)
)

dashboard_bill_value = ctk.CTkLabel(
    bill_card,
    text="₹0",
    font=("Arial", 24, "bold"),
    text_color=TEXT_COLOR
)

dashboard_bill_value.pack(
    anchor="w",
    padx=15,
    pady=(0, 15)
)


# Meals Completed Card
meals_card = ctk.CTkFrame(
    dashboard_frame,
    fg_color=CARD_COLOR,
    corner_radius=16,
    border_width=1,
    border_color=BORDER_COLOR
)

meals_card.pack(
    side="left",
    fill="both",
    expand=True,
    padx=5
)

ctk.CTkLabel(
    meals_card,
    text="Meals Completed",
    font=("Arial", 13),
    text_color=MUTED_TEXT
).pack(
    anchor="w",
    padx=15,
    pady=(15, 3)
)

dashboard_meals_value = ctk.CTkLabel(
    meals_card,
    text="0 / 3",
    font=("Arial", 24, "bold"),
    text_color=SUCCESS_COLOR
)

dashboard_meals_value.pack(
    anchor="w",
    padx=15,
    pady=(0, 15)
)


# This Month Card
month_card = ctk.CTkFrame(
    dashboard_frame,
    fg_color=CARD_COLOR,
    corner_radius=16,
    border_width=1,
    border_color=BORDER_COLOR
)

month_card.pack(
    side="left",
    fill="both",
    expand=True,
    padx=5
)

ctk.CTkLabel(
    month_card,
    text="This Month",
    font=("Arial", 13),
    text_color=MUTED_TEXT
).pack(
    anchor="w",
    padx=15,
    pady=(15, 3)
)

dashboard_month_value = ctk.CTkLabel(
    month_card,
    text="₹0",
    font=("Arial", 24, "bold"),
    text_color=WARNING_COLOR
)

dashboard_month_value.pack(
    anchor="w",
    padx=15,
    pady=(0, 15)
)


# Average / Day Card
average_card = ctk.CTkFrame(
    dashboard_frame,
    fg_color=CARD_COLOR,
    corner_radius=16,
    border_width=1,
    border_color=BORDER_COLOR
)

average_card.pack(
    side="left",
    fill="both",
    expand=True,
    padx=5
)

ctk.CTkLabel(
    average_card,
    text="Avg / Day",
    font=("Arial", 13),
    text_color=MUTED_TEXT
).pack(
    anchor="w",
    padx=15,
    pady=(15, 3)
)

dashboard_average_value = ctk.CTkLabel(
    average_card,
    text="₹0.00",
    font=("Arial", 24, "bold"),
    text_color=PRIMARY_COLOR
)

dashboard_average_value.pack(
    anchor="w",
    padx=15,
    pady=(0, 15)
)

# ---------------- MEALS FRAME ----------------
meals_frame = ctk.CTkFrame(
    app,
    fg_color=CARD_COLOR,
    corner_radius=18,
    border_width=1,
    border_color=BORDER_COLOR
)
meals_frame.pack(fill="x", padx=20, pady=10)


# ---------------- TODAY'S MEALS ----------------

meals_heading = ctk.CTkLabel(
    meals_frame,
    text="Today's Meals",
    font=("Arial", 20, "bold"),
    text_color=TEXT_COLOR
)

meals_heading.pack(
    anchor="w",
    padx=20,
    pady=(20, 5)
)


meals_subheading = ctk.CTkLabel(
    meals_frame,
    text="Track what you've had today",
    font=("Arial", 13),
    text_color=MUTED_TEXT
)

meals_subheading.pack(
    anchor="w",
    padx=20,
    pady=(0, 15)
)


# Container for individual meal cards
meal_cards_frame = ctk.CTkFrame(
    meals_frame,
    fg_color="transparent"
)

meal_cards_frame.pack(
    fill="x",
    padx=15,
    pady=(0, 15)
)


row = 0
outside_dinner_entry = None

meal_icons = {
    "Breakfast": "🍳",
    "Lunch": "🍛",
    "Dinner": "🌙"
}


for meal, price in meals.items():

    # Individual meal card
    meal_card = ctk.CTkFrame(
        meal_cards_frame,
        fg_color=CARD_HOVER,
        corner_radius=14,
        border_width=1,
        border_color=BORDER_COLOR
    )

    meal_card.pack(
        fill="x",
        padx=5,
        pady=6
    )


    # Meal icon + name
    meal_label = ctk.CTkLabel(
        meal_card,
        text=f"{meal_icons[meal]}  {meal}",
        font=("Arial", 15, "bold"),
        text_color=TEXT_COLOR
    )

    meal_label.pack(
        side="left",
        padx=15,
        pady=14
    )


    # Meal price
    if meal == "Dinner" and date.today().weekday() == 6:

        price_text = "Outside"

    else:

        price_text = f"₹{price}"


    price_label = ctk.CTkLabel(
        meal_card,
        text=price_text,
        font=("Arial", 14),
        text_color=MUTED_TEXT
    )

    price_label.pack(
        side="right",
        padx=(10, 15),
        pady=14
    )


    # Checkbox
    meal_checkbox = ctk.CTkCheckBox(
        meal_card,
        text="",
        command=update_bill,
        fg_color=PRIMARY_COLOR,
        hover_color=PRIMARY_HOVER,
        border_color=MUTED_TEXT,
        border_width=2,
        corner_radius=6,
        checkmark_color=TEXT_COLOR
    )

    meal_checkbox.pack(
        side="right",
        padx=5,
        pady=14
    )


    checkboxes[meal] = meal_checkbox


    # Sunday outside dinner amount
    if meal == "Dinner":

        outside_dinner_entry = ctk.CTkEntry(
            meal_card,
            placeholder_text="₹ amount",
            width=110,
            height=32
        )

        if date.today().weekday() == 6:

            outside_dinner_entry.pack(
                side="right",
                padx=10,
                pady=10
            )

            outside_dinner_entry.bind(
                "<KeyRelease>",
                lambda event: update_bill()
            )


    row += 1
# ---------------- BILL FRAME ----------------

bill_frame = ctk.CTkFrame(
    app,
    fg_color=CARD_COLOR,
    corner_radius=18,
    border_width=1,
    border_color=BORDER_COLOR
)
# Today's Bill Heading

bill_heading = ctk.CTkLabel(
    bill_frame,
    text="Today's Bill",
    font=("Arial", 18, "bold")
)

bill_heading.pack(anchor="w", padx=20, pady=(15, 5))


# Bill Amount

bill_label = ctk.CTkLabel(
    bill_frame,
    text="₹0",
    font=("Arial", 24, "bold")
)

bill_label.pack(anchor="w", padx=20, pady=(0, 5))


# Meal Count

meal_count_label = ctk.CTkLabel(
    bill_frame,
    text="Meals Completed: 0 / 3",
    font=("Arial", 14)
)

meal_count_label.pack(anchor="w", padx=20, pady=(0, 15))

bill_frame.pack(fill="x", padx=20, pady=10)

# ---------------- BUTTON FRAME ----------------

button_frame = ctk.CTkFrame(
    app,
    fg_color=CARD_COLOR,
    corner_radius=18,
    border_width=1,
    border_color=BORDER_COLOR
)

save_button = ctk.CTkButton(
    button_frame,
    text="Save Today's Record",
    command=save_record,
    fg_color=PRIMARY_COLOR,
    hover_color=PRIMARY_HOVER,
    corner_radius=10
)

save_button.pack(pady=10)

history_button = ctk.CTkButton(
    button_frame,
    text="Meal History",
    command=show_history,
    fg_color=PRIMARY_COLOR,
    hover_color=PRIMARY_HOVER,
    corner_radius=10
)

history_button.pack(pady=10)


summary_button = ctk.CTkButton(
    button_frame,
    text="Monthly Summary",
    command=show_monthly_summary,
    fg_color=PRIMARY_COLOR,
    hover_color=PRIMARY_HOVER,
    corner_radius=10
)

summary_button.pack(pady=10)


button_frame.pack(fill="x", padx=20, pady=10)

load_today_record()
#start application
app.mainloop()