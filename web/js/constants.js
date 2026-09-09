/**
 * MealTrack AI - Global Constants & Configuration
 */

export const APP_TITLE = "MealTrack AI";
export const DEFAULT_USER_NAME = "Sowmya";

export const DEFAULT_PRICES = {
  Breakfast: 30,
  Lunch: 50,
  Dinner: 30,
};

export const MEAL_ICONS = {
  Breakfast: "🍳",
  Lunch: "🍛",
  Dinner: "🌙",
};

export const MEAL_COLORS = {
  Breakfast: {
    bg: "#382315",
    border: "#6E3F1A",
    accent: "#F59E0B",
  },
  Lunch: {
    bg: "#133132",
    border: "#1D5456",
    accent: "#10B981",
  },
  Dinner: {
    bg: "#271B3D",
    border: "#4E2F7C",
    accent: "#A855F7",
  },
};

export const DEFAULT_NOTIFICATIONS = {
  enabled: true,
  breakfastTime: "10:00",
  lunchTime: "14:30",
  dinnerTime: "22:00",
  inactivityCheck: true,
  inactivityTime: "21:30",
};

export const STORAGE_KEYS = {
  MEALS: "mealtrack_meals_v1",
  SETTINGS: "mealtrack_settings_v1",
};
