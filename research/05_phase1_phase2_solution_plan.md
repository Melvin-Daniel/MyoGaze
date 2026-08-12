# NeuroShift — Phase 1 & Phase 2 Complete Plan

**For guide + external viva**  
**Base paper:** Chamberland et al., IEEE EMBC 2024  
**Rule:** Phase 1 = working demo + data. Phase 2 = research depth + paper.

---

## 1. What is our solution? (one page)

### Problem
People with stroke / partial paralysis / limited hand function struggle to use switches and remotes. Wrong smart-home actuations are dangerous.

### Solution name
**NeuroShift — Gaze-Selected, EMG-Confirmed Home Intention with Selective Actuation**

### How it works (simple) — LOCKED PIPELINE

```
1. Camera detects appliances (lamp, fan, plug) with YOLO/RT-DETR
2. Camera detects where user is LOOKING (head/face Phase 1; eye-gaze Phase 2)
3. Gaze selects the target appliance (with ~0.5–1s dwell)
4. MyoWare EMG confirms: does the user actually want to toggle it?
5. Intention policy:
      ACT on selected device   OR   ABSTAIN
6. ESP32 + MQTT + relay hub turns the device on/off
7. Dashboard logs why (gaze target, EMG score, decision)
```

**Principle:** Looking selects. Muscle confirms. Unsure → Abstain.  
Gaze alone must never actuate (prevents Midas-touch false activations).

### Difference from base paper
| Base paper | NeuroShift |
|---|---|
| Fixes wrong **gestures** for prosthesis | Decides which **home device** to control |
| Vision filters allowed grips | **Gaze selects** appliance; vision detects devices |
| Hand tracking near objects | **Head/eye gaze** as primary selector |
| HD-EMG (64 channels) | Sparse MyoWare (confirm only) |
| Always mainly about classification | Can **ABSTAIN** for safety |

---

## 2. Phase split (Sem 7 vs Sem 8)

| | **Phase 1 — Sem 7 (NOW)** | **Phase 2 — Sem 8 (NEXT)** |
|---|---|---|
| Goal | Working prototype + pilot data | Research contribution + IEEE paper |
| Status of idea | Prove pipeline works | Prove novelty with evaluation |
| Fusion | Rule-based / simple scorer | Learned fusion + calibrated abstention |
| Context | Device state + basic time | Personal habit prior |
| XAI | Decision log only | Caregiver explanations + dashboard |
| Demo | Live hardware demo | Live demo + graphs + paper draft |
| Deliverable | Prototype + report + dataset start | Full evaluation + paper + MVP polish |

---

## 3. Phase 1 (Sem 7) — Exact plan

### 3.1 What we will BUILD

| # | Module | What it does |
|---|---|---|
| 1 | **EMG acquisition** | MyoWare → ESP32/ADC → Python stream |
| 2 | **Volition encoder** | Convert EMG into P(user is trying to act) — **confirm only** |
| 3 | **Object detection** | Webcam → YOLO11/YOLOv8/RT-DETR → appliances |
| 4 | **Gaze selection** | MediaPipe Face Mesh / head pose → which appliance is looked at |
| 5 | **Dwell + match** | Gaze must stay on device ~0.5–1s; map to appliance box |
| 6 | **Intention policy** | Rule: gaze∧EMG → Act else Abstain |
| 7 | **IoT actuation** | MQTT → ESP32 → relay demo hub |
| 8 | **Logger + dashboard** | Show gaze target, EMG, decision |

### 3.2 Phase 1 algorithms (keep simple, defensible)

| Stage | Algorithm / model | Why this one |
|---|---|---|
| EMG preprocess | Bandpass / rectify / moving RMS or MAV | Standard, reliable for sparse EMG |
| Volition score | Threshold on RMS **or** small **1D-CNN / TCN** | Confirm intent — not gesture classes |
| Object detection | **YOLO11 / YOLOv8 / RT-DETR** | Real-time appliances; base-paper lineage |
| Gaze (Phase 1) | **MediaPipe Face Mesh / head pose** | Reliable demo; selects looked-at device |
| Gaze (Phase 2) | Eye-gaze model (iris / L2CS-style) | Higher precision for paper |
| Dwell filter | 0.5–1.0 s on target | Blocks accidental glances |
| Fusion (Phase 1) | **gaze selected ∧ EMG high → Act else Abstain** | Two-factor safety |
| Actuation | MQTT → ESP32 relay hub | Indian wired-home demo |
| Logging | SQLite/CSV + dashboard | Phase 2 evaluation |

**Phase 1 fusion logic (demo-friendly):**

```
IF no stable gaze on an appliance (dwell fail):
    → ABSTAIN
ELSE IF EMG_volition < T_low:
    → ABSTAIN   # looking ≠ wanting
ELSE IF gaze target confidence high AND EMG high:
    → ACT on gazed appliance
ELSE:
    → ABSTAIN
```

### 3.3 Phase 1 hardware requirements

| Item | Purpose | Required? |
|---|---|---|
| MyoWare EMG sensor + electrodes | Muscle volition | Yes |
| ESP32 (×1 or ×2) | EMG ADC/stream + relay control | Yes |
| Relay module / smart plug | Turn lamp/fan on-off | Yes |
| Webcam (USB) | Scene + pose | Yes |
| Laptop with GPU (or decent CPU) | Run vision + fusion | Yes |
| Lamp + fan (or bulbs + small appliances) | Demo targets | Yes |
| MQTT broker (Mosquitto local) | Message bus | Yes |
| Optional: breadboard, power supply, jumper wires | Wiring | Yes |

**Not required in Phase 1:** Raspberry Pi, HD-EMG armband, cloud LLM, hospital sensors.

### 3.4 Phase 1 software requirements

| Layer | Stack |
|---|---|
| AI / sensing | Python, PyTorch, OpenCV, Ultralytics YOLO or RT-DETR, MediaPipe |
| Backend | FastAPI |
| Frontend | React (simple live view + logs) |
| DB | SQLite (Phase 1) → PostgreSQL (Phase 2) |
| IoT | MQTT (paho-mqtt), ESP32 Arduino/ESP-IDF firmware |
| Tools | Git, VS Code/Cursor, Postman optional |

### 3.5 Phase 1 dataset (start collecting)

Collect **NeuroShift-ADL pilot**:
- Users: preferably **5+** (friends/lab mates OK for pilot)
- Trials per user: **~30–50**
- Conditions:
  - single device visible
  - multi-device ambiguous scene
  - ADL interference (hand moving without intent)
- Labels: `lamp_on / fan_on / plug_on / abstain`
- Save: EMG window, frame timestamp, detections, decision, ground truth

### 3.6 Phase 1 baselines (must run)

1. EMG-only → device  
2. Vision-only → device  
3. Chamberland-style late gate (vision validates EMG)  
4. Our Phase-1 Act/Abstain policy  

**Metric to show:** False Actuation Rate + intention accuracy

### 3.7 Phase 1 deliverables for college

- [ ] Working live demo (EMG + camera → device)
- [ ] Architecture diagram
- [ ] Base paper comparison slide
- [ ] Need analysis with population data
- [ ] Pilot dataset started
- [ ] Phase 1 report / PPT
- [ ] GitHub repo with code + README

---

## 4. Phase 2 (Sem 8) — Exact plan

### 4.1 What we will ADD

| # | Module | What it adds |
|---|---|---|
| 1 | **Learned multimodal fusion** | Train scorer/network over EMG + vision + context features |
| 2 | **Calibrated abstention** | Tune threshold to minimize FAR without killing usability |
| 3 | **Personal temporal prior** | Time-of-day / recent device use reweights candidates |
| 4 | **Decision-level XAI** | Show why system chose Act/Abstain |
| 5 | **Caregiver dashboard** | History, alerts, explanations |
| 6 | **Full evaluation** | All baselines + ablations + stats |
| 7 | **IEEE paper draft** | EMBC-style paper |

### 4.2 Phase 2 algorithms

| Stage | Algorithm | Why |
|---|---|---|
| EMG encoder | **TCN** or lightweight **Transformer/SSM** (small) | Temporal modeling; novelty is NOT the backbone |
| Vision features | Detector + pose embeddings / object one-hots | Affordance candidates |
| Fusion | Late fusion MLP / small cross-attention / calibrated score fusion | Intention ranking |
| Abstention | Confidence threshold / reject option / selective prediction | Safety novelty |
| Prior | Bayesian counts or small sequence model over user history | Disambiguation |
| XAI | Feature attribution + structured reason template | Caregiver trust |
| Optional assist | Tiny VLM caption only as helper (not core decision) | Avoid LLM-only novelty trap |

### 4.3 Phase 2 evaluation (paper-ready)

**Scenes:** desk/room with lamp, fan, plug, optional alert button  
**Users:** expand pilot (ideally 8–15 if possible)  
**Primary metrics:**
1. **False Actuation Rate (FAR)** ← main claim  
2. Intention macro-F1 (when system acts)  
3. Abstention precision/recall  
4. Latency (ms)  
5. Explanation completeness checklist  

**Ablations:**
- no EMG  
- no vision  
- no abstention  
- no prior  
- no affordance mapping  

### 4.4 Phase 2 deliverables

- [ ] Improved live demo (Act/Abstain visible)
- [ ] Caregiver dashboard
- [ ] Evaluation tables + graphs
- [ ] NeuroShift-ADL dataset protocol
- [ ] IEEE paper draft
- [ ] Final project report + viva PPT
- [ ] Startup/MVP narrative (optional)

---

## 5. System architecture (both phases)

```
┌──────────────┐     ┌───────────────────┐
│ MyoWare EMG  │────▶│ Volition Encoder  │──┐
└──────────────┘     └───────────────────┘  │
                                            ▼
┌──────────────┐     ┌───────────────────┐  ┌────────────────────┐
│ Webcam       │────▶│ YOLO/RT-DETR +    │─▶│ Intention Policy   │
└──────────────┘     │ Pose + Affordance │  │ Act / Abstain      │
                     └───────────────────┘  └─────────┬──────────┘
┌──────────────┐     ┌───────────────────┐            │
│ Context      │────▶│ Time / habit prior│────────────┘
│ (Phase 2)    │     └───────────────────┘            │
└──────────────┘                                      ▼
                                            ┌────────────────────┐
                                            │ MQTT → ESP32 Relay │
                                            │ Lamp / Fan / Plug  │
                                            └─────────┬──────────┘
                                                      ▼
                                            ┌────────────────────┐
                                            │ Dashboard + Logs   │
                                            └────────────────────┘
```

---

## 6. Requirements checklist (buy / arrange)

### Must have (Phase 1)
- [ ] MyoWare muscle sensor kit + electrode pads
- [ ] ESP32 DevKit
- [ ] 5V/optocoupler relay module (2–3 channels)
- [ ] USB webcam
- [ ] Laptop
- [ ] Table lamp + desk fan (or bulbs)
- [ ] Wires, power supply, enclosure box
- [ ] Mosquitto MQTT broker

### Nice to have
- [ ] Second ESP32 (separate sensing vs actuation)
- [ ] Smart plug (Tasmota/Sonoff MQTT)
- [ ] GPU laptop for faster YOLO
- [ ] Webcam stand / clamp
- [ ] Caregiver tablet for dashboard demo

### Software accounts / installs
- [ ] Python 3.10+
- [ ] PyTorch + CUDA if GPU available
- [ ] Node.js for React dashboard
- [ ] GitHub repository

---

## 7. How to show DEMO to EXTERNAL (critical)

### 7.1 Demo storyboard (8–10 minutes)

| Time | What you show | What you say |
|---|---|---|
| 0:00–1:00 | Title + need slide with population numbers | “~100M stroke survivors globally; India ~9.4M prevalence…” |
| 1:00–2:00 | Base paper vs NeuroShift comparison | “Base paper rescues gestures; we infer home intention with abstain” |
| 2:00–3:00 | Architecture diagram | Walk sensors → fusion → MQTT → devices |
| 3:00–6:30 | **LIVE DEMO** (3 scenes) | See below |
| 6:30–8:00 | Results / FAR vs baselines | Show table even if pilot numbers |
| 8:00–9:00 | Sem 7 done / Sem 8 next | Clear roadmap |
| 9:00–10:00 | Q&A | Novelty, ethics, limitations |

### 7.2 Live demo scenes (memorize these)

**Scene A — Clear intention (success)**  
- Only lamp in focus / hand oriented to lamp  
- User produces EMG effort  
- System ACTS → lamp turns ON  
- Dashboard shows: objects=[lamp], EMG=high, decision=ACT lamp

**Scene B — Ambiguity (safety)**  
- Lamp + fan both visible  
- Weak/ambiguous signal  
- System ABSTAINS → nothing turns on  
- Say: “Better to do nothing than wrong actuation”

**Scene C — Baseline contrast (optional but impressive)**  
- Run EMG-only or always-act mode on same ambiguous scene  
- Show false actuation  
- Switch to NeuroShift mode → abstain  
- This proves novelty visually

**Scene D — ADL interference (Phase 2 / if ready in Phase 1)**  
- User moves hand normally (not intending control)  
- System abstains

### 7.3 External examiner checklist (what they look for)

| They ask | Your answer |
|---|---|
| What is novelty? | Home intention + Act/Abstain, not gesture accuracy |
| Base paper? | Chamberland EMBC 2024; we extend gesture rescue → home intention |
| Why useful? | Stroke/paralysis population data + independent living |
| Algorithms? | YOLO/MediaPipe + EMG volition + fusion policy + MQTT |
| How evaluated? | FAR, intention F1, vs EMG-only / vision-only / Chamberland-gate |
| Failures? | Occlusion, unknown objects, noisy EMG → abstain by design |
| Ethics? | Consent for data collection; no critical medical device claim in Phase 1 |

### 7.4 Demo setup tips (avoid failure on stage)

1. **Pre-wire and tape** all relays the night before  
2. Keep a **backup video** of a successful run (if live fails)  
3. Use **high-contrast objects** (bright lamp, visible fan)  
4. Fix camera position; don’t move it during demo  
5. Show **dashboard decision panel** on projector  
6. Have a second person trigger MQTT manually only as emergency fallback (don’t admit unless asked)  
7. Rehearse the 3 scenes until they are boringly reliable  

### 7.5 What slides to carry

1. Title + team  
2. Need (population data)  
3. Base paper vs ours  
4. Problem statement + RQ  
5. Architecture  
6. Algorithms (Phase 1 / Phase 2)  
7. Hardware photo  
8. Live demo  
9. Results table  
10. Conclusion + future work  

---

## 8. Week-by-week skeleton (Phase 1)

| Weeks | Focus |
|---|---|
| 1–2 | Hardware bring-up: MyoWare + ESP32 stream + relay blink |
| 3–4 | YOLO + MediaPipe on desk scene; affordance map |
| 5–6 | Fusion rules + MQTT end-to-end lamp/fan control |
| 7–8 | Dashboard + logger; collect pilot trials |
| 9–10 | Baselines + FAR/accuracy table; polish demo |
| 11–12 | Report, PPT, rehearsal for external |

---

## 9. What NOT to do

- Don’t chase Ninapro SOTA accuracy  
- Don’t make Transformer the “novelty”  
- Don’t add fall detection / medicine / wheelchair into Phase 1 claims  
- Don’t depend on cloud LLM for core decision  
- Don’t demo without an abstain scene (that is your safety story)

---

## 10. One-line summary for external

> NeuroShift is a multimodal assistive system that uses camera context and sparse EMG to decide which home device a motor-impaired user intends to control—and abstains when unsure—to reduce false actuations.

---

## Phase ownership

| Phase | Own this sentence |
|---|---|
| **Phase 1** | “We built a working EMG + vision + IoT intention prototype with Act/Abstain and pilot data.” |
| **Phase 2** | “We proved with evaluation that affordance-conditioned fusion + abstention + personal prior reduces false actuations vs baselines, and wrote the IEEE paper.” |
