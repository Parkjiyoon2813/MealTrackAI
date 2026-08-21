# MealTrack AI — Project Instructions

## Project
MealTrack AI is a desktop meal tracking application built with Python,
CustomTkinter, and SQLite.

Current project location:
C:\Users\Jiiyoon\PROJECTS\MealTrackAI

## Current Technology
- Python
- CustomTkinter
- SQLite
- Git
- VS Code
- Virtual environment: .venv

## Current Architecture
The project is currently intentionally kept in app.py while the UI
redesign is in progress.

After the UI redesign is stable, refactor the project into separate files:

- app.py
- database.py
- logic.py
- ui.py
- constants.py

Do NOT permanently leave the entire project in app.py.

## Important Existing Functionality

The application currently supports:

1. Daily breakfast, lunch, and dinner tracking.
2. Checkbox-based meal completion.
3. Automatic daily bill calculation.
4. SQLite persistence.
5. Loading today's saved record when the application starts.
6. Updating an existing record for the current date.
7. Dynamic greeting:
   - Good Morning
   - Good Afternoon
   - Good Evening
8. Meal History.
9. Monthly Summary.
10. Monthly total spending.
11. Monthly average daily spending.
12. Monthly meal completion tracking.
13. Highest and lowest spending days.
14. Sunday dinner is normally NOT provided by the mess.
15. Sunday dinner can be entered as an outside meal amount.
16. Scrollable dashboard.
17. Sidebar navigation.
18. Dashboard summary cards.

## Current Data Model

SQLite database:

meals.db

Current table:

meals(
    date TEXT PRIMARY KEY,
    breakfast INTEGER,
    lunch INTEGER,
    dinner INTEGER,
    outside_dinner INTEGER DEFAULT 0,
    bill INTEGER
)

## Important Business Rules

Breakfast:
₹30

Lunch:
₹50

Dinner:
₹30

Sunday:
The mess does NOT provide dinner.

Sunday dinner must be purchased outside and the user can enter
the actual outside-dinner amount.

Do not hard-code Sunday dinner to ₹30 when calculating the Sunday bill.

## Current UI Direction

The application is being redesigned from a basic dark/blue CustomTkinter
interface into a polished dashboard.

Current design system:

BG_COLOR = "#0B0818"
CARD_COLOR = "#161126"
CARD_HOVER = "#21183A"
PRIMARY_COLOR = "#7C3AED"
PRIMARY_HOVER = "#6D28D9"
SUCCESS_COLOR = "#22C55E"
WARNING_COLOR = "#F59E0B"
DANGER_COLOR = "#F43F5E"
TEXT_COLOR = "#F8FAFC"
MUTED_TEXT = "#A1A1AA"
BORDER_COLOR = "#2D2445"

## Current UI Structure

Main window:

Sidebar
+
Scrollable main content

Sidebar currently contains:

- Dashboard
- Today's Meals
- Meal History
- Monthly Summary
- Analytics
- Settings

Main dashboard currently contains:

- Dynamic greeting
- Dynamic date
- Four summary cards:
  - Today's Bill
  - Meals Completed
  - This Month
  - Avg / Day
- Today's Meals section
- Today's Bill/action area
- Save Today's Record action

## UI Target

The final dashboard should closely follow the provided MealTrack AI
reference design.

Target visual characteristics:

- Dark navy/purple background
- Strong purple primary accent
- Colorful KPI cards
- Rounded cards
- Polished sidebar
- Dashboard-style layout
- Today's Meals presented visually
- Calendar/month overview
- Monthly Summary panel
- Spending Trend
- Quick Insights
- Motivation section
- Strong typography
- Consistent spacing
- Product-like visual hierarchy

Do not blindly add every target component to the dashboard.

Sidebar sections should eventually have distinct purposes:

Dashboard:
Today's overview.

Today's Meals:
Focused meal tracking.

Meal History:
Historical records and editing.

Monthly Summary:
Monthly financial and meal summary.

Analytics:
Charts and deeper trends.

Settings:
Preferences and configuration.

## Planned Future Feature

Past-date editing must eventually be implemented.

Example:

Meal History
→ select a previous date
→ edit breakfast/lunch/dinner
→ edit Sunday outside dinner amount if applicable
→ save changes

The database record for that specific date should be updated.

Do NOT implement this feature until the current UI redesign is stable.

## Important Development Rule

Preserve working functionality while redesigning the UI.

Do not unnecessarily rewrite working database logic.

Before making large structural changes:

1. Inspect the existing code.
2. Explain the intended change.
3. Make the smallest safe change.
4. Run/test the application.
5. Review the result.
6. Commit stable checkpoints with Git.

Do not duplicate functions, variables, frames, or navigation components.

Before adding new code, search the existing codebase to determine whether
the functionality already exists.

## Git

The project is already under Git version control.

Use Git checkpoints before major architectural changes.

Never delete working functionality without explaining why.

## Current UI Status

The application currently has:

- Design system
- Sidebar
- Scrollable content
- Header
- Dashboard summary cards
- Today's Meals cards
- Save Today's Record action
- Meal History
- Monthly Summary
- Dynamic greeting
- Persistent SQLite data

The UI redesign is NOT finished.

Continue from the existing implementation instead of rebuilding it.