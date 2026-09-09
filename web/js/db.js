/**
 * MealTrack AI - Database & Storage Layer
 * Manages persistent storage with localStorage & provides full JSON backup/restore.
 */

import { DEFAULT_PRICES, DEFAULT_USER_NAME, DEFAULT_NOTIFICATIONS, STORAGE_KEYS } from './constants.js';

class MealDatabase {
  constructor() {
    this.init();
  }

  init() {
    if (!localStorage.getItem(STORAGE_KEYS.MEALS)) {
      localStorage.setItem(STORAGE_KEYS.MEALS, JSON.stringify({}));
    }
    if (!localStorage.getItem(STORAGE_KEYS.SETTINGS)) {
      const defaultSettings = {
        userName: DEFAULT_USER_NAME,
        prices: { ...DEFAULT_PRICES },
        notifications: { ...DEFAULT_NOTIFICATIONS },
      };
      localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(defaultSettings));
    }
  }

  // --- Meal Records CRUD ---

  getAllMeals() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.MEALS);
      return data ? JSON.parse(data) : {};
    } catch (e) {
      console.error("Failed to load meals from storage:", e);
      return {};
    }
  }

  getMeal(dateStr) {
    const meals = this.getAllMeals();
    return meals[dateStr] || null;
  }

  saveMeal(dateStr, mealStates, bill, outsideDinner = 0) {
    const meals = this.getAllMeals();
    meals[dateStr] = {
      date: dateStr,
      breakfast: mealStates.Breakfast ? 1 : 0,
      lunch: mealStates.Lunch ? 1 : 0,
      dinner: mealStates.Dinner ? 1 : 0,
      outside_dinner: Number(outsideDinner) || 0,
      bill: Number(bill) || 0,
      updatedAt: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEYS.MEALS, JSON.stringify(meals));
    return meals[dateStr];
  }

  deleteMeal(dateStr) {
    const meals = this.getAllMeals();
    if (meals[dateStr]) {
      delete meals[dateStr];
      localStorage.setItem(STORAGE_KEYS.MEALS, JSON.stringify(meals));
      return true;
    }
    return false;
  }

  // --- Settings CRUD ---

  getSettings() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.SETTINGS);
      return data ? JSON.parse(data) : {
        userName: DEFAULT_USER_NAME,
        prices: { ...DEFAULT_PRICES },
        notifications: { ...DEFAULT_NOTIFICATIONS },
      };
    } catch (e) {
      return {
        userName: DEFAULT_USER_NAME,
        prices: { ...DEFAULT_PRICES },
        notifications: { ...DEFAULT_NOTIFICATIONS },
      };
    }
  }

  saveSettings(settings) {
    localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(settings));
  }

  getPrices() {
    const settings = this.getSettings();
    return settings.prices || { ...DEFAULT_PRICES };
  }

  getUserName() {
    const settings = this.getSettings();
    return settings.userName || DEFAULT_USER_NAME;
  }

  // --- Backup & Restore ---

  exportDataJSON() {
    const exportObject = {
      version: 1,
      exportedAt: new Date().toISOString(),
      meals: this.getAllMeals(),
      settings: this.getSettings(),
    };
    return JSON.stringify(exportObject, null, 2);
  }

  importDataJSON(jsonString) {
    try {
      const data = JSON.parse(jsonString);
      if (data && typeof data === 'object') {
        if (data.meals) {
          localStorage.setItem(STORAGE_KEYS.MEALS, JSON.stringify(data.meals));
        }
        if (data.settings) {
          localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(data.settings));
        }
        return { success: true, count: Object.keys(data.meals || {}).length };
      }
      return { success: false, error: "Invalid backup file structure." };
    } catch (e) {
      return { success: false, error: e.message };
    }
  }

  clearAllData() {
    localStorage.removeItem(STORAGE_KEYS.MEALS);
    localStorage.removeItem(STORAGE_KEYS.SETTINGS);
    this.init();
  }
}

export const db = new MealDatabase();
