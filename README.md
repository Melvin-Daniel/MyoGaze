# NeuroShift — Product README

**NeuroShift** is a deployable assistive smart-home control product:

> **Looking selects. Muscle confirms. Unsure → Abstain.**

Works on **desktop and mobile** via the Control App PWA. No camera needed for mock demos.

---

## Control App (recommended)

### 1) Install

```powershell
cd C:\Users\MELVIN\Projects\NeuroShift
python -m pip install -r requirements.txt
cd web
npm install
npm run build
cd ..
```

### 2) Run (PC + phone on same Wi‑Fi)

```powershell
python -m src.neuroshift serve
```

- PC: http://127.0.0.1:8000  
- Phone: http://YOUR_PC_LAN_IP:8000 (Chrome → Add to Home Screen for app-like use)  
- API docs: http://127.0.0.1:8000/docs  

### Dev mode (hot reload UI)

Terminal A:
```powershell
python -m src.neuroshift serve --reload
```

Terminal B:
```powershell
cd web
npm run dev
```
UI: http://127.0.0.1:5173 (proxies API/WebSocket to :8000)

### Docker deploy

```powershell
cd web
npm run build
cd ..
docker compose up --build
```

App: http://127.0.0.1:8000

---

## App screens

| Tab | What it does |
|---|---|
| **Home** | Device ON/OFF + last intention + start mock demo |
| **Demo** | Live pipeline preview stream (mock, no camera) |
| **Log** | Decision timeline with human-readable reasons |
| **Stats** | Acts / Abstains / toggles / FAR proxy |
| **Settings** | Dwell, thresholds, MQTT host, serial port |

---

## Other CLI commands

| Command | Purpose |
|---|---|
| `python -m src.neuroshift serve` | Control App (API + PWA) |
| `python -m src.neuroshift mock` | Headless scripted demo + report/video |
| `python -m src.neuroshift live` | Webcam UI (when camera is available) |
| `python -m src.neuroshift report` | HTML report from logs |
| `python -m src.neuroshift doctor` | Environment check |

---

## Architecture

```text
Phone / Desktop browser (PWA)
        │  REST + WebSocket
        ▼
FastAPI Control App
        │
        ├─ Intention engine (gaze ∧ EMG → Act/Abstain)
        ├─ Mock scene (no camera) / Live camera later
        ├─ Device hub → MQTT → ESP32 relays (hardware ready)
        └─ Session metrics + FAR proxy
```

---

## Hardware later

1. Flash `firmware/esp32_neuroshift/`
2. Enable MQTT in Settings
3. MyoWare → serial (`emg_mode: hardware`)
4. `python -m src.neuroshift live` when webcam is back

---

## Tests

```powershell
python -m unittest discover -s tests -v
```

Research docs remain under `research/` and `docs/`.
