# Smart Kitchen: setup guide for a first-time user

This guide takes you from a clean computer to a working demo: a Python backend on your laptop, plus a phone app that talks to it. It assumes you have never used any of these tools. Allow about 45 minutes.

## What you are running

| Part | What it is | Where it runs |
|---|---|---|
| `backend/` | FastAPI server and SQLite database. Stores the kitchen items, reads barcodes from photos, looks up products, suggests recipes, creates expiry alerts. | Your laptop |
| `mobile/` | The phone app (React Native with Expo). Shows items, scans barcodes, shows recipes and alerts. | Your phone, inside the Expo Go app |
| `firmware/` | Code for the real ESP32 barcode scanner. **Not needed for the demo.** The backend has a simulated scanner instead. | n/a |

The phone and the laptop must be on the **same Wi-Fi network**. A phone hotspot also works: connect the laptop to it.

## What is required and what is optional

| Service | Needed for the demo? | What you lose without it |
|---|---|---|
| Python, Node.js, Git, Expo Go | **Yes** | Nothing runs |
| Gemini API key | Optional | Recipes come only from the built-in dataset. Gemini is a fallback when fewer than 3 recipes match. |
| Firebase | Optional, and see the warning in Part 5 | Alerts are still created, stored and shown in the app's Alerts tab. They are just not pushed to the phone. |

Do Parts 1 to 4 first and get the demo working. Then add Gemini (Part 5) and Firebase (Part 6) if you want them.

---

## Part 1: Install the tools

Install each tool once. Afterwards, open a **new** terminal window so the new commands are found.

### 1.1 Git
- **Windows:** download from https://git-scm.com/download/win and install with the default options.
- **macOS:** run `xcode-select --install` in Terminal.
- **Linux (Ubuntu or Debian):** `sudo apt install git`

Check: `git --version`

### 1.2 Python 3.10 or newer
- **Windows:** download from https://www.python.org/downloads/. On the first installer screen, **tick "Add python.exe to PATH"**.
- **macOS:** `brew install python` (get Homebrew from https://brew.sh first), or use the installer from python.org.
- **Linux:** `sudo apt install python3 python3-venv python3-pip`

Check: `python --version` on Windows, or `python3 --version` on macOS and Linux. On macOS and Linux use `python3` wherever this guide says `python`.

### 1.3 The barcode reading library (zbar)
The backend uses it to read barcodes from photos.
- **Windows:** nothing to install. If you later see an error mentioning `libzbar` or a missing DLL, install the "Visual C++ Redistributable Packages for Visual Studio 2013" from Microsoft.
- **macOS:** `brew install zbar`
- **Linux:** `sudo apt install libzbar0`

### 1.4 Node.js 20 or newer (22 recommended)
Download the LTS version from https://nodejs.org and install it with the defaults.

Check: `node --version` and `npm --version`

### 1.5 Expo Go on your phone
Install **Expo Go** from the App Store (iPhone) or Google Play (Android). It is free, and you do not need an account for this demo.

---

## Part 2: Get the code

```bash
git clone https://github.com/Yogesh1101/kamal.git
cd kamal
git checkout main
```

If the repository is private, GitHub will ask you to sign in, and the owner must first add you as a collaborator. The code is on the `main` branch, which has the backend, the app and the firmware.

---

## Part 3: Run the backend

Open a terminal and keep it open for the whole demo. This is **terminal 1**.

### 3.1 Create the Python environment and install packages (once)

macOS and Linux:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell says scripts are disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, and try again.

The install takes a few minutes. After activation you will see `(.venv)` at the start of the prompt. You must activate again in every new terminal with the `source` or `Activate.ps1` line, not the `pip install` line.

### 3.2 Create the settings file (optional for now)
The backend works with no settings file. It then has no Gemini and no push, which is fine for a first run. Skip to 3.3. You will create `backend/.env` in Parts 5 and 6.

### 3.3 Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` lets your phone reach the server. Without it, only the laptop can.

The database file `backend/kitchen.db` is created automatically on the first start, with the default categories already in it.

You should see lines ending with `Application startup complete`. A warning that says `FIREBASE_CREDENTIALS not set` is expected until Part 6.

### 3.4 Check that it works
Open http://127.0.0.1:8000/docs in a browser. You get an interactive page that lists every endpoint. You can try any of them with the "Try it out" button.

You can also run `curl http://127.0.0.1:8000/api/v1/health`, which should return `{"data":{"status":"ok"}}`.

### 3.5 Allow the phone through the firewall
- **Windows:** the first time, a "Windows Defender Firewall" popup appears for Python. Tick **Private networks** and click Allow. If you missed it, search for "Allow an app through Windows Firewall" and allow Python.
- **macOS:** click Allow if it asks about incoming connections.
- **Linux with ufw:** `sudo ufw allow 8000/tcp`

---

## Part 4: Run the phone app

### 4.1 Find your laptop's IP address
The phone needs this address to reach the backend.
- **Windows:** run `ipconfig` and look for "IPv4 Address" under your Wi-Fi adapter.
- **macOS:** run `ipconfig getifaddr en0`
- **Linux:** run `ip -4 addr` and look for the address under your Wi-Fi interface, for example `192.168.1.23`.

It usually looks like `192.168.x.x`, `10.x.x.x` or `172.x.x.x`. Do not use `127.0.0.1`, because on the phone that means the phone itself. **The address changes when you switch Wi-Fi networks**, so check it again before each demo.

### 4.2 Install the app's packages (once)
Open a second terminal. This is **terminal 2**.
```bash
cd kamal/mobile
npm install
```

### 4.3 Tell the app where the backend is
Create a file named `.env` inside the `mobile/` folder, with this single line. Replace the address with yours from 4.1:

```
EXPO_PUBLIC_API_URL=http://192.168.1.23:8000/api/v1
```

Keep `http://` (not https), the port `8000`, and the `/api/v1` at the end.

### 4.4 Start the app

```bash
npx expo start -c
```

The `-c` clears the cache. Always use it after you change `.env`, because the value is baked in when the app starts. A QR code appears in the terminal.

- **iPhone:** open the normal Camera app, point it at the QR code and tap the banner. It opens in Expo Go.
- **Android:** open Expo Go, tap "Scan QR code" and scan it.

The first load takes a minute while it bundles. You will see four tabs: **Kitchen, Scan, Recipes, Alerts**.

If the app cannot connect, check these in order:
1. The phone and laptop are on the same network.
2. The IP in `mobile/.env` is current.
3. http://YOUR-IP:8000/docs opens in the **phone's browser**. If it does not, the problem is the firewall (3.5) or `--host 0.0.0.0` was missed (3.3).
4. Some office, college and guest Wi-Fi networks block devices from talking to each other (client isolation). Use a phone hotspot instead.
5. If only the Expo QR code fails to connect, try `npx expo start --tunnel` instead. It asks to install `@expo/ngrok` once.

---

## Part 5: Gemini API key (optional, for recipe fallback)

Gemini only runs when the built-in recipe dataset gives fewer than 3 good matches for the items in the kitchen. Answers are cached in the database.

1. Go to https://aistudio.google.com/apikey and sign in with a Google account.
2. Click **Create API key**. Choose or create a Google Cloud project when asked.
3. Copy the key. It starts with `AIza`.
4. Create the file `backend/.env` with this line (no quotes, no spaces around `=`):
   ```
   GEMINI_API_KEY=paste-your-key-here
   ```
5. Stop the backend with Ctrl+C and start it again (step 3.3). The `.env` file is only read at startup.

**If recipes return an error:** model names change and free-tier access varies by account. The backend tries models in order and skips any that are busy or missing. To choose your own, add this line to `backend/.env` using any model name listed at https://ai.google.dev/gemini-api/docs/models :
```
GEMINI_MODELS=gemini-2.5-flash,gemini-2.5-flash-lite
```
Free keys have rate limits, so a "429" or "503" error from Gemini just means wait a minute and retry. The key is a secret. Never commit it or share it in chat.

---

## Part 6: Firebase (optional, backend push only)

> **Read this first.** In the current code, the backend is ready to send push notifications, but **the phone app does not yet register itself for push**. It has no notification package and never sends a device token to the backend. So setting up Firebase will not make notifications appear on the phone, and Expo Go cannot receive FCM pushes at all. For the demo, the **Alerts tab** shows every alert from the database, and the **Run expiry check now** button creates them on demand. Only do this part if you plan to finish the push feature. It also needs a development build, not Expo Go, and only works on Android.

If you do want it:

1. Go to https://console.firebase.google.com and sign in with a Google account.
2. Click **Create a project** (or Add project). Name it anything, for example `smart-kitchen`. You can turn Google Analytics off. Click Create.
3. **Server key for the backend:**
   1. Click the gear icon next to "Project Overview", then **Project settings**.
   2. Open the **Service accounts** tab and click **Generate new private key**, then confirm.
   3. A `.json` file downloads. Move it to the `backend/` folder and rename it `firebase-key.json`. The repository's `.gitignore` already keeps files named `*firebase*.json` out of git.
   4. Add this line to `backend/.env`:
      ```
      FIREBASE_CREDENTIALS=firebase-key.json
      ```
   5. Restart the backend. The log should now say `Firebase initialised` instead of the warning.
4. **Android app registration (for the future app work):** in Project settings, under "Your apps", click the Android icon. Use the package name `com.yogesh.smartkitchen`, register the app, and download `google-services.json`. It is used when building the Android development build.

Never commit the key file or share it. Anyone holding it can send messages as your project.

---

## Part 7: Demo script

With both terminals running and the app open on the phone:

1. **Add an item with a barcode.** There is no scanner hardware, so use the API. Open http://127.0.0.1:8000/docs, expand `POST /api/v1/scans/codes`, click **Try it out**, and send:
   ```json
   {"code": "3017620422003"}
   ```
   The backend looks the product up on Open Food Facts (this needs internet) and adds it to the kitchen. In the app, go to the **Kitchen** tab and pull down to refresh. The new item appears with a pre-filled expiry date.
2. **Add a home-made item** with a kitchen QR label code in the same box:
   ```json
   {"code": "SKI:{\"name\": \"Paneer\", \"category\": \"dairy\"}"}
   ```
3. **Scan from the phone.** In the **Scan** tab, take or pick a photo of a real product barcode. The app sends it to the backend, which decodes it.
4. **Simulated scanner with the laptop webcam** (stands in for the ESP32 scanner). In a third terminal, from `kamal/backend` with the environment activated:
   ```bash
   python tools/scanner_sim.py
   ```
   Hold a barcode up to the webcam. Press SPACE to scan and Q to quit. You can also pass image files: `python tools/scanner_sim.py photo.jpg`.
5. **Recipes tab:** shows dishes ranked by which of your items expire soonest.
6. **Alerts tab:** tap **Run expiry check now**. Items close to or past their expiry produce alerts, which are listed here.
7. **Edit an expiry date** by opening an item in the Kitchen tab and changing the date, then rerun the expiry check to see the alert change.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python` or `pip` not found | Reopen the terminal. On Windows, reinstall Python with "Add to PATH" ticked. On macOS and Linux, use `python3`. |
| `ImportError: Unable to find zbar shared library` | Install zbar (step 1.3), then reopen the terminal. |
| `Address already in use` on port 8000 | Another copy of the backend is running. Close it, or add `--port 8001` and change the port in `mobile/.env`. |
| App says "Backend address not set" | `mobile/.env` is missing or misnamed. Create it (step 4.3) and restart with `npx expo start -c`. |
| App shows a network error | Follow the numbered checks at the end of Part 4. |
| Barcode lookup says "not found" | The product is not in Open Food Facts, or there is no internet. Try the Nutella code from the demo script. |
| Recipes show an error | See the Gemini notes in Part 5. The dataset recipes still work without a key. |
| Everything is wrong after pulling new code | In `backend/`, rerun `pip install -r requirements.txt`. In `mobile/`, rerun `npm install`, then `npx expo start -c`. |
| Want to reset all data | Stop the backend and delete `backend/kitchen.db`. It is recreated empty on the next start. |

## Keep secrets out of git
`backend/.env` and `backend/firebase-key.json` hold secrets and are already ignored by git. `google-services.json` is **not** ignored, so keep it outside the repository folder, or add it to `.gitignore` before running `git add`. `mobile/.env` only holds your laptop's local IP and is also ignored.
