# MyoGaze

**Look to select. Hold to confirm. Unsure → do nothing.**

MyoGaze (project codename NeuroShift) is an assistive smart-home control stack: laptop webcam gaze selects a nearby appliance, a dwell hold confirms the action, and an ESP32 relay hub toggles devices over USB serial / MQTT. Includes a phone PWA, Android/iOS Capacitor shells, and a one-class lamp detector you can fine-tune from labeled photos.

> Looking selects. Muscle confirms (when hardware is present). Unsure → Abstain.

---

## Control App (recommended)

### 1) Install

```powershell
cd NeuroShift
python -m pip install -r requirements.txt
cd web
npm install
npm run build
cd ..
```

### 2) Run (PC + phone on same Wi‑Fi)

```powershell
python -m src.neuroshift serve --host 0.0.0.0 --port 8000
```

- PC: http://127.0.0.1:8000  
- Phone: http://YOUR_PC_LAN_IP:8000 (Chrome → Add to Home Screen)  
- Label lamp photos: http://127.0.0.1:8000/label  
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

## What it does

| Area | Detail |
|---|---|
| **Gaze** | MediaPipe face landmarks → screen aim + dwell lock |
| **Vision** | Custom YOLOv8 lamp detector (or open-vocab YOLOE) |
| **Actuation** | USB serial to ESP32 hub and/or MQTT to LAN broker |
| **Apps** | Web PWA + Capacitor Android / iOS wrappers |
| **Safety** | Abstain when unsure; cooldown between toggles |

---

## Other CLI commands

| Command | Purpose |
|---|---|
| `python -m src.neuroshift serve` | Control App (API + PWA) |
| `python -m src.neuroshift mock` | Headless scripted demo + report/video |
| `python -m src.neuroshift live` | Webcam UI |
| `python -m src.neuroshift report` | HTML report from logs |
| `python -m src.neuroshift doctor` | Environment check |
| `python scripts/capture_lamp.py` | Capture training frames |
| `python scripts/prepare_lamp_dataset.py` | Split labeled raw → train/val |
| `python scripts/train_lamp.py` | Fine-tune YOLOv8n lamp model |

---

## Architecture

```text
Phone / Desktop browser (PWA)
        │  REST + WebSocket
        ▼
FastAPI Control App
        │
        ├─ Intention engine (gaze ∧ confirm → Act/Abstain)
        ├─ Live webcam + lamp detector
        ├─ Device hub → serial / MQTT → ESP32 relays
        └─ Session metrics + activity log
```

---

## Hardware

1. Flash `firmware/esp32_neuroshift/` (copy `secrets.h.example` → `secrets.h`)
2. Plug hub USB (default COM4 on Windows)
3. Optional: MQTT broker on the same LAN (`config/mosquitto.conf`)
4. Optional: MyoWare EMG serial (`emg_mode: hardware`)

---

## Tests

```powershell
python -m pytest tests -q
```

Research docs remain under `research/` and `docs/`.
