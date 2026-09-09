/**
 * MealTrack AI - Business Logic & Calculation Engines
 */

import { DEFAULT_PRICES } from './constants.js';

/**
 * Format a Date object to "DD-MM-YYYY"
 */
export function formatDateKey(dateObj = new Date()) {
  const d = String(dateObj.getDate()).padStart(2, '0');
  const m = String(dateObj.getMonth() + 1).padStart(2, '0');
  const y = dateObj.getFullYear();
  return `${d}-${m}-${y}`;
}

/**
 * Parse a "DD-MM-YYYY" string into a Date object
 */
export function parseDateKey(dateStr) {
  if (!dateStr) return new Date();
  if (dateStr instanceof Date) return dateStr;
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const year = parseInt(parts[2], 10);
    return new Date(year, month, day);
  }
  return new Date();
}

/**
 * Check if given date is Sunday (0 in JS getDay())
 */
export function isSunday(dateInput = new Date()) {
  const d = typeof dateInput === 'string' ? parseDateKey(dateInput) : dateInput;
  return d.getDay() === 0;
}

/**
 * Get dynamic greeting based on hour of day
 */
export function getGreeting(dateObj = new Date()) {
  const hour = dateObj.getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 17) return "Good Afternoon";
  return "Good Evening";
}

/**
 * Format date for display pill e.g. "Wednesday, 09 September 2026"
 */
export function getDisplayDate(dateObj = new Date()) {
  return dateObj.toLocaleDateString('en-US', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  });
}

/**
 * Calculate total bill based on meal states and Sunday outside dinner rule
 */
export function calculateBill(mealStates, prices = DEFAULT_PRICES, outsideDinner = 0, dateInput = new Date()) {
  let total = 0;
  const isSun = isSunday(dateInput);

  if (mealStates.Breakfast) {
    total += Number(prices.Breakfast) || 30;
  }
  if (mealStates.Lunch) {
    total += Number(prices.Lunch) || 50;
  }
  if (mealStates.Dinner) {
    if (isSun) {
      total += Number(outsideDinner) || 0;
    } else {
      total += Number(prices.Dinner) || 30;
    }
  }

  return total;
}

/**
 * Fetch monthly summary with all KPIs and analytics
 */
export function getMonthlySummary(allMealsMap, targetYear, targetMonth, prices = DEFAULT_PRICES) {
  // targetMonth is 0-indexed (0 = Jan, 8 = Sep)
  const targetMonthStr = String(targetMonth + 1).padStart(2, '0');
  const targetYearStr = String(targetYear);

  const monthRecords = [];
  for (const dateKey of Object.keys(allMealsMap)) {
    const parts = dateKey.split('-');
    if (parts.length === 3 && parts[1] === targetMonthStr && parts[2] === targetYearStr) {
      monthRecords.push(allMealsMap[dateKey]);
    }
  }

  // Sort chronological
  monthRecords.sort((a, b) => {
    const da = parseDateKey(a.date);
    const db = parseDateKey(b.date);
    return da - db;
  });

  const daysInMonth = new Date(targetYear, targetMonth + 1, 0).getDate();
  const daysRecorded = monthRecords.length;
  const totalSpent = monthRecords.reduce((sum, r) => sum + (Number(r.bill) || 0), 0);
  const totalMeals = monthRecords.reduce((sum, r) => sum + (r.breakfast ? 1 : 0) + (r.lunch ? 1 : 0) + (r.dinner ? 1 : 0), 0);
  const totalPossibleMeals = daysInMonth * 3;
  const averageSpending = daysRecorded > 0 ? totalSpent / daysRecorded : 0;

  let highestDay = null;
  let lowestDay = null;
  if (monthRecords.length > 0) {
    highestDay = monthRecords.reduce((max, r) => (r.bill > max.bill ? r : max), monthRecords[0]);
    lowestDay = monthRecords.reduce((min, r) => (r.bill < min.bill ? r : min), monthRecords[0]);
  }

  // Distribution breakdown
  let bfCount = 0, luCount = 0, dnCount = 0;
  let bfSpend = 0, luSpend = 0, dnSpend = 0;

  const bfPrice = Number(prices.Breakfast) || 30;
  const luPrice = Number(prices.Lunch) || 50;
  const dnPrice = Number(prices.Dinner) || 30;

  monthRecords.forEach(r => {
    if (r.breakfast) {
      bfCount++;
      bfSpend += bfPrice;
    }
    if (r.lunch) {
      luCount++;
      luSpend += luPrice;
    }
    if (r.dinner) {
      dnCount++;
      if (isSunday(r.date) && r.outside_dinner > 0) {
        dnSpend += Number(r.outside_dinner);
      } else {
        dnSpend += dnPrice;
      }
    }
  });

  return {
    year: targetYear,
    month: targetMonth,
    monthLabel: new Date(targetYear, targetMonth, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
    daysInMonth,
    daysRecorded,
    totalSpent,
    totalMeals,
    totalPossibleMeals,
    averageSpending,
    highestDay,
    lowestDay,
    records: monthRecords,
    breakdown: {
      breakfast: { count: bfCount, spend: bfSpend },
      lunch: { count: luCount, spend: luSpend },
      dinner: { count: dnCount, spend: dnSpend },
    }
  };
}

/**
 * Get spending for last N days for trend chart
 */
export function getRecentSpendingTrend(allMealsMap, limit = 7) {
  const today = new Date();
  const items = [];

  for (let i = limit - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const key = formatDateKey(d);
    const rec = allMealsMap[key];
    items.push({
      dateKey: key,
      dayNum: d.getDate(),
      dayName: d.toLocaleDateString('en-US', { weekday: 'short' }),
      bill: rec ? Number(rec.bill) || 0 : 0,
      hasRecord: !!rec,
      isToday: i === 0,
    });
  }

  return items;
}

/**
 * Generate smart quick insights
 */
export function getQuickInsights(summary) {
  if (!summary || summary.daysRecorded === 0) {
    return [
      "Save today's meals to start building your monthly insights.",
      "A full week of records will make spending trends much more accurate.",
      "Keep Sunday dinner tracked separately when having outside food.",
    ];
  }

  const insights = [];
  const avgMealsPerDay = summary.totalMeals / summary.daysRecorded;

  if (avgMealsPerDay >= 2.5) {
    insights.push("You are consistently eating and logging all 3 meals daily!");
  } else if (avgMealsPerDay >= 1.5) {
    insights.push("Your meal tracking is steady, with room to catch missing meals.");
  } else {
    insights.push("Meal tracking is sparse this month—every marked day keeps spending clear.");
  }

  if (summary.averageSpending <= 65) {
    insights.push("Your average daily spending is currently on the very affordable side.");
  } else if (summary.averageSpending <= 95) {
    insights.push("Your average daily spending looks balanced and well controlled.");
  } else {
    insights.push("Your daily average is trending higher—outside meals have the biggest impact.");
  }

  if (summary.highestDay && summary.lowestDay) {
    insights.push(`Your spending range runs from ₹${summary.lowestDay.bill} to ₹${summary.highestDay.bill} this month.`);
  }

  return insights.slice(0, 3);
}

/**
 * Generate personalized motivation quote
 */
export function getMotivationMessage(summary) {
  if (!summary || summary.daysRecorded === 0) {
    return "A small check-in today turns this dashboard into a powerful lifelong habit.";
  }

  if (summary.totalMeals >= summary.daysRecorded * 2.5) {
    return "Outstanding consistency! You're staying disciplined with your mess meals.";
  }

  if (summary.averageSpending <= 80) {
    return "You are doing great balancing daily nourishment with smart spending control.";
  }

  return "Stay with it! Even one well-tracked day makes your monthly budget crystal clear.";
}

/**
 * Get Day of Week distribution (Mon - Sun)
 */
export function getDayOfWeekDistribution(allMealsMap) {
  const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const counts = [0, 0, 0, 0, 0, 0, 0];
  const spends = [0, 0, 0, 0, 0, 0, 0];

  Object.values(allMealsMap).forEach(rec => {
    const d = parseDateKey(rec.date);
    const dayIdx = d.getDay();
    counts[dayIdx]++;
    spends[dayIdx] += Number(rec.bill) || 0;
  });

  return days.map((name, idx) => ({
    name,
    count: counts[idx],
    spend: spends[idx],
    avg: counts[idx] > 0 ? Math.round(spends[idx] / counts[idx]) : 0,
  }));
}
