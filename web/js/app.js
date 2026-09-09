/**
 * MealTrack AI - Core Web App Controller
 */

import { db } from './db.js';
import {
  formatDateKey,
  parseDateKey,
  isSunday,
  getGreeting,
  getDisplayDate,
  calculateBill,
  getMonthlySummary,
  getRecentSpendingTrend,
  getQuickInsights,
  getMotivationMessage,
  getDayOfWeekDistribution,
} from './logic.js';
import { notifier } from './notifications.js';
import { MEAL_ICONS } from './constants.js';

class MealTrackApp {
  constructor() {
    this.currentView = 'dashboard';
    const now = new Date();
    this.selectedCalMonth = now.getMonth();
    this.selectedCalYear = now.getFullYear();

    this.selectedMonthViewMonth = now.getMonth();
    this.selectedMonthViewYear = now.getFullYear();

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.renderHeader();
    this.showView(this.currentView);
    notifier.startPeriodicChecker();

    // Check if initial sample data should be added if store is totally empty
    this.seedInitialDataIfEmpty();
  }

  seedInitialDataIfEmpty() {
    const meals = db.getAllMeals();
    if (Object.keys(meals).length === 0) {
      // Add a couple of realistic recent days so new users see immediate dashboard charts
      const today = new Date();
      const prices = db.getPrices();

      // Today - 2
      const d2 = new Date(today);
      d2.setDate(today.getDate() - 2);
      const k2 = formatDateKey(d2);
      db.saveMeal(k2, { Breakfast: 1, Lunch: 1, Dinner: 1 }, calculateBill({ Breakfast: 1, Lunch: 1, Dinner: 1 }, prices, 0, d2), 0);

      // Today - 1
      const d1 = new Date(today);
      d1.setDate(today.getDate() - 1);
      const k1 = formatDateKey(d1);
      db.saveMeal(k1, { Breakfast: 1, Lunch: 1, Dinner: 0 }, calculateBill({ Breakfast: 1, Lunch: 1, Dinner: 0 }, prices, 0, d1), 0);
    }
  }

  setupEventListeners() {
    // Nav Items
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const view = e.currentTarget.dataset.view;
        if (view) this.showView(view);
        // Close mobile sidebar if open
        document.querySelector('.sidebar').classList.remove('mobile-open');
      });
    });

    // Mobile menu toggle
    const mobBtn = document.getElementById('mobile-menu-toggle');
    if (mobBtn) {
      mobBtn.addEventListener('click', () => {
        document.querySelector('.sidebar').classList.toggle('mobile-open');
      });
    }

    // Header Quick Actions
    const logPastBtn = document.getElementById('quick-log-past-btn');
    if (logPastBtn) {
      logPastBtn.addEventListener('click', () => this.openDateModal());
    }

    // Modal close
    const modalOverlay = document.getElementById('date-editor-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');

    if (modalCloseBtn) modalCloseBtn.addEventListener('click', () => this.closeDateModal());
    if (modalCancelBtn) modalCancelBtn.addEventListener('click', () => this.closeDateModal());
    if (modalOverlay) {
      modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) this.closeDateModal();
      });
    }

    // Modal Form Submit
    const modalForm = document.getElementById('modal-date-form');
    if (modalForm) {
      modalForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveDateModalRecord();
      });
    }

    // Modal Delete Button
    const modalDeleteBtn = document.getElementById('modal-delete-btn');
    if (modalDeleteBtn) {
      modalDeleteBtn.addEventListener('click', () => this.deleteDateModalRecord());
    }

    // Modal Date change handler to update Sunday status
    const modalDateInput = document.getElementById('modal-date-input');
    if (modalDateInput) {
      modalDateInput.addEventListener('change', (e) => {
        this.updateModalSundayUI(e.target.value);
      });
    }

    // Export & Import Handlers in Settings
    const exportBtn = document.getElementById('export-json-btn');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.handleExportBackup());
    }

    const importInput = document.getElementById('import-json-file');
    if (importInput) {
      importInput.addEventListener('change', (e) => this.handleImportBackup(e));
    }
  }

  showView(viewName) {
    this.currentView = viewName;

    // Update Nav active classes
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    // Toggle view containers
    document.querySelectorAll('.view-section').forEach(sec => {
      sec.classList.remove('active-view');
    });

    const targetSection = document.getElementById(`view-${viewName}`);
    if (targetSection) {
      targetSection.classList.add('active-view');
    }

    // Refresh view specific logic
    this.renderHeader();
    this.renderSidebarSummary();

    switch (viewName) {
      case 'dashboard':
        this.renderDashboardView();
        break;
      case 'today-meals':
        this.renderTodayMealsView();
        break;
      case 'history':
        this.renderHistoryView();
        break;
      case 'monthly':
        this.renderMonthlyView();
        break;
      case 'analytics':
        this.renderAnalyticsView();
        break;
      case 'settings':
        this.renderSettingsView();
        break;
    }
  }

  renderHeader() {
    const greetingEl = document.getElementById('dynamic-greeting');
    const user = db.getUserName();
    if (greetingEl) {
      greetingEl.innerHTML = `${getGreeting()}, <span class="greeting-user">${escapeHTML(user)}</span> 👋`;
    }

    const datePill = document.getElementById('header-date-pill');
    if (datePill) {
      datePill.innerHTML = `📅  ${getDisplayDate()}`;
    }
  }

  renderSidebarSummary() {
    const today = new Date();
    const allMeals = db.getAllMeals();
    const prices = db.getPrices();
    const summary = getMonthlySummary(allMeals, today.getFullYear(), today.getMonth(), prices);

    const spendEl = document.getElementById('sidebar-month-spend');
    const daysEl = document.getElementById('sidebar-month-days');

    if (spendEl) spendEl.textContent = `₹${summary.totalSpent}`;
    if (daysEl) daysEl.textContent = `${summary.daysRecorded} / ${summary.daysInMonth} days logged`;
  }

  // =========================================================================
  // VIEW 1: DASHBOARD
  // =========================================================================

  renderDashboardView() {
    const allMeals = db.getAllMeals();
    const prices = db.getPrices();
    const today = new Date();
    const todayKey = formatDateKey(today);
    const todayRec = db.getMeal(todayKey) || { breakfast: 0, lunch: 0, dinner: 0, outside_dinner: 0, bill: 0 };

    const monthSummary = getMonthlySummary(allMeals, today.getFullYear(), today.getMonth(), prices);

    // 1. Top KPI Cards
    const kpiTodayBill = document.getElementById('kpi-today-bill');
    const kpiMealsCompleted = document.getElementById('kpi-meals-completed');
    const kpiMonthSpend = document.getElementById('kpi-month-spend');
    const kpiAvgDaily = document.getElementById('kpi-avg-daily');

    const completedTodayCount = (todayRec.breakfast ? 1 : 0) + (todayRec.lunch ? 1 : 0) + (todayRec.dinner ? 1 : 0);

    if (kpiTodayBill) kpiTodayBill.textContent = `₹${todayRec.bill || 0}`;
    if (kpiMealsCompleted) kpiMealsCompleted.textContent = `${completedTodayCount} / 3`;
    if (kpiMonthSpend) kpiMonthSpend.textContent = `₹${monthSummary.totalSpent}`;
    if (kpiAvgDaily) kpiAvgDaily.textContent = `₹${Math.round(monthSummary.averageSpending)}`;

    // 2. Middle Section: Today's Meals Quick Card
    this.renderDashboardTodayMealsCard(todayRec);

    // 3. Middle Section: Mini Month Calendar
    this.renderDashboardCalendar();

    // 4. Middle Section: Monthly Summary Quick Card
    this.renderDashboardMonthlySummaryCard(monthSummary);

    // 5. Bottom Section: Spending Trend Bar Chart
    this.renderDashboardSpendingTrend(allMeals);

    // 6. Bottom Section: Quick Insights
    this.renderDashboardInsights(monthSummary);

    // 7. Bottom Section: Motivation Quote
    this.renderDashboardMotivation(monthSummary);
  }

  renderDashboardTodayMealsCard(todayRec) {
    const container = document.getElementById('dash-today-meals-grid');
    if (!container) return;

    const isSun = isSunday();
    const prices = db.getPrices();

    const mealConfig = [
      { key: 'Breakfast', icon: '🍳', rate: prices.Breakfast, class: 'meal-subcard-breakfast', done: !!todayRec.breakfast },
      { key: 'Lunch', icon: '🍛', rate: prices.Lunch, class: 'meal-subcard-lunch', done: !!todayRec.lunch },
      { key: 'Dinner', icon: '🌙', rate: isSun ? 'Outside' : prices.Dinner, class: 'meal-subcard-dinner', done: !!todayRec.dinner },
    ];

    container.innerHTML = mealConfig.map(m => `
      <div class="meal-subcard ${m.class}">
        <div class="meal-subcard-icon">${m.icon}</div>
        <div class="meal-subcard-title">${m.key}</div>
        <div class="meal-subcard-price">${typeof m.rate === 'number' ? `₹${m.rate}` : m.rate}</div>
        <button class="meal-toggle-btn ${m.done ? 'btn-completed' : 'btn-pending'}" data-meal="${m.key}">
          ${m.done ? '✓ Completed' : 'Mark Completed'}
        </button>
      </div>
    `).join('');

    container.querySelectorAll('.meal-toggle-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const mealKey = e.currentTarget.dataset.meal;
        this.toggleTodayMeal(mealKey);
      });
    });
  }

  toggleTodayMeal(mealKey) {
    const today = new Date();
    const todayKey = formatDateKey(today);
    const current = db.getMeal(todayKey) || { breakfast: 0, lunch: 0, dinner: 0, outside_dinner: 0 };
    const prices = db.getPrices();

    const stateKey = mealKey.toLowerCase();
    const newState = current[stateKey] ? 0 : 1;

    const mealStates = {
      Breakfast: mealKey === 'Breakfast' ? newState : current.breakfast,
      Lunch: mealKey === 'Lunch' ? newState : current.lunch,
      Dinner: mealKey === 'Dinner' ? newState : current.dinner,
    };

    const bill = calculateBill(mealStates, prices, current.outside_dinner, today);
    db.saveMeal(todayKey, mealStates, bill, current.outside_dinner);

    notifier.showToast("Record Updated", `${mealKey} marked as ${newState ? 'completed' : 'pending'} for today.`, "info", "✓");

    this.renderDashboardView();
    this.renderSidebarSummary();
  }

  renderDashboardCalendar() {
    const calGrid = document.getElementById('dash-calendar-grid');
    const monthTitle = document.getElementById('dash-calendar-month-title');
    if (!calGrid || !monthTitle) return;

    const year = this.selectedCalYear;
    const month = this.selectedCalMonth;

    monthTitle.textContent = new Date(year, month, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const allMeals = db.getAllMeals();
    const today = new Date();
    const todayKey = formatDateKey(today);

    // Days header
    const daysHeader = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
    let html = daysHeader.map(d => `<div class="cal-day-label">${d}</div>`).join('');

    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Empty previous month cells
    for (let i = 0; i < firstDayIndex; i++) {
      html += `<div class="cal-day-cell empty"></div>`;
    }

    // Days in month
    for (let day = 1; day <= daysInMonth; day++) {
      const dateKey = `${String(day).padStart(2, '0')}-${String(month + 1).padStart(2, '0')}-${year}`;
      const rec = allMeals[dateKey];
      const isCurrentToday = dateKey === todayKey;
      const isRecorded = !!rec;

      const classes = ['cal-day-cell'];
      if (isCurrentToday) classes.push('today');
      if (isRecorded) classes.push('recorded');

      const tooltip = rec ? `₹${rec.bill}` : '';
      html += `<div class="${classes.join(' ')}" data-date="${dateKey}" title="${tooltip}">${day}</div>`;
    }

    calGrid.innerHTML = html;

    // Attach click listeners to calendar cells to open past-date editor
    calGrid.querySelectorAll('.cal-day-cell:not(.empty)').forEach(cell => {
      cell.addEventListener('click', (e) => {
        const dateKey = e.currentTarget.dataset.date;
        this.openDateModal(dateKey);
      });
    });

    // Navigation buttons
    const prevBtn = document.getElementById('dash-cal-prev');
    const nextBtn = document.getElementById('dash-cal-next');

    if (prevBtn) {
      prevBtn.onclick = () => {
        if (this.selectedCalMonth === 0) {
          this.selectedCalMonth = 11;
          this.selectedCalYear--;
        } else {
          this.selectedCalMonth--;
        }
        this.renderDashboardCalendar();
      };
    }

    if (nextBtn) {
      nextBtn.onclick = () => {
        if (this.selectedCalMonth === 11) {
          this.selectedCalMonth = 0;
          this.selectedCalYear++;
        } else {
          this.selectedCalMonth++;
        }
        this.renderDashboardCalendar();
      };
    }
  }

  renderDashboardMonthlySummaryCard(summary) {
    const list = document.getElementById('dash-month-summary-list');
    if (!list) return;

    list.innerHTML = `
      <div class="summary-stat-row">
        <span class="stat-label">Total Spent</span>
        <span class="stat-val" style="color: var(--warning)">₹${summary.totalSpent}</span>
      </div>
      <div class="summary-stat-row">
        <span class="stat-label">Meals Completed</span>
        <span class="stat-val" style="color: var(--success)">${summary.totalMeals} / ${summary.totalPossibleMeals}</span>
      </div>
      <div class="summary-stat-row">
        <span class="stat-label">Average / Day</span>
        <span class="stat-val">₹${Math.round(summary.averageSpending)}</span>
      </div>
      <div class="summary-stat-row">
        <span class="stat-label">Days Recorded</span>
        <span class="stat-val">${summary.daysRecorded} days</span>
      </div>
      <div class="summary-stat-row">
        <span class="stat-label">Highest Day</span>
        <span class="stat-val">${summary.highestDay ? `${summary.highestDay.date.slice(0, 5)} (₹${summary.highestDay.bill})` : '—'}</span>
      </div>
    `;
  }

  renderDashboardSpendingTrend(allMeals) {
    const container = document.getElementById('dash-trend-bars');
    if (!container) return;

    const trendItems = getRecentSpendingTrend(allMeals, 7);
    const maxBill = Math.max(...trendItems.map(t => t.bill), 100);

    container.innerHTML = trendItems.map(item => {
      const heightPercent = item.bill > 0 ? Math.min(100, Math.max(15, (item.bill / maxBill) * 100)) : 0;
      return `
        <div class="trend-bar-col" title="${item.dateKey}: ₹${item.bill}">
          <span class="trend-amount-label">${item.bill > 0 ? `₹${item.bill}` : ''}</span>
          <div class="trend-bar-track">
            <div class="trend-bar-fill ${item.isToday ? 'today-bar' : ''}" style="height: ${heightPercent}%"></div>
          </div>
          <span class="trend-day-label">${item.dayName}</span>
        </div>
      `;
    }).join('');
  }

  renderDashboardInsights(summary) {
    const container = document.getElementById('dash-insights-list');
    if (!container) return;

    const insights = getQuickInsights(summary);
    container.innerHTML = insights.map(i => `
      <div class="insight-item">
        <span class="insight-bullet">✦</span>
        <span>${i}</span>
      </div>
    `).join('');
  }

  renderDashboardMotivation(summary) {
    const quoteEl = document.getElementById('dash-motivation-quote');
    if (quoteEl) {
      quoteEl.textContent = `"${getMotivationMessage(summary)}"`;
    }
  }

  // =========================================================================
  // VIEW 2: TODAY'S MEALS DEDICATED VIEW
  // =========================================================================

  renderTodayMealsView() {
    const today = new Date();
    const todayKey = formatDateKey(today);
    const todayRec = db.getMeal(todayKey) || { breakfast: 0, lunch: 0, dinner: 0, outside_dinner: 0, bill: 0 };
    const prices = db.getPrices();
    const isSun = isSunday(today);

    const fullGrid = document.getElementById('today-meals-full-grid');
    if (!fullGrid) return;

    const mealConfig = [
      { key: 'Breakfast', icon: '🍳', rate: `Standard Rate: ₹${prices.Breakfast}`, done: !!todayRec.breakfast, isSunDinner: false },
      { key: 'Lunch', icon: '🍛', rate: `Standard Rate: ₹${prices.Lunch}`, done: !!todayRec.lunch, isSunDinner: false },
      { key: 'Dinner', icon: '🌙', rate: isSun ? 'Sunday Outside Dinner' : `Standard Rate: ₹${prices.Dinner}`, done: !!todayRec.dinner, isSunDinner: isSun },
    ];

    fullGrid.innerHTML = mealConfig.map(m => `
      <div class="meal-big-card">
        <div class="meal-big-icon">${m.icon}</div>
        <div class="meal-big-title">${m.key}</div>
        <div class="meal-big-rate">${m.rate}</div>

        ${m.isSunDinner ? `
          <div class="outside-dinner-input-group">
            <span class="outside-dinner-label">Amount: ₹</span>
            <input type="number" id="today-outside-input" class="outside-dinner-input" value="${todayRec.outside_dinner || 0}" min="0">
          </div>
        ` : ''}

        <button class="meal-big-btn ${m.done ? 'btn-completed' : 'header-btn-primary'}" data-meal="${m.key}">
          ${m.done ? '✓ Completed' : 'Mark as Completed'}
        </button>
      </div>
    `).join('');

    const totalEl = document.getElementById('today-view-total');
    if (totalEl) totalEl.textContent = `₹${todayRec.bill || 0}`;

    // Attach meal buttons
    fullGrid.querySelectorAll('.meal-big-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const mealKey = e.currentTarget.dataset.meal;
        this.toggleTodayMealView(mealKey);
      });
    });

    // Save button
    const saveBtn = document.getElementById('today-view-save-btn');
    if (saveBtn) {
      saveBtn.onclick = () => {
        this.saveTodayExplicit();
      };
    }
  }

  toggleTodayMealView(mealKey) {
    const today = new Date();
    const todayKey = formatDateKey(today);
    const current = db.getMeal(todayKey) || { breakfast: 0, lunch: 0, dinner: 0, outside_dinner: 0 };
    const prices = db.getPrices();

    const stateKey = mealKey.toLowerCase();
    const newState = current[stateKey] ? 0 : 1;

    let outsideDinner = current.outside_dinner || 0;
    const outsideInput = document.getElementById('today-outside-input');
    if (outsideInput) {
      outsideDinner = Number(outsideInput.value) || 0;
    }

    const mealStates = {
      Breakfast: mealKey === 'Breakfast' ? newState : current.breakfast,
      Lunch: mealKey === 'Lunch' ? newState : current.lunch,
      Dinner: mealKey === 'Dinner' ? newState : current.dinner,
    };

    const bill = calculateBill(mealStates, prices, outsideDinner, today);
    db.saveMeal(todayKey, mealStates, bill, outsideDinner);

    notifier.showToast("Saved", `${mealKey} updated for today!`, "info", "💾");
    this.renderTodayMealsView();
    this.renderSidebarSummary();
  }

  saveTodayExplicit() {
    const today = new Date();
    const todayKey = formatDateKey(today);
    const current = db.getMeal(todayKey) || { breakfast: 0, lunch: 0, dinner: 0, outside_dinner: 0 };
    const prices = db.getPrices();

    let outsideDinner = current.outside_dinner || 0;
    const outsideInput = document.getElementById('today-outside-input');
    if (outsideInput) {
      outsideDinner = Number(outsideInput.value) || 0;
    }

    const mealStates = {
      Breakfast: current.breakfast,
      Lunch: current.lunch,
      Dinner: current.dinner,
    };

    const bill = calculateBill(mealStates, prices, outsideDinner, today);
    db.saveMeal(todayKey, mealStates, bill, outsideDinner);

    notifier.showToast("Database Updated", `Today's record (₹${bill}) saved successfully!`, "info", "💾");
    this.renderTodayMealsView();
    this.renderSidebarSummary();
  }

  // =========================================================================
  // VIEW 3: MEAL HISTORY & AUDIT LOG
  // =========================================================================

  renderHistoryView() {
    const tbody = document.getElementById('history-table-body');
    const searchInput = document.getElementById('history-search-input');
    if (!tbody) return;

    const allMeals = db.getAllMeals();
    let records = Object.values(allMeals);

    // Sort newest to oldest
    records.sort((a, b) => {
      const da = parseDateKey(a.date);
      const db = parseDateKey(b.date);
      return db - da;
    });

    const filterText = searchInput ? searchInput.value.toLowerCase().trim() : '';
    if (filterText) {
      records = records.filter(r => r.date.toLowerCase().includes(filterText));
    }

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--muted-text); padding: 32px;">No historical meal records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(r => {
      const d = parseDateKey(r.date);
      const isSun = d.getDay() === 0;
      const dayDisplay = d.toLocaleDateString('en-US', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });

      return `
        <tr>
          <td>
            <strong>${dayDisplay}</strong>
            ${isSun ? '<span class="badge-pill" style="margin-left: 6px; color: var(--warning)">Sunday</span>' : ''}
          </td>
          <td>
            <span class="meal-chip ${r.breakfast ? 'chip-done' : 'chip-missed'}">🍳 Breakfast</span>
            <span class="meal-chip ${r.lunch ? 'chip-done' : 'chip-missed'}">🍛 Lunch</span>
            <span class="meal-chip ${r.dinner ? 'chip-done' : 'chip-missed'}">🌙 Dinner</span>
          </td>
          <td>${isSun && r.dinner ? `₹${r.outside_dinner || 0}` : '—'}</td>
          <td><strong style="color: var(--warning)">₹${r.bill || 0}</strong></td>
          <td>
            <button class="action-btn-sm" data-edit="${r.date}">✏️ Edit</button>
            <button class="action-btn-sm action-btn-danger" data-del="${r.date}">🗑️</button>
          </td>
        </tr>
      `;
    }).join('');

    // Attach row actions
    tbody.querySelectorAll('[data-edit]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.openDateModal(e.currentTarget.dataset.edit);
      });
    });

    tbody.querySelectorAll('[data-del]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const dateKey = e.currentTarget.dataset.del;
        if (confirm(`Delete meal record for ${dateKey}?`)) {
          db.deleteMeal(dateKey);
          notifier.showToast("Record Deleted", `Meal record for ${dateKey} was removed.`, "warning", "🗑️");
          this.renderHistoryView();
          this.renderSidebarSummary();
        }
      });
    });

    if (searchInput && !searchInput.dataset.bound) {
      searchInput.dataset.bound = 'true';
      searchInput.addEventListener('input', () => this.renderHistoryView());
    }
  }

  // =========================================================================
  // VIEW 4: MONTHLY SUMMARY
  // =========================================================================

  renderMonthlyView() {
    const allMeals = db.getAllMeals();
    const prices = db.getPrices();
    const year = this.selectedMonthViewYear;
    const month = this.selectedMonthViewMonth;

    const summary = getMonthlySummary(allMeals, year, month, prices);

    const monthTitle = document.getElementById('monthly-view-title');
    if (monthTitle) monthTitle.textContent = summary.monthLabel;

    // Financial KPI Cards
    const totalSpentEl = document.getElementById('monthly-kpi-total-spent');
    const totalMealsEl = document.getElementById('monthly-kpi-total-meals');
    const avgSpendEl = document.getElementById('monthly-kpi-avg-spend');
    const daysLoggedEl = document.getElementById('monthly-kpi-days-logged');

    if (totalSpentEl) totalSpentEl.textContent = `₹${summary.totalSpent}`;
    if (totalMealsEl) totalMealsEl.textContent = `${summary.totalMeals} / ${summary.totalPossibleMeals}`;
    if (avgSpendEl) avgSpendEl.textContent = `₹${Math.round(summary.averageSpending)}`;
    if (daysLoggedEl) daysLoggedEl.textContent = `${summary.daysRecorded} / ${summary.daysInMonth} days`;

    // Distribution breakdown
    const bfSpendEl = document.getElementById('monthly-dist-bf-spend');
    const luSpendEl = document.getElementById('monthly-dist-lu-spend');
    const dnSpendEl = document.getElementById('monthly-dist-dn-spend');

    if (bfSpendEl) bfSpendEl.textContent = `₹${summary.breakdown.breakfast.spend} (${summary.breakdown.breakfast.count} meals)`;
    if (luSpendEl) luSpendEl.textContent = `₹${summary.breakdown.lunch.spend} (${summary.breakdown.lunch.count} meals)`;
    if (dnSpendEl) dnSpendEl.textContent = `₹${summary.breakdown.dinner.spend} (${summary.breakdown.dinner.count} meals)`;

    // Monthly table
    const tbody = document.getElementById('monthly-table-body');
    if (tbody) {
      if (summary.records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--muted-text); padding: 24px;">No records logged for ${summary.monthLabel}.</td></tr>`;
      } else {
        tbody.innerHTML = summary.records.map(r => `
          <tr>
            <td><strong>${r.date}</strong></td>
            <td>${(r.breakfast ? 1 : 0) + (r.lunch ? 1 : 0) + (r.dinner ? 1 : 0)} / 3</td>
            <td>${isSunday(r.date) && r.outside_dinner > 0 ? `Outside ₹${r.outside_dinner}` : 'Standard'}</td>
            <td><strong style="color: var(--warning)">₹${r.bill}</strong></td>
          </tr>
        `).join('');
      }
    }

    // Month Navigation
    const prevBtn = document.getElementById('monthly-prev-btn');
    const nextBtn = document.getElementById('monthly-next-btn');

    if (prevBtn) {
      prevBtn.onclick = () => {
        if (this.selectedMonthViewMonth === 0) {
          this.selectedMonthViewMonth = 11;
          this.selectedMonthViewYear--;
        } else {
          this.selectedMonthViewMonth--;
        }
        this.renderMonthlyView();
      };
    }

    if (nextBtn) {
      nextBtn.onclick = () => {
        if (this.selectedMonthViewMonth === 11) {
          this.selectedMonthViewMonth = 0;
          this.selectedMonthViewYear++;
        } else {
          this.selectedMonthViewMonth++;
        }
        this.renderMonthlyView();
      };
    }
  }

  // =========================================================================
  // VIEW 5: ANALYTICS & TRENDS
  // =========================================================================

  renderAnalyticsView() {
    const allMeals = db.getAllMeals();
    const dowDistribution = getDayOfWeekDistribution(allMeals);

    const dowContainer = document.getElementById('analytics-dow-bars');
    if (dowContainer) {
      const maxSpend = Math.max(...dowDistribution.map(d => d.spend), 100);
      dowContainer.innerHTML = dowDistribution.map(d => {
        const heightPercent = d.spend > 0 ? Math.min(100, Math.max(12, (d.spend / maxSpend) * 100)) : 0;
        return `
          <div class="trend-bar-col" title="${d.name}: Total ₹${d.spend} (${d.count} days)">
            <span class="trend-amount-label">${d.spend > 0 ? `₹${d.spend}` : ''}</span>
            <div class="trend-bar-track">
              <div class="trend-bar-fill" style="height: ${heightPercent}%"></div>
            </div>
            <span class="trend-day-label">${d.name.slice(0, 3)}</span>
          </div>
        `;
      }).join('');
    }

    const today = new Date();
    const prices = db.getPrices();
    const summary = getMonthlySummary(allMeals, today.getFullYear(), today.getMonth(), prices);

    // Projected Month Spend
    const daysPassed = today.getDate();
    const projectedTotal = daysPassed > 0 ? Math.round((summary.totalSpent / daysPassed) * summary.daysInMonth) : 0;

    const projEl = document.getElementById('analytics-projected-spend');
    if (projEl) projEl.textContent = `₹${projectedTotal}`;
  }

  // =========================================================================
  // VIEW 6: SETTINGS
  // =========================================================================

  renderSettingsView() {
    const settings = db.getSettings();
    const prices = settings.prices || { Breakfast: 30, Lunch: 50, Dinner: 30 };
    const notifs = settings.notifications || {};

    const nameInput = document.getElementById('settings-user-name');
    const bfInput = document.getElementById('settings-price-breakfast');
    const luInput = document.getElementById('settings-price-lunch');
    const dnInput = document.getElementById('settings-price-dinner');

    const notifSwitch = document.getElementById('settings-notif-switch');
    const bfTimeInput = document.getElementById('settings-time-breakfast');
    const luTimeInput = document.getElementById('settings-time-lunch');
    const dnTimeInput = document.getElementById('settings-time-dinner');
    const inactSwitch = document.getElementById('settings-inact-switch');
    const inactTimeInput = document.getElementById('settings-time-inactivity');

    if (nameInput) nameInput.value = settings.userName || '';
    if (bfInput) bfInput.value = prices.Breakfast || 30;
    if (luInput) luInput.value = prices.Lunch || 50;
    if (dnInput) dnInput.value = prices.Dinner || 30;

    if (notifSwitch) notifSwitch.checked = !!notifs.enabled;
    if (bfTimeInput) bfTimeInput.value = notifs.breakfastTime || '10:00';
    if (luTimeInput) luTimeInput.value = notifs.lunchTime || '14:30';
    if (dnTimeInput) dnTimeInput.value = notifs.dinnerTime || '22:00';
    if (inactSwitch) inactSwitch.checked = !!notifs.inactivityCheck;
    if (inactTimeInput) inactTimeInput.value = notifs.inactivityTime || '21:30';

    // Save Settings Button
    const saveBtn = document.getElementById('save-settings-btn');
    if (saveBtn && !saveBtn.dataset.bound) {
      saveBtn.dataset.bound = 'true';
      saveBtn.addEventListener('click', () => {
        const updated = {
          userName: nameInput ? nameInput.value.trim() || 'User' : 'User',
          prices: {
            Breakfast: Number(bfInput ? bfInput.value : 30) || 30,
            Lunch: Number(luInput ? luInput.value : 50) || 50,
            Dinner: Number(dnInput ? dnInput.value : 30) || 30,
          },
          notifications: {
            enabled: notifSwitch ? notifSwitch.checked : true,
            breakfastTime: bfTimeInput ? bfTimeInput.value : '10:00',
            lunchTime: luTimeInput ? luTimeInput.value : '14:30',
            dinnerTime: dnTimeInput ? dnTimeInput.value : '22:00',
            inactivityCheck: inactSwitch ? inactSwitch.checked : true,
            inactivityTime: inactTimeInput ? inactTimeInput.value : '21:30',
          }
        };

        db.saveSettings(updated);
        notifier.showToast("Settings Saved", "Preferences and pricing rates updated.", "info", "⚙️");
        this.renderHeader();
        this.renderSidebarSummary();
      });
    }

    // Test Notification Button
    const testBtn = document.getElementById('test-notification-btn');
    if (testBtn && !testBtn.dataset.bound) {
      testBtn.dataset.bound = 'true';
      testBtn.addEventListener('click', async () => {
        await notifier.requestPermission();
        notifier.sendAlert("🔔 MealTrack AI Alert", "Notifications & audio chimes are fully active!");
      });
    }
  }

  // =========================================================================
  // PAST-DATE MEAL EDITOR MODAL
  // =========================================================================

  openDateModal(dateKey = null) {
    const modal = document.getElementById('date-editor-modal');
    if (!modal) return;

    const targetKey = dateKey || formatDateKey(new Date());
    const existingRec = db.getMeal(targetKey) || { breakfast: 0, lunch: 0, dinner: 0, outside_dinner: 0, bill: 0 };

    const dateInput = document.getElementById('modal-date-input');
    const bfCb = document.getElementById('modal-cb-breakfast');
    const luCb = document.getElementById('modal-cb-lunch');
    const dnCb = document.getElementById('modal-cb-dinner');
    const outInput = document.getElementById('modal-outside-dinner');
    const delBtn = document.getElementById('modal-delete-btn');

    // Convert DD-MM-YYYY to YYYY-MM-DD for HTML input[type="date"]
    const parts = targetKey.split('-');
    if (parts.length === 3 && dateInput) {
      dateInput.value = `${parts[2]}-${parts[1]}-${parts[0]}`;
    }

    if (bfCb) bfCb.checked = !!existingRec.breakfast;
    if (luCb) luCb.checked = !!existingRec.lunch;
    if (dnCb) dnCb.checked = !!existingRec.dinner;
    if (outInput) outInput.value = existingRec.outside_dinner || 0;

    if (delBtn) {
      delBtn.style.display = dateKey && db.getMeal(dateKey) ? 'inline-block' : 'none';
    }

    this.updateModalSundayUI(dateInput ? dateInput.value : '');
    modal.classList.add('open');
  }

  closeDateModal() {
    const modal = document.getElementById('date-editor-modal');
    if (modal) modal.classList.remove('open');
  }

  updateModalSundayUI(isoDateStr) {
    const sundayRow = document.getElementById('modal-sunday-row');
    if (!sundayRow || !isoDateStr) return;

    const d = new Date(isoDateStr + 'T00:00:00');
    const isSun = d.getDay() === 0;
    sundayRow.style.display = isSun ? 'flex' : 'none';
  }

  saveDateModalRecord() {
    const dateInput = document.getElementById('modal-date-input');
    const bfCb = document.getElementById('modal-cb-breakfast');
    const luCb = document.getElementById('modal-cb-lunch');
    const dnCb = document.getElementById('modal-cb-dinner');
    const outInput = document.getElementById('modal-outside-dinner');

    if (!dateInput || !dateInput.value) return;

    // Convert YYYY-MM-DD to DD-MM-YYYY
    const parts = dateInput.value.split('-');
    const dateKey = `${parts[2]}-${parts[1]}-${parts[0]}`;
    const dateObj = new Date(dateInput.value + 'T00:00:00');

    const mealStates = {
      Breakfast: bfCb ? (bfCb.checked ? 1 : 0) : 0,
      Lunch: luCb ? (luCb.checked ? 1 : 0) : 0,
      Dinner: dnCb ? (dnCb.checked ? 1 : 0) : 0,
    };

    const outsideDinner = outInput ? Number(outInput.value) || 0 : 0;
    const prices = db.getPrices();
    const bill = calculateBill(mealStates, prices, outsideDinner, dateObj);

    db.saveMeal(dateKey, mealStates, bill, outsideDinner);
    notifier.showToast("Record Saved", `Record for ${dateKey} (₹${bill}) saved.`, "info", "💾");

    this.closeDateModal();
    this.showView(this.currentView);
  }

  deleteDateModalRecord() {
    const dateInput = document.getElementById('modal-date-input');
    if (!dateInput || !dateInput.value) return;

    const parts = dateInput.value.split('-');
    const dateKey = `${parts[2]}-${parts[1]}-${parts[0]}`;

    if (confirm(`Delete meal record for ${dateKey}?`)) {
      db.deleteMeal(dateKey);
      notifier.showToast("Record Removed", `Record for ${dateKey} deleted.`, "warning", "🗑️");
      this.closeDateModal();
      this.showView(this.currentView);
    }
  }

  // =========================================================================
  // DATA BACKUP & RESTORE
  // =========================================================================

  handleExportBackup() {
    const jsonStr = db.exportDataJSON();
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `MealTrackAI_Backup_${formatDateKey(new Date())}.json`;
    a.click();
    URL.revokeObjectURL(url);
    notifier.showToast("Backup Created", "Meal records downloaded as JSON.", "info", "📦");
  }

  handleImportBackup(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      const result = db.importDataJSON(evt.target.result);
      if (result.success) {
        notifier.showToast("Restore Successful", `Restored ${result.count} meal records from backup!`, "info", "✅");
        this.showView(this.currentView);
      } else {
        notifier.showToast("Restore Failed", result.error || "Could not read backup file.", "warning", "⚠️");
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  }
}

function escapeHTML(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Instantiate on DOM load
document.addEventListener('DOMContentLoaded', () => {
  window.mealTrackApp = new MealTrackApp();
});
