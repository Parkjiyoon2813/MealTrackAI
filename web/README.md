# 🚀 MealTrack AI — Live Web Application on Vercel

MealTrack AI is now ready to run live on the web with full desktop and mobile support, persistent local storage, and real-time reminders!

---

## 🌐 Deploy to Vercel (Step-by-Step)

### Option 1: Instant 1-Click Import (Recommended)
1. Commit and push your code to your GitHub repository:
   ```bash
   git add .
   git commit -m "feat: add isolated live web app for Vercel"
   git push origin master
   ```
2. Open **[vercel.com](https://vercel.com)** and log in with GitHub.
3. Click **"Add New..."** → **"Project"**.
4. Select your **`MealTrackAI`** repository.
5. Click **Deploy**!
   *(The included root `vercel.json` automatically routes traffic directly to the `web/` app).*
6. Your live website URL will be ready instantly (e.g. `https://mealtrackai.vercel.app`)!

---

### Option 2: Deploying via Vercel CLI
If you have the Vercel CLI installed:
```bash
cd web
vercel
```

---

## ✨ Web Features
- **Zero Config Hosting**: Powered entirely by modern Web Standards (HTML5, Vanilla CSS3, ES Modules).
- **Persistent Data**: Stores all meal records, past dates, and custom rates directly in your browser.
- **Backup & Restore**: Easily download all your records as a JSON file or restore on any new phone/device.
- **PWA (Install as App)**: Can be added directly to your phone or desktop home screen.
- **Smart Reminders**: Desktop browser notifications + pleasant chime alerts.
