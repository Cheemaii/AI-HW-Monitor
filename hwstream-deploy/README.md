# HWStream — Live PC Sensor Dashboard

Stream your HWiNFO64 sensor data to a public website in real time.

---

## Project Structure

```
hwmonitor/
├── backend/
│   ├── server.js       ← Node.js server (WebSocket + REST API + serves frontend)
│   └── package.json
├── frontend/
│   └── index.html      ← Dashboard UI
└── hwstream.py         ← Python uploader (runs on your PC)
```

---

## Deploying the Server (free on Railway)

1. Push this folder to a GitHub repo
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your repo, Railway auto-detects Node.js
4. Set the **root directory** to `backend/`
5. Railway gives you a public URL like `https://hwstream-xyz.up.railway.app`

**OR use Render.com:**
1. New Web Service → connect GitHub repo
2. Root directory: `backend`
3. Build command: `npm install`
4. Start command: `node server.js`

---

## HWiNFO64 Setup

1. Open HWiNFO64 → click **Sensors**
2. In the Sensors window → **Settings** (wrench icon)
3. Check **"Log all values to file"**
4. Set **Logging interval** to `2000` ms
5. Note the CSV file path shown (e.g. `C:\Users\you\HWiNFO64.CSV`)
6. Click OK — logging starts immediately

---

## Running the Uploader

Install Python dependency:
```bash
pip install requests
```

Run the uploader:
```bash
python hwstream.py \
  --csv "C:\Users\YourName\HWiNFO64.CSV" \
  --token your-unique-token \
  --server https://your-railway-url.up.railway.app
```

**Token tips:**
- Use anything unique: `zain-pc`, `gaming-rig-2025`, `my-server`
- Your dashboard URL will be: `https://your-server/dashboard/your-token`
- Share that URL with anyone — they see your live stats

---

## Running Locally (dev)

```bash
cd backend
npm install
node server.js
```

Open `http://localhost:3001` in your browser.

Run the uploader pointing to `http://localhost:3001`.

---

## How It Works

```
HWiNFO64 → CSV file → hwstream.py → POST /api/upload/:token
                                              ↓
                                    Server stores + broadcasts
                                              ↓
                              Browser ←── WebSocket ──── Dashboard
```

- The Python script watches the CSV file and POSTs new rows every 2 seconds
- The server holds the latest snapshot per token in memory
- The dashboard connects via WebSocket and receives live updates instantly
- Multiple people can watch the same token simultaneously

---

## Sensor Categories

The uploader auto-categorizes sensors by keyword matching:

| Category | Color  | Detected by keywords |
|----------|--------|---------------------|
| CPU      | Green  | cpu, core, package, tdie |
| GPU      | Cyan   | gpu, vram, video |
| RAM      | Purple | ram, memory, dram |
| Fans     | Blue   | fan, rpm, cooler |
| Voltages | Yellow | volt, vcore, vdd |
| Storage  | Orange | drive, disk, nvme, ssd |

---

## Thresholds (auto color coding)

| Sensor | Warn | Danger |
|--------|------|--------|
| Temp (°C) | ≥ 75 | ≥ 90 |
| Load (%)  | ≥ 80 | ≥ 95 |
| Fan (RPM) | < 200 | = 0 |
