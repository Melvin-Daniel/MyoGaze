# NeuroShift Official Pipeline — Gaze Select + EMG Confirm

**Status:** Frozen (updated July 2026)  
**Rule:** Looking selects. Muscle confirms. Unsure → Abstain.

---

## One-line design

> Camera detects appliances **and** where the user is looking; EMG confirms whether they actually want to turn that appliance on/off; system **Acts** or **Abstains**.

---

## Real-time pipeline

```text
Webcam frame
   │
   ├─ YOLO11 / YOLOv8 / RT-DETR  →  appliance boxes (lamp, fan, plug)
   ├─ MediaPipe Face Mesh (Phase 1) / Eye-gaze model (Phase 2)
   │         →  gaze / head direction
   └─ Match gaze ray to appliance box  →  SELECTED TARGET
                    │
                    ▼
            Target appliance confirmed?
                    │
         ┌──────────┴──────────┐
         NO                    YES
         ▼                     ▼
      ABSTAIN          MyoWare EMG volition?
                              │
                    ┌─────────┴─────────┐
                    LOW/NO              HIGH
                    ▼                   ▼
                 ABSTAIN            ACT (toggle via MQTT → ESP32 → relay)
```

---

## Two-factor safety rule (critical)

| Signal | Role | Alone enough to actuate? |
|---|---|---|
| Gaze / head direction | **Select** which appliance | **No** |
| EMG effort | **Confirm** real intent | **No** (without a selected target) |
| Gaze + EMG together | Intention complete | **Yes → Act** |
| Either missing / ambiguous | Unsafe | **Abstain** |

This avoids the **Midas touch** problem (devices turning on just because the user looked at them).

---

## Phase split for gaze

| Phase | Gaze method | Why |
|---|---|---|
| **Phase 1 (Sem 7)** | **Head / face orientation** via MediaPipe Face Mesh | Reliable demo; low compute |
| **Phase 2 (Sem 8)** | **Eye-gaze estimation** (iris / L2CS-style model) + dwell time | Higher precision; stronger paper |
| Both phases | **Dwell** ~0.5–1.0 s on target before EMG window counts | Stops accidental glances |

Optional extra (not primary): hand pose if available.

---

## Example scenarios

### Clear Act
1. User looks at lamp for 0.8 s.  
2. Detector: lamp selected.  
3. EMG spike (voluntary effort).  
4. **ACT → lamp ON** via relay hub.

### Abstain (look only)
1. User glances at fan.  
2. Target = fan.  
3. No EMG effort.  
4. **ABSTAIN** (looking ≠ wanting).

### Abstain (EMG without gaze)
1. User tenses muscle while talking / moving.  
2. No stable gaze on a device.  
3. **ABSTAIN**.

### Ambiguous multi-object
1. Lamp and fan both near gaze center / low confidence.  
2. **ABSTAIN** (or Phase 2 clarify).

---

## Novelty update

**Official novelty package:**
1. **Gaze-selected home intention** (not gesture class)
2. **EMG confirmation** (not gesture dictionary)
3. **Act / Abstain** safety policy
4. **FAR** as primary metric

**Delta over Chamberland EMBC 2024:**  
They use vision to validate **prosthesis grips**.  
We use gaze to **select home appliances** and EMG to **confirm actuation**, with abstention for safety.

---

## Algorithms (locked)

| Stage | Phase 1 | Phase 2 |
|---|---|---|
| Objects | YOLO11s / YOLOv8s (or RT-DETR) | Same + optional open-vocab assist |
| Gaze | MediaPipe Face Mesh / head pose | Eye-gaze model + dwell calibration |
| EMG | RMS/MAV threshold or small TCN | Calibrated volition score |
| Policy | Rule: gaze∧EMG → Act else Abstain | Learned fusion + FAR-tuned abstention |
| Prior | Basic time-of-day (optional) | Personal temporal prior |
| IoT | MQTT → ESP32 → relay demo hub | Same + caregiver XAI dashboard |

---

## Viva one-liner

> NeuroShift uses the camera to detect appliances and which one the user is looking at; the EMG sensor then confirms whether they truly want to toggle it. If either signal is unclear, the system abstains to reduce false actuations.
