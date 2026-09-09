import calendar
from datetime import date, datetime, timedelta
import customtkinter as ctk

from constants import (
    APP_TITLE,
    BG_COLOR,
    BORDER_COLOR,
    CARD_COLOR,
    CARD_HOVER,
    DANGER_COLOR,
    MEALS,
    MEAL_ICONS,
    MUTED_TEXT,
    PRIMARY_COLOR,
    PRIMARY_HOVER,
    SUCCESS_COLOR,
    TEXT_COLOR,
    USER_NAME,
    WARNING_COLOR,
    WINDOW_SIZE,
)
from database import get_setting, init_database, set_setting
from logic import (
    DATE_FORMAT,
    DEFAULT_NOTIFICATION_SETTINGS,
    calculate_bill,
    check_pending_reminders,
    fetch_dashboard_totals,
    fetch_history_records,
    fetch_meal_type_distribution,
    fetch_monthly_summary,
    fetch_record_by_date,
    fetch_today_record,
    get_completed_meals,
    get_display_date,
    get_greeting,
    get_motivation_message,
    get_quick_insights,
    get_recorded_days,
    get_recent_spending_records,
    get_today_string,
    is_sunday,
    parse_date_string,
    parse_outside_dinner_amount,
    save_date_meal_record,
    save_meal_record,
    send_system_notification,
)



class MealTrackApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")

        self.connection, self.cursor = init_database()
        self.user_name = get_setting(self.cursor, "user_name", USER_NAME)
        self.meal_prices = {
            "Breakfast": int(get_setting(self.cursor, "price_breakfast", MEALS["Breakfast"])),
            "Lunch": int(get_setting(self.cursor, "price_lunch", MEALS["Lunch"])),
            "Dinner": int(get_setting(self.cursor, "price_dinner", MEALS["Dinner"])),
        }
        self.bill = 0
        self.today_meal_states = {"Breakfast": 0, "Lunch": 0, "Dinner": 0}
        self.today_outside_dinner = 0

        # Notification Preferences & State
        self.notification_settings = {}
        for k, def_val in DEFAULT_NOTIFICATION_SETTINGS.items():
            self.notification_settings[k] = get_setting(self.cursor, k, def_val)

        self.sent_reminders_today = set()
        self.last_reminder_check_day = date.today().day
        self.toast_banner = None

        # Active navigation view
        self.current_view = "dashboard"
        self.nav_buttons = {}

        # Selected calendar month/year for overview
        today = date.today()
        self.cal_month = today.month
        self.cal_year = today.year

        # UI References
        self.app = ctk.CTk()
        self.app.title(APP_TITLE)
        self.app.geometry(WINDOW_SIZE)
        self.app.minsize(1050, 680)
        self.app.configure(fg_color=BG_COLOR)
        self.app.protocol("WM_DELETE_WINDOW", self.close)

        self.sidebar_frame = None
        self.content_container = None
        self.active_view_frame = None

        self.sidebar_month_spend_label = None
        self.sidebar_days_label = None

        # Build main layout and load initial state
        self.build_main_layout()
        self.load_today_record()
        self.show_view("dashboard")

        # Start periodic notification checker (first check after 5 seconds)
        self.app.after(5000, self.run_notification_checker)

    def show_toast_banner(self, title, message):
        if self.toast_banner and self.toast_banner.winfo_exists():
            try:
                self.toast_banner.destroy()
            except Exception:
                pass

        self.toast_banner = ctk.CTkFrame(
            self.app,
            fg_color="#1F143A",
            corner_radius=16,
            border_width=2,
            border_color=PRIMARY_COLOR,
            width=360,
            height=90,
        )
        self.toast_banner.place(relx=0.98, rely=0.03, anchor="ne")
        self.toast_banner.pack_propagate(False)

        content = ctk.CTkFrame(self.toast_banner, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=14, pady=10)

        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")

        t_lbl = ctk.CTkLabel(top_row, text=title, font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
        t_lbl.pack(side="left")

        close_btn = ctk.CTkButton(
            top_row,
            text="✕",
            width=22,
            height=22,
            fg_color="transparent",
            hover_color="#3B1C66",
            font=("Arial", 11, "bold"),
            text_color=MUTED_TEXT,
            command=self.toast_banner.destroy,
        )
        close_btn.pack(side="right")

        m_lbl = ctk.CTkLabel(
            content,
            text=message,
            font=("Arial", 11),
            text_color=MUTED_TEXT,
            justify="left",
            wraplength=310,
        )
        m_lbl.pack(anchor="w", pady=(3, 0))

        # Auto dismiss after 7 seconds
        self.app.after(
            7000,
            lambda: self.toast_banner.destroy() if self.toast_banner and self.toast_banner.winfo_exists() else None,
        )

    def run_notification_checker(self):
        try:
            today_d = date.today().day
            if today_d != self.last_reminder_check_day:
                self.sent_reminders_today.clear()
                self.last_reminder_check_day = today_d

            pending = check_pending_reminders(
                self.cursor,
                sent_keys_today=self.sent_reminders_today,
                settings=self.notification_settings,
            )

            for alert_key, title, msg in pending:
                self.sent_reminders_today.add(alert_key)
                send_system_notification(title, msg)
                self.show_toast_banner(title, msg)
        except Exception as e:
            print("Notification checker error:", e)

        # Check again every 30 seconds
        self.app.after(30000, self.run_notification_checker)

    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass
        self.app.destroy()

    def run(self):
        self.app.mainloop()


    # -------------------------------------------------------------
    # STATE & DATA SYNCHRONIZATION
    # -------------------------------------------------------------

    def load_today_record(self):
        record = fetch_today_record(self.cursor)
        if record:
            bf, lu, dn, out_dn, saved_b = record
            self.today_meal_states = {"Breakfast": bf, "Lunch": lu, "Dinner": dn}
            self.today_outside_dinner = out_dn
            self.bill = saved_b
        else:
            self.today_meal_states = {"Breakfast": 0, "Lunch": 0, "Dinner": 0}
            self.today_outside_dinner = 0
            self.bill = 0

    def refresh_all_dashboard_views(self, edited_date=None):
        today_str = get_today_string()
        if edited_date == today_str or edited_date is None:
            self.load_today_record()

        self.update_sidebar_pulse()

        # Re-render current active view to reflect updated database values
        if self.current_view:
            self.show_view(self.current_view, force_refresh=True)

    def update_sidebar_pulse(self):
        summary = fetch_monthly_summary(self.cursor, len(self.meal_prices))
        if self.sidebar_month_spend_label and self.sidebar_month_spend_label.winfo_exists():
            self.sidebar_month_spend_label.configure(text=f"Spent: ₹{summary['total_spent']}")
        if self.sidebar_days_label and self.sidebar_days_label.winfo_exists():
            self.sidebar_days_label.configure(text=f"Saved Days: {summary['days_recorded']}")

    # -------------------------------------------------------------
    # MAIN SHELL & SIDEBAR NAVIGATION
    # -------------------------------------------------------------

    def build_main_layout(self):
        # Master horizontal layout
        master_frame = ctk.CTkFrame(self.app, fg_color="transparent")
        master_frame.pack(fill="both", expand=True)

        # Left Sidebar
        self.sidebar_frame = ctk.CTkFrame(
            master_frame,
            width=220,
            fg_color="#120D24",
            corner_radius=0,
            border_width=1,
            border_color="#1F1638",
        )
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        # Sidebar Header Logo
        logo_row = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        logo_row.pack(fill="x", padx=16, pady=(24, 4))

        logo_icon = ctk.CTkLabel(
            logo_row,
            text="🍴",
            font=("Arial", 22),
            fg_color=PRIMARY_COLOR,
            width=38,
            height=38,
            corner_radius=19,
        )
        logo_icon.pack(side="left", padx=(0, 10))

        title_col = ctk.CTkFrame(logo_row, fg_color="transparent")
        title_col.pack(side="left")

        logo_title = ctk.CTkLabel(
            title_col,
            text="MealTrack AI",
            font=("Arial", 17, "bold"),
            text_color=TEXT_COLOR,
        )
        logo_title.pack(anchor="w")

        logo_subtitle = ctk.CTkLabel(
            title_col,
            text="Eat Smart • Track Smarter",
            font=("Arial", 10),
            text_color=MUTED_TEXT,
        )
        logo_subtitle.pack(anchor="w")

        # Divider
        nav_divider = ctk.CTkFrame(self.sidebar_frame, height=1, fg_color=BORDER_COLOR)
        nav_divider.pack(fill="x", padx=16, pady=16)

        # Navigation Buttons List
        nav_items = [
            ("dashboard", "⌂  Dashboard"),
            ("meals", "🍽  Today's Meals"),
            ("history", "📅  Meal History"),
            ("monthly_summary", "📊  Monthly Summary"),
            ("analytics", "📈  Analytics"),
            ("settings", "⚙  Settings"),
            ("about", "ℹ  About"),
        ]

        self.nav_buttons = {}
        for view_key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=label,
                command=lambda vk=view_key: self.show_view(vk),
                fg_color="transparent",
                hover_color=CARD_HOVER,
                text_color=MUTED_TEXT,
                corner_radius=10,
                anchor="w",
                height=40,
                font=("Arial", 13, "bold"),
            )
            btn.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[view_key] = btn

        # Sidebar Bottom Card (Inspiration Quote Card)
        bottom_card = ctk.CTkFrame(
            self.sidebar_frame,
            fg_color=CARD_HOVER,
            corner_radius=16,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        bottom_card.pack(side="bottom", fill="x", padx=14, pady=18)

        quote_icon = ctk.CTkLabel(bottom_card, text="🥗", font=("Arial", 22))
        quote_icon.pack(anchor="w", padx=14, pady=(12, 2))

        quote_text = ctk.CTkLabel(
            bottom_card,
            text='"Small food choices,\nbig health results!"',
            font=("Arial", 12, "italic"),
            text_color=TEXT_COLOR,
            justify="left",
        )
        quote_text.pack(anchor="w", padx=14, pady=(0, 8))

        pulse_divider = ctk.CTkFrame(bottom_card, height=1, fg_color=BORDER_COLOR)
        pulse_divider.pack(fill="x", padx=12, pady=4)

        self.sidebar_month_spend_label = ctk.CTkLabel(
            bottom_card,
            text="Spent: ₹0",
            font=("Arial", 11, "bold"),
            text_color=PRIMARY_COLOR,
        )
        self.sidebar_month_spend_label.pack(anchor="w", padx=14, pady=(2, 0))

        self.sidebar_days_label = ctk.CTkLabel(
            bottom_card,
            text="Saved Days: 0",
            font=("Arial", 11),
            text_color=MUTED_TEXT,
        )
        self.sidebar_days_label.pack(anchor="w", padx=14, pady=(0, 10))

        # Main View Content Area
        self.content_container = ctk.CTkFrame(master_frame, fg_color="transparent")
        self.content_container.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    def show_view(self, view_name, force_refresh=False):
        if self.current_view == view_name and not force_refresh and self.active_view_frame is not None:
            return

        self.current_view = view_name

        # Update sidebar button active styles
        for key, btn in self.nav_buttons.items():
            if key == view_name:
                btn.configure(
                    fg_color=PRIMARY_COLOR,
                    hover_color=PRIMARY_HOVER,
                    text_color=TEXT_COLOR,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    hover_color=CARD_HOVER,
                    text_color=MUTED_TEXT,
                )

        # Clear existing view
        if self.active_view_frame:
            self.active_view_frame.destroy()

        # Render corresponding view
        if view_name == "dashboard":
            self.render_dashboard_view()
        elif view_name == "meals":
            self.render_today_meals_view()
        elif view_name == "history":
            self.render_history_view()
        elif view_name == "monthly_summary":
            self.render_monthly_summary_view()
        elif view_name == "analytics":
            self.render_analytics_view()
        elif view_name == "settings":
            self.render_settings_view()
        elif view_name == "about":
            self.render_about_view()

    # -------------------------------------------------------------
    # VIEW 1: EXECUTIVE DASHBOARD (Matching target-dashboard.png)
    # -------------------------------------------------------------

    def render_dashboard_view(self):
        self.active_view_frame = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
        )
        self.active_view_frame.pack(fill="both", expand=True)

        # --- 1. Top Header Row ---
        header_row = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=6, pady=(6, 12))

        header_left = ctk.CTkFrame(header_row, fg_color="transparent")
        header_left.pack(side="left")

        greeting_text = f"{get_greeting()}, {self.user_name}! 🌙"
        greeting_label = ctk.CTkLabel(
            header_left,
            text=greeting_text,
            font=("Arial", 26, "bold"),
            text_color=TEXT_COLOR,
        )
        greeting_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_left,
            text="Track your meals, control your spending, live better.",
            font=("Arial", 13),
            text_color=MUTED_TEXT,
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # Date Badge Pill Top Right
        date_pill = ctk.CTkFrame(
            header_row,
            fg_color=CARD_COLOR,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        date_pill.pack(side="right", pady=4)

        date_pill_label = ctk.CTkLabel(
            date_pill,
            text=f"📅  {get_display_date()}",
            font=("Arial", 13, "bold"),
            text_color=TEXT_COLOR,
        )
        date_pill_label.pack(padx=16, pady=8)

        # --- 2. Top KPI Cards Row ---
        kpi_row = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        kpi_row.pack(fill="x", padx=2, pady=(0, 14))

        completed_today = get_completed_meals(self.today_meal_states)
        total_month_spent, avg_daily = fetch_dashboard_totals(self.cursor)

        self.create_dashboard_kpi_card(
            kpi_row,
            icon="🍽️",
            title="Today's Bill",
            value=f"₹{self.bill}",
            color="#8B5CF6",
            icon_bg="#26174D",
        ).pack(side="left", fill="both", expand=True, padx=4)

        self.create_dashboard_kpi_card(
            kpi_row,
            icon="🍴",
            title="Meals Completed",
            value=f"{completed_today} / 3",
            color="#10B981",
            icon_bg="#0B3728",
        ).pack(side="left", fill="both", expand=True, padx=4)

        self.create_dashboard_kpi_card(
            kpi_row,
            icon="🔥",
            title="This Month",
            value=f"₹{total_month_spent} spent",
            color="#F59E0B",
            icon_bg="#3F270B",
        ).pack(side="left", fill="both", expand=True, padx=4)

        self.create_dashboard_kpi_card(
            kpi_row,
            icon="💖",
            title="Avg / Day",
            value=f"₹{avg_daily:.0f}",
            color="#EC4899",
            icon_bg="#401228",
        ).pack(side="left", fill="both", expand=True, padx=4)

        # --- 3. Middle Section: 3-Column Layout ---
        mid_row = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        mid_row.pack(fill="x", padx=2, pady=(0, 14))

        # Column 1: Today's Meals Card (40% width)
        today_meals_col = ctk.CTkFrame(mid_row, fg_color="transparent")
        today_meals_col.pack(side="left", fill="both", expand=True, padx=4)
        self.build_dashboard_today_meals_card(today_meals_col)

        # Column 2: Month Overview Calendar (30% width)
        calendar_col = ctk.CTkFrame(mid_row, fg_color="transparent", width=290)
        calendar_col.pack(side="left", fill="y", padx=4)
        calendar_col.pack_propagate(False)
        self.build_dashboard_calendar_card(calendar_col)

        # Column 3: Monthly Summary (30% width)
        summary_col = ctk.CTkFrame(mid_row, fg_color="transparent", width=290)
        summary_col.pack(side="left", fill="y", padx=4)
        summary_col.pack_propagate(False)
        self.build_dashboard_month_summary_card(summary_col)

        # --- 4. Bottom Section: 3 Columns ---
        bottom_row = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        bottom_row.pack(fill="x", padx=2, pady=(0, 14))

        # Column 1: Spending Trend Bar Chart
        trend_col = ctk.CTkFrame(bottom_row, fg_color="transparent")
        trend_col.pack(side="left", fill="both", expand=True, padx=4)
        self.build_dashboard_spending_trend_card(trend_col)

        # Column 2: Quick Insights
        insights_col = ctk.CTkFrame(bottom_row, fg_color="transparent", width=290)
        insights_col.pack(side="left", fill="y", padx=4)
        insights_col.pack_propagate(False)
        self.build_dashboard_quick_insights_card(insights_col)

        # Column 3: Motivation Card
        motivation_col = ctk.CTkFrame(bottom_row, fg_color="transparent", width=290)
        motivation_col.pack(side="left", fill="y", padx=4)
        motivation_col.pack_propagate(False)
        self.build_dashboard_motivation_card(motivation_col)

    def create_dashboard_kpi_card(self, parent, icon, title, value, color, icon_bg):
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=16,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card_content = ctk.CTkFrame(card, fg_color="transparent")
        card_content.pack(fill="both", expand=True, padx=16, pady=16)

        icon_badge = ctk.CTkLabel(
            card_content,
            text=icon,
            font=("Arial", 20),
            fg_color=icon_bg,
            width=46,
            height=46,
            corner_radius=23,
        )
        icon_badge.pack(side="left", padx=(0, 14))

        text_col = ctk.CTkFrame(card_content, fg_color="transparent")
        text_col.pack(side="left", fill="both", expand=True)

        title_lbl = ctk.CTkLabel(
            text_col,
            text=title,
            font=("Arial", 12),
            text_color=MUTED_TEXT,
        )
        title_lbl.pack(anchor="w")

        val_lbl = ctk.CTkLabel(
            text_col,
            text=value,
            font=("Arial", 22, "bold"),
            text_color=color,
        )
        val_lbl.pack(anchor="w", pady=(2, 0))

        return card

    def build_dashboard_today_meals_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.pack(fill="both", expand=True)

        # Header with Goal Badge
        header_row = ctk.CTkFrame(card, fg_color="transparent")
        header_row.pack(fill="x", padx=18, pady=(16, 12))

        title = ctk.CTkLabel(
            header_row,
            text="🍴  Today's Meals",
            font=("Arial", 18, "bold"),
            text_color=TEXT_COLOR,
        )
        title.pack(side="left")

        goal_pill = ctk.CTkLabel(
            header_row,
            text="Goal: 3 meals / day",
            font=("Arial", 11, "bold"),
            text_color=MUTED_TEXT,
            fg_color=CARD_HOVER,
            corner_radius=10,
            padx=10,
            pady=4,
        )
        goal_pill.pack(side="right")

        # 3 Sub-Cards for Meals
        meals_row = ctk.CTkFrame(card, fg_color="transparent")
        meals_row.pack(fill="both", expand=True, padx=12, pady=(0, 14))

        meal_items = [
            ("Breakfast", "☀️", "Breakfast", self.meal_prices.get("Breakfast", 30), "#382315"),
            ("Lunch", "🍛", "Lunch", self.meal_prices.get("Lunch", 50), "#133132"),
            ("Dinner", "🌙", "Dinner", self.meal_prices.get("Dinner", 30), "#271B3D"),
        ]

        is_sun_today = is_sunday()

        for meal_key, icon, label, price, tint_bg in meal_items:
            sub_card = ctk.CTkFrame(
                meals_row,
                fg_color=tint_bg,
                corner_radius=14,
                border_width=1,
                border_color=BORDER_COLOR,
            )
            sub_card.pack(side="left", fill="both", expand=True, padx=6)

            # Icon
            m_icon = ctk.CTkLabel(sub_card, text=icon, font=("Arial", 28))
            m_icon.pack(pady=(16, 4))

            # Meal Name
            m_name = ctk.CTkLabel(
                sub_card,
                text=label,
                font=("Arial", 15, "bold"),
                text_color=TEXT_COLOR,
            )
            m_name.pack()

            # Price Label
            if meal_key == "Dinner" and is_sun_today:
                price_text = "Outside"
            else:
                price_text = f"₹{price}"

            m_price = ctk.CTkLabel(
                sub_card,
                text=price_text,
                font=("Arial", 12),
                text_color=MUTED_TEXT,
            )
            m_price.pack(pady=(2, 10))

            is_done = self.today_meal_states.get(meal_key, 0) == 1

            # Completed Toggle Button
            toggle_btn = ctk.CTkButton(
                sub_card,
                text="✓ Completed" if is_done else "Mark Completed",
                command=lambda mk=meal_key: self.toggle_today_meal(mk),
                fg_color=SUCCESS_COLOR if is_done else CARD_HOVER,
                hover_color="#16A34A" if is_done else "#2D224E",
                font=("Arial", 11, "bold"),
                corner_radius=10,
                height=32,
            )
            toggle_btn.pack(fill="x", padx=12, pady=(0, 14))

    def toggle_today_meal(self, meal_key):
        new_state = 0 if self.today_meal_states.get(meal_key, 0) == 1 else 1
        self.today_meal_states[meal_key] = new_state
        self.bill = calculate_bill(
            self.today_meal_states,
            self.meal_prices,
            self.today_outside_dinner,
        )
        save_meal_record(
            self.cursor,
            self.connection,
            self.today_meal_states,
            self.bill,
            self.today_outside_dinner,
        )
        self.refresh_all_dashboard_views(get_today_string())

    def build_dashboard_calendar_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.pack(fill="both", expand=True)

        # Header with < Month Year >
        cal_header = ctk.CTkFrame(card, fg_color="transparent")
        cal_header.pack(fill="x", padx=14, pady=(14, 8))

        prev_btn = ctk.CTkButton(
            cal_header,
            text="‹",
            width=28,
            height=28,
            fg_color=CARD_HOVER,
            hover_color=PRIMARY_HOVER,
            font=("Arial", 16, "bold"),
            corner_radius=8,
            command=lambda: self.change_cal_month(-1),
        )
        prev_btn.pack(side="left")

        month_title = datetime(self.cal_year, self.cal_month, 1).strftime("%B %Y")
        cal_title = ctk.CTkLabel(
            cal_header,
            text=month_title,
            font=("Arial", 14, "bold"),
            text_color=TEXT_COLOR,
        )
        cal_title.pack(side="left", expand=True)

        next_btn = ctk.CTkButton(
            cal_header,
            text="›",
            width=28,
            height=28,
            fg_color=CARD_HOVER,
            hover_color=PRIMARY_HOVER,
            font=("Arial", 16, "bold"),
            corner_radius=8,
            command=lambda: self.change_cal_month(1),
        )
        next_btn.pack(side="right")

        # Weekday headers (Sun - Sat)
        weekdays_row = ctk.CTkFrame(card, fg_color="transparent")
        weekdays_row.pack(fill="x", padx=12, pady=(0, 4))

        for wd in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
            wd_lbl = ctk.CTkLabel(
                weekdays_row,
                text=wd,
                font=("Arial", 10, "bold"),
                text_color=MUTED_TEXT,
                width=32,
            )
            wd_lbl.pack(side="left", expand=True)

        # Fetch records for this calendar month
        target_cal_date = date(self.cal_year, self.cal_month, 1)
        summary = fetch_monthly_summary(self.cursor, len(self.meal_prices), current_date=target_cal_date)
        recorded_days = get_recorded_days(summary["records"])
        today = date.today()

        # Build Sunday-first calendar weeks
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.cal_year, self.cal_month)

        grid_frame = ctk.CTkFrame(card, fg_color="transparent")
        grid_frame.pack(fill="x", padx=12, pady=(0, 8))

        for week in month_days:
            w_row = ctk.CTkFrame(grid_frame, fg_color="transparent")
            w_row.pack(fill="x", pady=1)

            for d in week:
                if d == 0:
                    sp = ctk.CTkLabel(w_row, text="", width=32, height=26)
                    sp.pack(side="left", expand=True, padx=1)
                else:
                    is_rec = d in recorded_days
                    is_tdy = (d == today.day and self.cal_month == today.month and self.cal_year == today.year)

                    if is_tdy:
                        bg_c = PRIMARY_COLOR
                        txt_c = TEXT_COLOR
                    elif is_rec:
                        bg_c = SUCCESS_COLOR
                        txt_c = TEXT_COLOR
                    else:
                        bg_c = "transparent"
                        txt_c = MUTED_TEXT

                    d_btn = ctk.CTkButton(
                        w_row,
                        text=str(d),
                        width=32,
                        height=26,
                        fg_color=bg_c,
                        hover_color=PRIMARY_HOVER,
                        corner_radius=8,
                        font=("Arial", 11, "bold"),
                        text_color=txt_c,
                        command=lambda day_num=d: self.open_date_editor_for_month_day(day_num),
                    )
                    d_btn.pack(side="left", expand=True, padx=1)

        # Legend
        legend_row = ctk.CTkFrame(card, fg_color="transparent")
        legend_row.pack(fill="x", padx=14, pady=(4, 12))

        rec_dot = ctk.CTkLabel(
            legend_row,
            text="● Recorded",
            font=("Arial", 10, "bold"),
            text_color=SUCCESS_COLOR,
        )
        rec_dot.pack(side="left", padx=(6, 0))

        today_dot = ctk.CTkLabel(
            legend_row,
            text="● Today",
            font=("Arial", 10, "bold"),
            text_color=PRIMARY_COLOR,
        )
        today_dot.pack(side="right", padx=(0, 6))

    def change_cal_month(self, delta):
        self.cal_month += delta
        if self.cal_month > 12:
            self.cal_month = 1
            self.cal_year += 1
        elif self.cal_month < 1:
            self.cal_month = 12
            self.cal_year -= 1
        self.show_view("dashboard", force_refresh=True)

    def open_date_editor_for_month_day(self, day_num):
        target_date = date(self.cal_year, self.cal_month, day_num)
        self.open_date_editor(target_date.strftime(DATE_FORMAT))

    def build_dashboard_month_summary_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.pack(fill="both", expand=True)

        target_date = date(self.cal_year, self.cal_month, 1)
        summary = fetch_monthly_summary(self.cursor, len(self.meal_prices), current_date=target_date)

        # Header
        header_row = ctk.CTkFrame(card, fg_color="transparent")
        header_row.pack(fill="x", padx=14, pady=(14, 6))

        title = ctk.CTkLabel(
            header_row,
            text="👑  Monthly Summary",
            font=("Arial", 15, "bold"),
            text_color=TEXT_COLOR,
        )
        title.pack(side="left")

        month_tag = ctk.CTkLabel(
            header_row,
            text=target_date.strftime("%b %Y"),
            font=("Arial", 11, "bold"),
            text_color=MUTED_TEXT,
            fg_color=CARD_HOVER,
            corner_radius=8,
            padx=8,
            pady=3,
        )
        month_tag.pack(side="right")

        # Stats Rows
        stats_list = [
            ("🥗", "Total Spent", f"₹{summary['total_spent']}"),
            ("💧", "Average / Day", f"₹{summary['average_spending']:.2f}"),
            ("🍔", "Meals Completed", f"{summary['total_meals']} / {summary['total_possible_meals']}"),
            ("📥", "Days Recorded", str(summary["days_recorded"])),
        ]

        for icon, label, val in stats_list:
            s_row = ctk.CTkFrame(card, fg_color=CARD_HOVER, corner_radius=10)
            s_row.pack(fill="x", padx=12, pady=3)

            i_lbl = ctk.CTkLabel(s_row, text=icon, font=("Arial", 13))
            i_lbl.pack(side="left", padx=(10, 4), pady=6)

            l_lbl = ctk.CTkLabel(s_row, text=label, font=("Arial", 11), text_color=MUTED_TEXT)
            l_lbl.pack(side="left")

            v_lbl = ctk.CTkLabel(s_row, text=val, font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
            v_lbl.pack(side="right", padx=10)

        # Mini Highlights Row
        high_low_row = ctk.CTkFrame(card, fg_color="transparent")
        high_low_row.pack(fill="x", padx=10, pady=(6, 12))

        highest_amt = f"₹{summary['highest_day'][4]}" if summary["highest_day"] else "₹0"
        highest_date = summary["highest_day"][0] if summary["highest_day"] else "—"

        lowest_amt = f"₹{summary['lowest_day'][4]}" if summary["lowest_day"] else "₹0"
        lowest_date = summary["lowest_day"][0] if summary["lowest_day"] else "—"

        # Highest Card
        h_card = ctk.CTkFrame(high_low_row, fg_color=CARD_HOVER, corner_radius=10, border_width=1, border_color=SUCCESS_COLOR)
        h_card.pack(side="left", fill="both", expand=True, padx=2)
        ctk.CTkLabel(h_card, text="▲ Highest Spend", font=("Arial", 9, "bold"), text_color=SUCCESS_COLOR).pack(anchor="w", padx=8, pady=(6, 1))
        ctk.CTkLabel(h_card, text=highest_amt, font=("Arial", 13, "bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=8)
        ctk.CTkLabel(h_card, text=highest_date, font=("Arial", 9), text_color=MUTED_TEXT).pack(anchor="w", padx=8, pady=(0, 6))

        # Lowest Card
        l_card = ctk.CTkFrame(high_low_row, fg_color=CARD_HOVER, corner_radius=10, border_width=1, border_color=DANGER_COLOR)
        l_card.pack(side="left", fill="both", expand=True, padx=2)
        ctk.CTkLabel(l_card, text="▼ Lowest Spend", font=("Arial", 9, "bold"), text_color=DANGER_COLOR).pack(anchor="w", padx=8, pady=(6, 1))
        ctk.CTkLabel(l_card, text=lowest_amt, font=("Arial", 13, "bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=8)
        ctk.CTkLabel(l_card, text=lowest_date, font=("Arial", 9), text_color=MUTED_TEXT).pack(anchor="w", padx=8, pady=(0, 6))

    def build_dashboard_spending_trend_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.pack(fill="both", expand=True)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 4))

        title = ctk.CTkLabel(header, text="🔀  Spending Trend", font=("Arial", 16, "bold"), text_color=TEXT_COLOR)
        title.pack(side="left")

        summary = fetch_monthly_summary(self.cursor, len(self.meal_prices))
        trend_records = get_recent_spending_records(summary["records"], limit=6)

        chart_frame = ctk.CTkFrame(card, fg_color="transparent")
        chart_frame.pack(fill="both", expand=True, padx=14, pady=(6, 14))

        if not trend_records:
            empty_lbl = ctk.CTkLabel(chart_frame, text="Log your meals to view recent spending trends.", font=("Arial", 12), text_color=MUTED_TEXT)
            empty_lbl.pack(pady=30)
            return

        max_bill = max(r["bill"] for r in trend_records) or 1
        bar_colors = [PRIMARY_COLOR, "#2DD4BF", WARNING_COLOR, SUCCESS_COLOR, "#F97316", "#EC4899"]

        bars_row = ctk.CTkFrame(chart_frame, fg_color="transparent")
        bars_row.pack(fill="both", expand=True)

        for idx, rec in enumerate(trend_records):
            col = ctk.CTkFrame(bars_row, fg_color="transparent")
            col.pack(side="left", fill="both", expand=True, padx=4)

            amt_lbl = ctk.CTkLabel(col, text=f"₹{rec['bill']}", font=("Arial", 11, "bold"), text_color=TEXT_COLOR)
            amt_lbl.pack(side="top", pady=(0, 4))

            bar_h = max(24, int((rec["bill"] / max_bill) * 90))
            bar = ctk.CTkFrame(
                col,
                width=24,
                height=bar_h,
                fg_color=bar_colors[idx % len(bar_colors)],
                corner_radius=8,
            )
            bar.pack(side="top", pady=2)
            bar.pack_propagate(False)

            d_lbl = ctk.CTkLabel(col, text=rec["date"][:5], font=("Arial", 10), text_color=MUTED_TEXT)
            d_lbl.pack(side="top", pady=(4, 0))

    def build_dashboard_quick_insights_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.pack(fill="both", expand=True)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(14, 8))

        title = ctk.CTkLabel(header, text="✨  Quick Insights", font=("Arial", 15, "bold"), text_color=TEXT_COLOR)
        title.pack(side="left")

        summary = fetch_monthly_summary(self.cursor, len(self.meal_prices))
        insights = get_quick_insights(summary)
        bullet_icons = ["🍃", "🎯", "💧", "💖"]

        for idx, ins in enumerate(insights):
            row = ctk.CTkFrame(card, fg_color=CARD_HOVER, corner_radius=10)
            row.pack(fill="x", padx=12, pady=3)

            i_lbl = ctk.CTkLabel(row, text=bullet_icons[idx % len(bullet_icons)], font=("Arial", 12))
            i_lbl.pack(side="left", padx=(10, 6), pady=8)

            t_lbl = ctk.CTkLabel(row, text=ins, font=("Arial", 11), text_color=TEXT_COLOR, justify="left", wraplength=220)
            t_lbl.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=8)

    def build_dashboard_motivation_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.pack(fill="both", expand=True)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(14, 4))

        title = ctk.CTkLabel(header, text="🍃  Motivation", font=("Arial", 15, "bold"), text_color=TEXT_COLOR)
        title.pack(side="left")

        summary = fetch_monthly_summary(self.cursor, len(self.meal_prices))
        msg = get_motivation_message(summary)

        quote_frame = ctk.CTkFrame(
            card,
            fg_color="#2D1A10",
            corner_radius=12,
            border_width=1,
            border_color="#78350F",
        )
        quote_frame.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        quote_label = ctk.CTkLabel(
            quote_frame,
            text=f'"{msg}"',
            font=("Arial", 13, "italic"),
            text_color="#FDE68A",
            justify="center",
            wraplength=230,
        )
        quote_label.pack(padx=14, pady=16)

        footer_lbl = ctk.CTkLabel(
            card,
            text="Healthy meals today, a stronger you tomorrow!",
            font=("Arial", 10),
            text_color=MUTED_TEXT,
        )
        footer_lbl.pack(pady=(0, 10))

    # -------------------------------------------------------------
    # VIEW 2: TODAY'S MEALS FOCUSED TRACKER
    # -------------------------------------------------------------

    def render_today_meals_view(self):
        self.active_view_frame = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
        )
        self.active_view_frame.pack(fill="both", expand=True)

        header_frame = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=6, pady=(6, 14))

        ctk.CTkLabel(header_frame, text="🍽️  Today's Meal Tracker", font=("Arial", 26, "bold"), text_color=TEXT_COLOR).pack(anchor="w")
        ctk.CTkLabel(header_frame, text=f"Record your completed meals for {get_display_date()}.", font=("Arial", 13), text_color=MUTED_TEXT).pack(anchor="w", pady=(2, 0))

        # Main Meal Cards Container
        cards_row = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        cards_row.pack(fill="x", padx=2, pady=(0, 14))

        is_sun_today = is_sunday()
        outside_entry: ctk.CTkEntry | None = None

        for meal_name, price in self.meal_prices.items():
            card = ctk.CTkFrame(cards_row, fg_color=CARD_COLOR, corner_radius=18, border_width=1, border_color=BORDER_COLOR)
            card.pack(side="left", fill="both", expand=True, padx=6)

            ctk.CTkLabel(card, text=MEAL_ICONS.get(meal_name, "🍽️"), font=("Arial", 36)).pack(pady=(20, 6))
            ctk.CTkLabel(card, text=meal_name, font=("Arial", 18, "bold"), text_color=TEXT_COLOR).pack()

            if meal_name == "Dinner" and is_sun_today:
                price_str = "Sunday Outside Dinner"
            else:
                price_str = f"Standard Rate: ₹{price}"

            ctk.CTkLabel(card, text=price_str, font=("Arial", 12), text_color=MUTED_TEXT).pack(pady=(2, 12))

            is_checked = self.today_meal_states.get(meal_name, 0) == 1

            if meal_name == "Dinner" and is_sun_today:
                oe_frame = ctk.CTkFrame(card, fg_color="transparent")
                oe_frame.pack(pady=(0, 10))
                ctk.CTkLabel(oe_frame, text="Amount: ₹", font=("Arial", 12, "bold"), text_color=WARNING_COLOR).pack(side="left")
                oe_entry = ctk.CTkEntry(oe_frame, width=90, height=30)
                oe_entry.pack(side="left")
                if self.today_outside_dinner > 0:
                    oe_entry.insert(0, str(self.today_outside_dinner))
                outside_entry = oe_entry

            t_btn = ctk.CTkButton(
                card,
                text="✓ Completed" if is_checked else "Mark as Completed",
                command=lambda mn=meal_name: self.toggle_today_meal_advanced(mn, outside_entry),
                fg_color=SUCCESS_COLOR if is_checked else PRIMARY_COLOR,
                hover_color="#16A34A" if is_checked else PRIMARY_HOVER,
                font=("Arial", 12, "bold"),
                height=36,
                corner_radius=10,
            )
            t_btn.pack(fill="x", padx=18, pady=(0, 20))

        # Today's Total Box
        summary_card = ctk.CTkFrame(self.active_view_frame, fg_color=CARD_COLOR, corner_radius=18, border_width=1, border_color=BORDER_COLOR)
        summary_card.pack(fill="x", padx=6, pady=10)

        s_row = ctk.CTkFrame(summary_card, fg_color="transparent")
        s_row.pack(fill="x", padx=24, pady=18)

        ctk.CTkLabel(s_row, text="Today's Calculated Total:", font=("Arial", 15), text_color=MUTED_TEXT).pack(side="left")
        ctk.CTkLabel(s_row, text=f"₹{self.bill}", font=("Arial", 26, "bold"), text_color=WARNING_COLOR).pack(side="left", padx=(10, 0))

        save_btn = ctk.CTkButton(
            s_row,
            text="💾 Save Record to Database",
            command=lambda: self.save_today_meals_explicit(outside_entry),
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            font=("Arial", 13, "bold"),
            height=38,
            corner_radius=10,
        )
        save_btn.pack(side="right")

    def toggle_today_meal_advanced(self, meal_name, outside_entry):
        new_val = 0 if self.today_meal_states.get(meal_name, 0) == 1 else 1
        self.today_meal_states[meal_name] = new_val
        if outside_entry and outside_entry.winfo_exists():
            self.today_outside_dinner = parse_outside_dinner_amount(outside_entry.get())
        self.bill = calculate_bill(self.today_meal_states, self.meal_prices, self.today_outside_dinner)
        save_meal_record(self.cursor, self.connection, self.today_meal_states, self.bill, self.today_outside_dinner)
        self.show_view("meals", force_refresh=True)

    def save_today_meals_explicit(self, outside_entry):
        if outside_entry and outside_entry.winfo_exists():
            self.today_outside_dinner = parse_outside_dinner_amount(outside_entry.get())
        self.bill = calculate_bill(self.today_meal_states, self.meal_prices, self.today_outside_dinner)
        save_meal_record(self.cursor, self.connection, self.today_meal_states, self.bill, self.today_outside_dinner)
        self.refresh_all_dashboard_views(get_today_string())

    # -------------------------------------------------------------
    # VIEW 3: MEAL HISTORY & AUDIT LOG
    # -------------------------------------------------------------

    def render_history_view(self):
        self.active_view_frame = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
        )
        self.active_view_frame.pack(fill="both", expand=True)

        header_row = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=6, pady=(6, 12))

        title_col = ctk.CTkFrame(header_row, fg_color="transparent")
        title_col.pack(side="left")

        ctk.CTkLabel(title_col, text="📅  Meal History & Past-Date Editor", font=("Arial", 24, "bold"), text_color=TEXT_COLOR).pack(anchor="w")
        ctk.CTkLabel(title_col, text="View historical meal records, edit past days, or log missing dates.", font=("Arial", 12), text_color=MUTED_TEXT).pack(anchor="w", pady=(2, 0))

        add_past_btn = ctk.CTkButton(
            header_row,
            text="+ Log Past Date",
            command=lambda: self.open_date_editor(None),
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            font=("Arial", 13, "bold"),
            height=36,
            corner_radius=10,
        )
        add_past_btn.pack(side="right")

        # Table Card Container
        table_card = ctk.CTkFrame(self.active_view_frame, fg_color=CARD_COLOR, corner_radius=18, border_width=1, border_color=BORDER_COLOR)
        table_card.pack(fill="both", expand=True, padx=4, pady=6)

        # Header Columns
        cols_row = ctk.CTkFrame(table_card, fg_color="transparent")
        cols_row.pack(fill="x", padx=18, pady=(16, 6))

        ctk.CTkLabel(cols_row, text="Date", font=("Arial", 12, "bold"), text_color=MUTED_TEXT, width=140, anchor="w").pack(side="left")
        ctk.CTkLabel(cols_row, text="Meals Completed", font=("Arial", 12, "bold"), text_color=MUTED_TEXT, width=120, anchor="w").pack(side="left")
        ctk.CTkLabel(cols_row, text="Items Taken", font=("Arial", 12, "bold"), text_color=MUTED_TEXT, anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(cols_row, text="Bill", font=("Arial", 12, "bold"), text_color=MUTED_TEXT, width=90, anchor="e").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(cols_row, text="Action", font=("Arial", 12, "bold"), text_color=MUTED_TEXT, width=80, anchor="center").pack(side="right")

        records = fetch_history_records(self.cursor)

        if not records:
            empty_lbl = ctk.CTkLabel(table_card, text="No meal records found in history yet.", font=("Arial", 13), text_color=MUTED_TEXT)
            empty_lbl.pack(pady=40)
            return

        for record in records:
            date_val, bf, lu, dn, out_dn, bill_val = record
            completed = bf + lu + dn

            row = ctk.CTkFrame(table_card, fg_color=CARD_HOVER, corner_radius=12)
            row.pack(fill="x", padx=14, pady=3)

            is_sun = is_sunday(date_val)
            date_str = date_val + (" (Sun)" if is_sun else "")

            d_lbl = ctk.CTkLabel(row, text=date_str, font=("Arial", 13, "bold"), text_color=WARNING_COLOR if is_sun else TEXT_COLOR, width=140, anchor="w")
            d_lbl.pack(side="left", padx=(12, 0), pady=10)

            m_lbl = ctk.CTkLabel(row, text=f"{completed} / 3", font=("Arial", 12), text_color=SUCCESS_COLOR if completed == 3 else MUTED_TEXT, width=120, anchor="w")
            m_lbl.pack(side="left")

            items = []
            if bf: items.append("Breakfast")
            if lu: items.append("Lunch")
            if dn:
                if is_sun and out_dn > 0:
                    items.append(f"Outside Dinner (₹{out_dn})")
                else:
                    items.append("Dinner")
            items_str = ", ".join(items) if items else "None"

            i_lbl = ctk.CTkLabel(row, text=items_str, font=("Arial", 11), text_color=MUTED_TEXT, anchor="w")
            i_lbl.pack(side="left", fill="x", expand=True)

            b_lbl = ctk.CTkLabel(row, text=f"₹{bill_val}", font=("Arial", 13, "bold"), text_color=TEXT_COLOR, width=90, anchor="e")
            b_lbl.pack(side="left", padx=(0, 10))

            edit_btn = ctk.CTkButton(
                row,
                text="✏️ Edit",
                command=lambda d=date_val: self.open_date_editor(d),
                fg_color=PRIMARY_COLOR,
                hover_color=PRIMARY_HOVER,
                font=("Arial", 11, "bold"),
                width=70,
                height=28,
                corner_radius=8,
            )
            edit_btn.pack(side="right", padx=(0, 10), pady=6)

        total_spent = sum(r[5] for r in records)
        footer_bar = ctk.CTkFrame(table_card, fg_color="transparent")
        footer_bar.pack(fill="x", padx=18, pady=(12, 16))

        ctk.CTkLabel(footer_bar, text=f"Total Cumulative Spend: ₹{total_spent} across {len(records)} recorded days", font=("Arial", 13, "bold"), text_color=TEXT_COLOR).pack(side="left")

    # -------------------------------------------------------------
    # VIEW 4: MONTHLY SUMMARY & BREAKDOWN
    # -------------------------------------------------------------

    def render_monthly_summary_view(self):
        self.active_view_frame = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
        )
        self.active_view_frame.pack(fill="both", expand=True)

        target_date = date(self.cal_year, self.cal_month, 1)
        summary = fetch_monthly_summary(self.cursor, len(self.meal_prices), current_date=target_date)

        header_row = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=6, pady=(6, 14))

        title_col = ctk.CTkFrame(header_row, fg_color="transparent")
        title_col.pack(side="left")

        ctk.CTkLabel(title_col, text="📊  Monthly Financial Summary", font=("Arial", 24, "bold"), text_color=TEXT_COLOR).pack(anchor="w")
        ctk.CTkLabel(title_col, text=f"Review total spending and daily breakdown for {target_date.strftime('%B %Y')}.", font=("Arial", 12), text_color=MUTED_TEXT).pack(anchor="w", pady=(2, 0))

        # Month Switcher Controls
        switcher = ctk.CTkFrame(header_row, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        switcher.pack(side="right")

        ctk.CTkButton(switcher, text="‹", width=30, height=30, fg_color="transparent", hover_color=PRIMARY_HOVER, command=lambda: self.change_cal_month(-1)).pack(side="left")
        ctk.CTkLabel(switcher, text=target_date.strftime("%B %Y"), font=("Arial", 13, "bold"), text_color=TEXT_COLOR).pack(side="left", padx=10)
        ctk.CTkButton(switcher, text="›", width=30, height=30, fg_color="transparent", hover_color=PRIMARY_HOVER, command=lambda: self.change_cal_month(1)).pack(side="left")

        # 4 Metric Cards Row
        cards_row = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        cards_row.pack(fill="x", padx=2, pady=(0, 14))

        self.create_dashboard_kpi_card(cards_row, "💰", "Total Spend", f"₹{summary['total_spent']}", "#8B5CF6", "#26174D").pack(side="left", fill="both", expand=True, padx=4)
        self.create_dashboard_kpi_card(cards_row, "📈", "Daily Average", f"₹{summary['average_spending']:.2f}", "#10B981", "#0B3728").pack(side="left", fill="both", expand=True, padx=4)
        self.create_dashboard_kpi_card(cards_row, "🍽️", "Meals Completed", f"{summary['total_meals']} / {summary['total_possible_meals']}", "#F59E0B", "#3F270B").pack(side="left", fill="both", expand=True, padx=4)
        self.create_dashboard_kpi_card(cards_row, "🗓️", "Days Logged", f"{summary['days_recorded']} days", "#EC4899", "#401228").pack(side="left", fill="both", expand=True, padx=4)

        # Day-by-Day Table Card
        table_card = ctk.CTkFrame(self.active_view_frame, fg_color=CARD_COLOR, corner_radius=18, border_width=1, border_color=BORDER_COLOR)
        table_card.pack(fill="both", expand=True, padx=4, pady=6)

        table_hdr = ctk.CTkFrame(table_card, fg_color="transparent")
        table_hdr.pack(fill="x", padx=18, pady=(14, 8))
        ctk.CTkLabel(table_hdr, text=f"Daily Records for {target_date.strftime('%B %Y')}", font=("Arial", 16, "bold"), text_color=TEXT_COLOR).pack(side="left")

        if not summary["records"]:
            ctk.CTkLabel(table_card, text="No meal records found for this month.", font=("Arial", 12), text_color=MUTED_TEXT).pack(pady=30)
            return

        for rec in summary["records"]:
            d_val, bf, lu, dn, b_val = rec
            row = ctk.CTkFrame(table_card, fg_color=CARD_HOVER, corner_radius=10)
            row.pack(fill="x", padx=14, pady=3)

            is_sun = is_sunday(d_val)
            d_text = d_val + (" (Sun)" if is_sun else "")

            ctk.CTkLabel(row, text=d_text, font=("Arial", 12, "bold"), text_color=WARNING_COLOR if is_sun else TEXT_COLOR, width=140, anchor="w").pack(side="left", padx=(12, 0), pady=8)
            ctk.CTkLabel(row, text=f"Meals: {bf + lu + dn} / 3", font=("Arial", 12), text_color=MUTED_TEXT, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=f"Bill: ₹{b_val}", font=("Arial", 13, "bold"), text_color=TEXT_COLOR).pack(side="left", padx=10)

            ctk.CTkButton(
                row,
                text="✏️ Edit",
                command=lambda d=d_val: self.open_date_editor(d),
                fg_color=PRIMARY_COLOR,
                hover_color=PRIMARY_HOVER,
                font=("Arial", 11, "bold"),
                width=65,
                height=26,
                corner_radius=8,
            ).pack(side="right", padx=10, pady=4)

    # -------------------------------------------------------------
    # VIEW 5: ANALYTICS
    # -------------------------------------------------------------

    def render_analytics_view(self):
        self.active_view_frame = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
        )
        self.active_view_frame.pack(fill="both", expand=True)

        header_frame = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=6, pady=(6, 14))

        ctk.CTkLabel(header_frame, text="📈  Spending & Meal Analytics", font=("Arial", 24, "bold"), text_color=TEXT_COLOR).pack(anchor="w")
        ctk.CTkLabel(header_frame, text="Comprehensive distribution and spending patterns for this month.", font=("Arial", 12), text_color=MUTED_TEXT).pack(anchor="w", pady=(2, 0))

        dist = fetch_meal_type_distribution(self.cursor, meal_prices=self.meal_prices)

        # 3 Category Breakdown Cards
        cat_row = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        cat_row.pack(fill="x", padx=2, pady=(0, 14))

        self.create_analytics_cat_card(cat_row, "🍳 Breakfast", dist["breakfast_count"], dist["breakfast_spend"], "#F59E0B").pack(side="left", fill="both", expand=True, padx=4)
        self.create_analytics_cat_card(cat_row, "🍛 Lunch", dist["lunch_count"], dist["lunch_spend"], "#10B981").pack(side="left", fill="both", expand=True, padx=4)
        self.create_analytics_cat_card(cat_row, "🌙 Dinner", dist["dinner_count"], dist["dinner_spend"], "#8B5CF6").pack(side="left", fill="both", expand=True, padx=4)

        # Detailed Breakdown & Proportions Card
        prop_card = ctk.CTkFrame(self.active_view_frame, fg_color=CARD_COLOR, corner_radius=18, border_width=1, border_color=BORDER_COLOR)
        prop_card.pack(fill="x", padx=4, pady=6)

        ctk.CTkLabel(prop_card, text="Spending Share by Meal Type", font=("Arial", 16, "bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=20, pady=(16, 10))

        tot = dist["total_spend"] or 1
        bf_pct = (dist["breakfast_spend"] / tot) * 100
        lu_pct = (dist["lunch_spend"] / tot) * 100
        dn_pct = (dist["dinner_spend"] / tot) * 100

        self.create_progress_bar_row(prop_card, "Breakfast Spending", f"₹{dist['breakfast_spend']} ({bf_pct:.1f}%)", bf_pct / 100, "#F59E0B")
        self.create_progress_bar_row(prop_card, "Lunch Spending", f"₹{dist['lunch_spend']} ({lu_pct:.1f}%)", lu_pct / 100, "#10B981")
        self.create_progress_bar_row(prop_card, "Dinner Spending (incl. Outside)", f"₹{dist['dinner_spend']} ({dn_pct:.1f}%)", dn_pct / 100, "#8B5CF6")

        # Summary Footnote
        summary_row = ctk.CTkFrame(prop_card, fg_color=CARD_HOVER, corner_radius=12)
        summary_row.pack(fill="x", padx=18, pady=(14, 18))

        ctk.CTkLabel(summary_row, text=f"Total Tracked Month Spend: ₹{dist['total_spend']} across {dist['total_meals']} completed meals", font=("Arial", 13, "bold"), text_color=TEXT_COLOR).pack(padx=16, pady=12)

    def create_analytics_cat_card(self, parent, title, count, spend, accent_color):
        card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=16, border_width=1, border_color=BORDER_COLOR)
        c_frame = ctk.CTkFrame(card, fg_color="transparent")
        c_frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(c_frame, text=title, font=("Arial", 16, "bold"), text_color=TEXT_COLOR).pack(anchor="w")
        ctk.CTkLabel(c_frame, text=f"{count} meals consumed", font=("Arial", 12), text_color=MUTED_TEXT).pack(anchor="w", pady=(2, 8))
        ctk.CTkLabel(c_frame, text=f"₹{spend}", font=("Arial", 24, "bold"), text_color=accent_color).pack(anchor="w")

        return card

    def create_progress_bar_row(self, parent, label, val_text, progress_val, color):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=6)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", pady=(0, 3))

        ctk.CTkLabel(top, text=label, font=("Arial", 12, "bold"), text_color=TEXT_COLOR).pack(side="left")
        ctk.CTkLabel(top, text=val_text, font=("Arial", 12), text_color=MUTED_TEXT).pack(side="right")

        pb = ctk.CTkProgressBar(row, height=8, corner_radius=4, fg_color=CARD_HOVER, progress_color=color)
        pb.pack(fill="x")
        pb.set(progress_val)

    # -------------------------------------------------------------
    # VIEW 6: SETTINGS
    # -------------------------------------------------------------

    def render_settings_view(self):
        self.active_view_frame = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
        )
        self.active_view_frame.pack(fill="both", expand=True)

        header_frame = ctk.CTkFrame(self.active_view_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=6, pady=(6, 14))

        ctk.CTkLabel(header_frame, text="⚙️  Application Settings", font=("Arial", 24, "bold"), text_color=TEXT_COLOR).pack(anchor="w")
        ctk.CTkLabel(header_frame, text="Customize user preferences and meal pricing rates.", font=("Arial", 12), text_color=MUTED_TEXT).pack(anchor="w", pady=(2, 0))

        card = ctk.CTkFrame(self.active_view_frame, fg_color=CARD_COLOR, corner_radius=18, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", padx=4, pady=6)

        # Profile Settings
        ctk.CTkLabel(card, text="Profile Settings", font=("Arial", 16, "bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=20, pady=(18, 10))

        name_row = ctk.CTkFrame(card, fg_color="transparent")
        name_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(name_row, text="Display Name:", font=("Arial", 13), text_color=MUTED_TEXT, width=140, anchor="w").pack(side="left")
        name_entry = ctk.CTkEntry(name_row, width=200)
        name_entry.pack(side="left")
        name_entry.insert(0, self.user_name)

        divider = ctk.CTkFrame(card, height=1, fg_color=BORDER_COLOR)
        divider.pack(fill="x", padx=20, pady=16)

        # Meal Pricing Configuration
        ctk.CTkLabel(card, text="Standard Meal Pricing Rates (₹)", font=("Arial", 16, "bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=20, pady=(0, 10))

        def create_rate_row(label, current_val):
            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(r, text=label, font=("Arial", 13), text_color=MUTED_TEXT, width=140, anchor="w").pack(side="left")
            e = ctk.CTkEntry(r, width=100)
            e.pack(side="left")
            e.insert(0, str(current_val))
            return e

        bf_entry = create_rate_row("Breakfast (₹):", self.meal_prices.get("Breakfast", 30))
        lu_entry = create_rate_row("Lunch (₹):", self.meal_prices.get("Lunch", 50))
        dn_entry = create_rate_row("Dinner (₹):", self.meal_prices.get("Dinner", 30))

        divider2 = ctk.CTkFrame(card, height=1, fg_color=BORDER_COLOR)
        divider2.pack(fill="x", padx=20, pady=16)

        # Smart Meal Reminders & Notifications
        notif_hdr_row = ctk.CTkFrame(card, fg_color="transparent")
        notif_hdr_row.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(
            notif_hdr_row,
            text="🔔 Smart Meal Reminders & Notifications",
            font=("Arial", 16, "bold"),
            text_color=TEXT_COLOR,
        ).pack(side="left")

        # Master Toggle Switch
        is_notif_on = str(self.notification_settings.get("notifications_enabled", "1")) == "1"
        notif_enabled_var = ctk.BooleanVar(value=is_notif_on)

        notif_switch = ctk.CTkSwitch(
            notif_hdr_row,
            text="Enable Reminders",
            variable=notif_enabled_var,
            font=("Arial", 12, "bold"),
            progress_color=PRIMARY_COLOR,
            text_color=TEXT_COLOR,
        )
        notif_switch.pack(side="right")

        notif_sub_lbl = ctk.CTkLabel(
            card,
            text="Receive timely desktop alerts after standard meal hours and an evening alert if no meals were logged.",
            font=("Arial", 11),
            text_color=MUTED_TEXT,
            justify="left",
        )
        notif_sub_lbl.pack(anchor="w", padx=20, pady=(0, 10))

        # Reminder Time Inputs
        times_card = ctk.CTkFrame(card, fg_color=CARD_HOVER, corner_radius=14)
        times_card.pack(fill="x", padx=20, pady=(0, 14))

        def create_time_row(parent, label_text, default_time):
            r = ctk.CTkFrame(parent, fg_color="transparent")
            r.pack(fill="x", padx=14, pady=4)
            ctk.CTkLabel(r, text=label_text, font=("Arial", 12), text_color=TEXT_COLOR, width=220, anchor="w").pack(side="left")
            e = ctk.CTkEntry(r, width=80, placeholder_text="HH:MM")
            e.pack(side="left")
            e.insert(0, str(default_time))
            ctk.CTkLabel(r, text="(24-hr format, e.g. 14:30)", font=("Arial", 10), text_color=MUTED_TEXT).pack(side="left", padx=8)
            return e

        bf_time_entry = create_time_row(
            times_card,
            "🍳 Breakfast Reminder Time:",
            self.notification_settings.get("breakfast_time", "10:00"),
        )
        lu_time_entry = create_time_row(
            times_card,
            "🍛 Lunch Reminder Time:",
            self.notification_settings.get("lunch_time", "14:30"),
        )
        dn_time_entry = create_time_row(
            times_card,
            "🌙 Dinner Reminder Time:",
            self.notification_settings.get("dinner_time", "22:00"),
        )

        inact_divider = ctk.CTkFrame(times_card, height=1, fg_color=BORDER_COLOR)
        inact_divider.pack(fill="x", padx=12, pady=6)

        # Inactivity Check Controls
        is_inact_on = str(self.notification_settings.get("inactivity_check", "1")) == "1"
        inact_enabled_var = ctk.BooleanVar(value=is_inact_on)

        inact_switch = ctk.CTkSwitch(
            times_card,
            text="Alert if NO meals have been marked by evening",
            variable=inact_enabled_var,
            font=("Arial", 12, "bold"),
            progress_color=WARNING_COLOR,
            text_color=TEXT_COLOR,
        )
        inact_switch.pack(anchor="w", padx=14, pady=(4, 4))

        inact_time_entry = create_time_row(
            times_card,
            "⚠️ Evening Inactivity Check Time:",
            self.notification_settings.get("inactivity_time", "21:30"),
        )

        # Action Row (Test Notification + Save Preferences)
        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.pack(fill="x", padx=20, pady=(10, 20))

        def test_notification():
            test_title = "🔔 MealTrack AI — Reminder Test"
            test_msg = "Notifications are active and working! You will be alerted when meal markings are pending."
            send_system_notification(test_title, test_msg)
            self.show_toast_banner(test_title, test_msg)

        test_btn = ctk.CTkButton(
            action_row,
            text="🔔 Test Notification",
            command=test_notification,
            fg_color=CARD_HOVER,
            hover_color="#302254",
            font=("Arial", 13, "bold"),
            height=36,
            corner_radius=10,
            text_color=TEXT_COLOR,
        )
        test_btn.pack(side="left", padx=(0, 10))

        def save_settings():
            new_name = name_entry.get().strip()
            if new_name:
                self.user_name = new_name
                set_setting(self.cursor, self.connection, "user_name", self.user_name)

            try:
                self.meal_prices["Breakfast"] = int(bf_entry.get())
                self.meal_prices["Lunch"] = int(lu_entry.get())
                self.meal_prices["Dinner"] = int(dn_entry.get())
                set_setting(self.cursor, self.connection, "price_breakfast", self.meal_prices["Breakfast"])
                set_setting(self.cursor, self.connection, "price_lunch", self.meal_prices["Lunch"])
                set_setting(self.cursor, self.connection, "price_dinner", self.meal_prices["Dinner"])
            except ValueError:
                pass

            # Save Notification Settings
            self.notification_settings["notifications_enabled"] = "1" if notif_enabled_var.get() else "0"
            self.notification_settings["breakfast_time"] = bf_time_entry.get().strip() or "10:00"
            self.notification_settings["lunch_time"] = lu_time_entry.get().strip() or "14:30"
            self.notification_settings["dinner_time"] = dn_time_entry.get().strip() or "22:00"
            self.notification_settings["inactivity_check"] = "1" if inact_enabled_var.get() else "0"
            self.notification_settings["inactivity_time"] = inact_time_entry.get().strip() or "21:30"

            for k, v in self.notification_settings.items():
                set_setting(self.cursor, self.connection, k, v)

            self.refresh_all_dashboard_views()
            self.show_toast_banner("✓ Settings Saved", "Your notification preferences have been saved successfully!")
            print("Settings and Notification preferences saved successfully!")

        save_btn = ctk.CTkButton(
            action_row,
            text="💾 Save Preferences",
            command=save_settings,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            font=("Arial", 13, "bold"),
            height=36,
            corner_radius=10,
        )
        save_btn.pack(side="left")


    # -------------------------------------------------------------
    # VIEW 7: ABOUT
    # -------------------------------------------------------------

    def render_about_view(self):
        self.active_view_frame = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
        )
        self.active_view_frame.pack(fill="both", expand=True)

        card = ctk.CTkFrame(self.active_view_frame, fg_color=CARD_COLOR, corner_radius=18, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="both", expand=True, padx=4, pady=6)

        ctk.CTkLabel(card, text="🍴  MealTrack AI", font=("Arial", 24, "bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(card, text="Smart desktop meal tracking & expense management application.", font=("Arial", 13), text_color=MUTED_TEXT).pack(anchor="w", padx=24, pady=(0, 16))

        info_box = ctk.CTkFrame(card, fg_color=CARD_HOVER, corner_radius=14)
        info_box.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(info_box, text="Mess Business Rules & Policies:", font=("Arial", 14, "bold"), text_color=PRIMARY_COLOR).pack(anchor="w", padx=16, pady=(12, 6))
        rules = [
            "• Breakfast: ₹30 standard mess rate",
            "• Lunch: ₹50 standard mess rate",
            "• Dinner: ₹30 standard mess rate (Monday through Saturday)",
            "• Sunday Dinner: Mess is closed. Outside dinner can be logged with actual spend.",
            "• Past-Date Editing: Allows correcting or logging missed past days at any time.",
        ]
        for r in rules:
            ctk.CTkLabel(info_box, text=r, font=("Arial", 12), text_color=TEXT_COLOR).pack(anchor="w", padx=20, pady=2)

        ctk.CTkLabel(info_box, text="", font=("Arial", 2)).pack(pady=4)

    # -------------------------------------------------------------
    # GLOBAL PAST-DATE EDITOR MODAL (Preserving all Phase 1 capabilities)
    # -------------------------------------------------------------

    def open_date_editor(self, initial_date_str=None, on_save_callback=None):
        if not initial_date_str:
            initial_date_str = get_today_string()

        init_date = parse_date_string(initial_date_str)

        editor_frame = ctk.CTkFrame(
            self.app,
            width=540,
            height=660,
            fg_color=CARD_COLOR,
            corner_radius=20,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        editor_frame.place(relx=0.5, rely=0.5, anchor="center")
        editor_frame.pack_propagate(False)

        title_row = ctk.CTkFrame(editor_frame, fg_color="transparent")
        title_row.pack(fill="x", padx=24, pady=(20, 4))

        title = ctk.CTkLabel(
            title_row,
            text="🗓️  Log / Edit Meal Record",
            font=("Arial", 22, "bold"),
            text_color=TEXT_COLOR,
        )
        title.pack(side="left")

        subtitle = ctk.CTkLabel(
            editor_frame,
            text="Select a past or current date to enter or update meal records.",
            font=("Arial", 12),
            text_color=MUTED_TEXT,
        )
        subtitle.pack(anchor="w", padx=24, pady=(0, 10))

        date_picker_frame = ctk.CTkFrame(
            editor_frame,
            fg_color=CARD_HOVER,
            corner_radius=14,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        date_picker_frame.pack(fill="x", padx=20, pady=(0, 10))

        date_selectors_row = ctk.CTkFrame(date_picker_frame, fg_color="transparent")
        date_selectors_row.pack(fill="x", padx=14, pady=(12, 6))

        day_var = ctk.StringVar(value=f"{init_date.day:02d}")
        month_var = ctk.StringVar(value=f"{init_date.month:02d}")
        year_var = ctk.StringVar(value=str(init_date.year))

        day_label = ctk.CTkLabel(
            date_selectors_row,
            text="Day:",
            font=("Arial", 12, "bold"),
            text_color=MUTED_TEXT,
        )
        day_label.pack(side="left", padx=(0, 4))

        days_list = [f"{i:02d}" for i in range(1, 32)]
        day_menu = ctk.CTkOptionMenu(
            date_selectors_row,
            values=days_list,
            variable=day_var,
            width=65,
            height=32,
            fg_color=CARD_COLOR,
            button_color=PRIMARY_COLOR,
            button_hover_color=PRIMARY_HOVER,
            dropdown_fg_color=CARD_COLOR,
            text_color=TEXT_COLOR,
        )
        day_menu.pack(side="left", padx=(0, 8))

        month_label = ctk.CTkLabel(
            date_selectors_row,
            text="Month:",
            font=("Arial", 12, "bold"),
            text_color=MUTED_TEXT,
        )
        month_label.pack(side="left", padx=(0, 4))

        months_list = [f"{i:02d}" for i in range(1, 13)]
        month_menu = ctk.CTkOptionMenu(
            date_selectors_row,
            values=months_list,
            variable=month_var,
            width=65,
            height=32,
            fg_color=CARD_COLOR,
            button_color=PRIMARY_COLOR,
            button_hover_color=PRIMARY_HOVER,
            dropdown_fg_color=CARD_COLOR,
            text_color=TEXT_COLOR,
        )
        month_menu.pack(side="left", padx=(0, 8))

        year_label = ctk.CTkLabel(
            date_selectors_row,
            text="Year:",
            font=("Arial", 12, "bold"),
            text_color=MUTED_TEXT,
        )
        year_label.pack(side="left", padx=(0, 4))

        current_year = date.today().year
        years_list = [str(y) for y in range(current_year - 2, current_year + 3)]
        year_menu = ctk.CTkOptionMenu(
            date_selectors_row,
            values=years_list,
            variable=year_var,
            width=80,
            height=32,
            fg_color=CARD_COLOR,
            button_color=PRIMARY_COLOR,
            button_hover_color=PRIMARY_HOVER,
            dropdown_fg_color=CARD_COLOR,
            text_color=TEXT_COLOR,
        )
        year_menu.pack(side="left", padx=(0, 8))

        quick_btn_today = ctk.CTkButton(
            date_selectors_row,
            text="Today",
            width=50,
            height=32,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            font=("Arial", 11, "bold"),
            corner_radius=8,
            command=lambda: set_quick_date(date.today()),
        )
        quick_btn_today.pack(side="right", padx=(4, 0))

        quick_btn_yest = ctk.CTkButton(
            date_selectors_row,
            text="Yest",
            width=50,
            height=32,
            fg_color=CARD_COLOR,
            hover_color="#2C2148",
            font=("Arial", 11, "bold"),
            corner_radius=8,
            command=lambda: set_quick_date(date.today() - timedelta(days=1)),
        )
        quick_btn_yest.pack(side="right", padx=(4, 0))

        date_status_row = ctk.CTkFrame(date_picker_frame, fg_color="transparent")
        date_status_row.pack(fill="x", padx=14, pady=(0, 10))

        formatted_date_label = ctk.CTkLabel(
            date_status_row,
            text=init_date.strftime("%A, %d %B %Y"),
            font=("Arial", 13, "bold"),
            text_color=TEXT_COLOR,
        )
        formatted_date_label.pack(side="left")

        record_status_badge = ctk.CTkLabel(
            date_status_row,
            text="● Checking...",
            font=("Arial", 11, "bold"),
            text_color=MUTED_TEXT,
        )
        record_status_badge.pack(side="right")

        sunday_banner = ctk.CTkFrame(
            editor_frame,
            fg_color="#3B2314",
            corner_radius=10,
            border_width=1,
            border_color=WARNING_COLOR,
        )
        sunday_banner_label = ctk.CTkLabel(
            sunday_banner,
            text="🌙 Sunday: Mess dinner closed. Enter outside dinner amount.",
            font=("Arial", 11, "bold"),
            text_color=WARNING_COLOR,
        )
        sunday_banner_label.pack(padx=10, pady=5)

        meals_container = ctk.CTkFrame(editor_frame, fg_color="transparent")
        meals_container.pack(fill="x", padx=20, pady=(0, 10))

        editor_checkboxes = {}

        bf_card = ctk.CTkFrame(meals_container, fg_color=CARD_HOVER, corner_radius=12)
        bf_card.pack(fill="x", pady=3)
        ctk.CTkLabel(bf_card, text="🍳  Breakfast", font=("Arial", 14, "bold"), text_color=TEXT_COLOR).pack(side="left", padx=14, pady=10)
        ctk.CTkLabel(bf_card, text=f"₹{self.meal_prices.get('Breakfast', 30)}", font=("Arial", 13), text_color=MUTED_TEXT).pack(side="left", padx=10)
        bf_cb = ctk.CTkCheckBox(bf_card, text="Completed", fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER, border_color=MUTED_TEXT, border_width=2, corner_radius=6, checkmark_color=TEXT_COLOR, text_color=TEXT_COLOR, font=("Arial", 12, "bold"))
        bf_cb.pack(side="right", padx=14, pady=10)
        editor_checkboxes["Breakfast"] = bf_cb

        lu_card = ctk.CTkFrame(meals_container, fg_color=CARD_HOVER, corner_radius=12)
        lu_card.pack(fill="x", pady=3)
        ctk.CTkLabel(lu_card, text="🍛  Lunch", font=("Arial", 14, "bold"), text_color=TEXT_COLOR).pack(side="left", padx=14, pady=10)
        ctk.CTkLabel(lu_card, text=f"₹{self.meal_prices.get('Lunch', 50)}", font=("Arial", 13), text_color=MUTED_TEXT).pack(side="left", padx=10)
        lu_cb = ctk.CTkCheckBox(lu_card, text="Completed", fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER, border_color=MUTED_TEXT, border_width=2, corner_radius=6, checkmark_color=TEXT_COLOR, text_color=TEXT_COLOR, font=("Arial", 12, "bold"))
        lu_cb.pack(side="right", padx=14, pady=10)
        editor_checkboxes["Lunch"] = lu_cb

        dn_card = ctk.CTkFrame(meals_container, fg_color=CARD_HOVER, corner_radius=12)
        dn_card.pack(fill="x", pady=3)
        ctk.CTkLabel(dn_card, text="🌙  Dinner", font=("Arial", 14, "bold"), text_color=TEXT_COLOR).pack(side="left", padx=14, pady=10)
        dn_price_label = ctk.CTkLabel(dn_card, text=f"₹{self.meal_prices.get('Dinner', 30)}", font=("Arial", 13), text_color=MUTED_TEXT)
        dn_price_label.pack(side="left", padx=10)
        dn_cb = ctk.CTkCheckBox(dn_card, text="Completed", fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER, border_color=MUTED_TEXT, border_width=2, corner_radius=6, checkmark_color=TEXT_COLOR, text_color=TEXT_COLOR, font=("Arial", 12, "bold"))
        dn_cb.pack(side="right", padx=14, pady=10)
        editor_checkboxes["Dinner"] = dn_cb

        outside_row = ctk.CTkFrame(meals_container, fg_color="#1E1430", corner_radius=10)
        ctk.CTkLabel(outside_row, text="Sunday Outside Dinner Amount:", font=("Arial", 12, "bold"), text_color=TEXT_COLOR).pack(side="left", padx=14, pady=8)
        editor_outside_entry = ctk.CTkEntry(outside_row, placeholder_text="₹ amount", width=100, height=30)
        editor_outside_entry.pack(side="right", padx=14, pady=8)

        calc_card = ctk.CTkFrame(editor_frame, fg_color="#1A1230", corner_radius=14, border_width=1, border_color=BORDER_COLOR)
        calc_card.pack(fill="x", padx=20, pady=(0, 14))

        calc_row = ctk.CTkFrame(calc_card, fg_color="transparent")
        calc_row.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(calc_row, text="Calculated Daily Bill:", font=("Arial", 13), text_color=MUTED_TEXT).pack(side="left")
        calc_bill_value = ctk.CTkLabel(calc_row, text="₹0", font=("Arial", 20, "bold"), text_color=WARNING_COLOR)
        calc_bill_value.pack(side="left", padx=(8, 0))

        calc_meals_value = ctk.CTkLabel(calc_row, text="0 / 3 meals", font=("Arial", 13, "bold"), text_color=SUCCESS_COLOR)
        calc_meals_value.pack(side="right")

        action_row = ctk.CTkFrame(editor_frame, fg_color="transparent")
        action_row.pack(fill="x", padx=20, pady=(0, 16))

        save_btn = ctk.CTkButton(action_row, text="Save Changes", fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER, font=("Arial", 14, "bold"), height=40, corner_radius=10)
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        cancel_btn = ctk.CTkButton(action_row, text="Cancel", command=editor_frame.destroy, fg_color=CARD_HOVER, hover_color="#2C2148", font=("Arial", 13, "bold"), height=40, corner_radius=10, text_color=TEXT_COLOR)
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))

        def get_selected_date():
            try:
                d_val = int(day_var.get())
                m_val = int(month_var.get())
                y_val = int(year_var.get())
            except (ValueError, TypeError):
                return date.today()
            max_days = calendar.monthrange(y_val, m_val)[1]
            if d_val > max_days:
                d_val = max_days
                day_var.set(f"{d_val:02d}")
            return date(y_val, m_val, d_val)

        def get_selected_date_str():
            return get_selected_date().strftime(DATE_FORMAT)

        def recalc_bill(*args):
            sel_date = get_selected_date()
            is_sun = is_sunday(sel_date)
            meal_states = {m: editor_checkboxes[m].get() for m in ["Breakfast", "Lunch", "Dinner"]}
            outside_amt = 0
            if is_sun:
                outside_amt = parse_outside_dinner_amount(editor_outside_entry.get())
            total = calculate_bill(meal_states, self.meal_prices, outside_amt, sel_date)
            completed = sum(meal_states.values())
            calc_bill_value.configure(text=f"₹{total}")
            calc_meals_value.configure(text=f"{completed} / 3 meals")
            return total, meal_states, outside_amt

        def on_date_selected(*args):
            sel_date = get_selected_date()
            date_str = sel_date.strftime(DATE_FORMAT)
            formatted_date_label.configure(text=sel_date.strftime("%A, %d %B %Y"))
            is_sun = is_sunday(sel_date)

            if is_sun:
                sunday_banner.pack(fill="x", padx=20, pady=(0, 8), before=meals_container)
                outside_row.pack(fill="x", pady=(4, 0))
                dn_price_label.configure(text="Outside")
            else:
                sunday_banner.pack_forget()
                outside_row.pack_forget()
                dn_price_label.configure(text=f"₹{self.meal_prices.get('Dinner', 30)}")

            record = fetch_record_by_date(self.cursor, date_str)
            if record:
                bf, lu, dn, out_dn, saved_b = record
                if bf == 1: editor_checkboxes["Breakfast"].select()
                else: editor_checkboxes["Breakfast"].deselect()

                if lu == 1: editor_checkboxes["Lunch"].select()
                else: editor_checkboxes["Lunch"].deselect()

                if dn == 1: editor_checkboxes["Dinner"].select()
                else: editor_checkboxes["Dinner"].deselect()

                editor_outside_entry.delete(0, "end")
                if out_dn > 0:
                    editor_outside_entry.insert(0, str(out_dn))

                record_status_badge.configure(text="● Saved Record Found", text_color=SUCCESS_COLOR)
            else:
                editor_checkboxes["Breakfast"].deselect()
                editor_checkboxes["Lunch"].deselect()
                editor_checkboxes["Dinner"].deselect()
                editor_outside_entry.delete(0, "end")
                record_status_badge.configure(text="○ New Date (No Record Yet)", text_color=WARNING_COLOR)

            recalc_bill()

        def set_quick_date(target_d):
            day_var.set(f"{target_d.day:02d}")
            month_var.set(f"{target_d.month:02d}")
            year_var.set(str(target_d.year))
            on_date_selected()

        def save_changes():
            sel_date_str = get_selected_date_str()
            total_bill, meal_states, outside_amt = recalc_bill()

            save_date_meal_record(
                self.cursor,
                self.connection,
                sel_date_str,
                meal_states,
                total_bill,
                outside_amt,
            )

            self.refresh_all_dashboard_views(edited_date=sel_date_str)
            if on_save_callback:
                on_save_callback()

            print(f"Record for {sel_date_str} saved successfully! Bill: ₹{total_bill}")
            editor_frame.destroy()

        day_menu.configure(command=lambda _: on_date_selected())
        month_menu.configure(command=lambda _: on_date_selected())
        year_menu.configure(command=lambda _: on_date_selected())

        for cb in editor_checkboxes.values():
            cb.configure(command=recalc_bill)

        editor_outside_entry.bind("<KeyRelease>", lambda e: recalc_bill())
        save_btn.configure(command=save_changes)

        on_date_selected()
