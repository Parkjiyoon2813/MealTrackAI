/**
 * MealTrack AI - Smart Notifications & Reminders Engine
 * Handles Toast Banners, Browser Push Alerts, and Audio Chimes.
 */

import { db } from './db.js';
import { formatDateKey } from './logic.js';

class NotificationService {
  constructor() {
    this.audioCtx = null;
    this.sentToday = new Set();
    this.lastCheckedDay = new Date().getDate();
    this.initAudio();
  }

  initAudio() {
    // Create audio context on first user interaction
    const unlockAudio = () => {
      if (!this.audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
          this.audioCtx = new AudioContext();
        }
      }
      document.removeEventListener('click', unlockAudio);
      document.removeEventListener('touchstart', unlockAudio);
    };
    document.addEventListener('click', unlockAudio);
    document.addEventListener('touchstart', unlockAudio);
  }

  playChime() {
    try {
      if (!this.audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) this.audioCtx = new AudioContext();
      }
      if (this.audioCtx && this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }
      if (!this.audioCtx) return;

      const now = this.audioCtx.currentTime;
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc.type = 'sine';
      // Dual pleasant tone
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.15); // A5

      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc.start(now);
      osc.stop(now + 0.4);
    } catch (e) {
      console.warn("Audio chime could not play:", e);
    }
  }

  async requestPermission() {
    if (!("Notification" in window)) {
      this.showToast("Notifications Not Supported", "Your browser does not support desktop notifications, but in-app toasts are active.", "warning");
      return false;
    }

    if (Notification.permission === "granted") {
      return true;
    }

    if (Notification.permission !== "denied") {
      const permission = await Notification.requestPermission();
      return permission === "granted";
    }

    return false;
  }

  sendAlert(title, message, icon = "🔔") {
    // 1. Play chime sound
    this.playChime();

    // 2. In-app Toast Banner
    this.showToast(title, message, "info", icon);

    // 3. Browser Native Notification
    if ("Notification" in window && Notification.permission === "granted") {
      try {
        new Notification(title, {
          body: message,
          icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍽️</text></svg>",
          tag: "mealtrack-alert",
        });
      } catch (e) {
        console.warn("Native notification failed:", e);
      }
    }
  }

  showToast(title, message, type = "info", icon = "🔔", duration = 5000) {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast-item toast-${type}`;

    toast.innerHTML = `
      <div class="toast-icon">${icon}</div>
      <div class="toast-content">
        <div class="toast-title">${escapeHTML(title)}</div>
        <div class="toast-message">${escapeHTML(message)}</div>
      </div>
      <button class="toast-close" aria-label="Close">✕</button>
    `;

    toast.querySelector(".toast-close").addEventListener("click", () => {
      toast.classList.add("toast-hiding");
      setTimeout(() => toast.remove(), 300);
    });

    container.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) {
        toast.classList.add("toast-hiding");
        setTimeout(() => toast.remove(), 300);
      }
    }, duration);
  }

  startPeriodicChecker() {
    // Check every 30 seconds
    setInterval(() => this.checkReminders(), 30000);
    // Initial check after 3 seconds
    setTimeout(() => this.checkReminders(), 3000);
  }

  checkReminders() {
    const today = new Date();
    if (today.getDate() !== this.lastCheckedDay) {
      this.sentToday.clear();
      this.lastCheckedDay = today.getDate();
    }

    const settings = db.getSettings();
    const notifs = settings.notifications || {};
    if (!notifs.enabled) return;

    const currentHHMM = `${String(today.getHours()).padStart(2, '0')}:${String(today.getMinutes()).padStart(2, '0')}`;
    const todayKey = formatDateKey(today);
    const todayRecord = db.getMeal(todayKey) || { breakfast: 0, lunch: 0, dinner: 0 };

    // 1. Breakfast check
    if (notifs.breakfastTime && currentHHMM >= notifs.breakfastTime && !this.sentToday.has("breakfast")) {
      if (!todayRecord.breakfast) {
        this.sentToday.add("breakfast");
        this.sendAlert("🍳 Breakfast Reminder", "Don't forget to mark your Breakfast in MealTrack AI!");
      }
    }

    // 2. Lunch check
    if (notifs.lunchTime && currentHHMM >= notifs.lunchTime && !this.sentToday.has("lunch")) {
      if (!todayRecord.lunch) {
        this.sentToday.add("lunch");
        this.sendAlert("🍛 Lunch Reminder", "Did you have lunch? Update today's record in MealTrack AI.");
      }
    }

    // 3. Dinner check
    if (notifs.dinnerTime && currentHHMM >= notifs.dinnerTime && !this.sentToday.has("dinner")) {
      if (!todayRecord.dinner) {
        this.sentToday.add("dinner");
        this.sendAlert("🌙 Dinner Reminder", "Remember to log your dinner or outside meal for today.");
      }
    }

    // 4. Evening inactivity check
    if (notifs.inactivityCheck && notifs.inactivityTime && currentHHMM >= notifs.inactivityTime && !this.sentToday.has("inactivity")) {
      const totalLogged = (todayRecord.breakfast ? 1 : 0) + (todayRecord.lunch ? 1 : 0) + (todayRecord.dinner ? 1 : 0);
      if (totalLogged === 0) {
        this.sentToday.add("inactivity");
        this.sendAlert("⚠️ Daily Meal Audit Pending", "You haven't marked any meals today. Take 10 seconds to keep your tracker up to date!");
      }
    }
  }
}

function escapeHTML(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export const notifier = new NotificationService();
