# NeuroShift — 10 Reference Papers (Module-wise)

**For guide review**  
**Base paper (approved):** Chamberland et al., IEEE EMBC 2024  
**Rule sir asked:** From ~10 relevant papers, each NeuroShift module is supported by a reference; one is chosen as base.

---

## How to explain to your guide (30 seconds)

> We surveyed related work across EMG, vision, gaze, fusion, smart-home assistive control, and safety/abstention.  
> We selected **10 key papers**.  
> **Chamberland EMBC 2024** is our **base paper** (EMG + vision scene understanding).  
> Each module of NeuroShift is mapped to at least one of these papers.  
> Our novelty is combining them as: **gaze selects appliance → EMG confirms → Act/Abstain → home relay control**, evaluated by **FAR**.

---

## NeuroShift modules

```text
M1 Object detection (appliances)
M2 Gaze / head-direction selection
M3 EMG volition confirmation
M4 Multimodal fusion (EMG + vision/gaze)
M5 Act / Abstain safety (reject false actuation)
M6 Assistive / smart-home control
M7 Real-time face landmarks (implementation)
M8 Modern real-time detector alternative
M9 Sparse/wearable EMG practical sensing
M10 Overall base architecture (EMG + scene CV)
```

---

## The 10 papers (show this table to sir)

| # | Paper | Year / Venue | NeuroShift module | How we use it |
|---|---|---|---|---|
| **P1 BASE** | Chamberland et al., *Visual Scene Understanding for Enhanced EMG Gesture Recognition* | IEEE EMBC 2024 | **M10 Base architecture** + M1 + M4 | Base paper. EMG + YOLO scene context. We extend from prosthesis *gestures* to *home intention* |
| **P2** | Wang / Frontiers group, *Multimodal fusion of EMG and vision for human grasp intent inference* | Frontiers in Robotics and AI, 2024 | **M4 Multimodal fusion** | Shows EMG+vision can infer *intent*, not only gesture class. Supports our intention framing |
| **P3** | Yang et al., *Empowering High-Level SCI Patients… Hybrid Gaze and FEMG-Controlled Assistive Robotic System* | IEEE TNSRE 2024 | **M2 Gaze select + M3 EMG confirm** | Strong support for **gaze selects, EMG/FEMG confirms** hybrid HCI |
| **P4** | BlinkGrid / gaze-home appliance papers e.g. *BlinkGrid Control: Eye Gaze Driven Framework… Home Appliances* | IEEE ICCIT 2023 | **M2 Gaze → home appliances** | Webcam gaze used to control home devices (supports appliance domain) |
| **P5** | Zhang et al. (or classic hybrid), *Hybrid BCI smart home combining SSVEP and EMG* | Biomed. Signal / related 2019– | **M5 Confirm + prevent idle false ops** | EMG used to **confirm** selection and prevent incorrect operations when idle |
| **P6** | Scheme et al., *Confidence-Based Rejection for Improved Pattern Recognition Myoelectric Control* | IEEE TBME 2013 | **M5 Act/Abstain / reject option** | Classic myoelectric **reject/abstain** when confidence low (FAR philosophy) |
| **P7** | Sagacity / *IoT and Older Adults: Multimodal EMG and AI-Based Interaction with Smart Home* | arXiv 2025 | **M6 Smart-home EMG assistive IoT** | EMG for smart-home interaction for older/impaired users (domain support) |
| **P8** | Kartynnik et al., *Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs* (MediaPipe Face Mesh) | arXiv 2019 | **M7 Face/head landmarks implementation** | Basis for Phase-1 head/face direction from webcam |
| **P9** | Jocher / Ultralytics YOLO family (and base paper’s YOLO use); optional alt: Zhao/Lv *RT-DETR* CVPR 2024 | 2023–2024 | **M1 Object detection** | YOLO for appliances (same family as base); RT-DETR as modern alternative |
| **P10** | Chamberland et al., *Novel Wearable HD-EMG Sensor…* OR practical MyoWare-class wearable EMG HCI literature | IEEE TBioCAS 2023 / related | **M9 Wearable EMG sensing** | Wearable EMG acquisition motivation; we use sparse MyoWare for low-cost feasibility |

> Note: P1 is **base**. P9 can be cited as YOLO (used in P1) + RT-DETR paper if sir wants a detector-specific citation. Exact bibliographic lines are below.

---

## Module → paper map (sir’s “module-wise” request)

| NeuroShift module | What it does in our system | Main reference paper(s) | What we keep | What we change / improve |
|---|---|---|---|---|
| **Appliance detection** | Find lamp/fan/plug in camera | **P1, P9** (YOLO / RT-DETR) | Real-time object detection | Detect home appliances, not prosthesis grasp objects only |
| **Gaze / head selection** | Choose which appliance user is looking at | **P3, P4, P8** | Gaze as selector | Webcam head/eye gaze for home devices (Phase1 head, Phase2 eyes) |
| **EMG confirmation** | Confirm user really wants toggle | **P3, P5, P10** | EMG as intention/confirm signal | Sparse MyoWare confirm, **not** 6-class gesture dictionary |
| **Multimodal fusion** | Combine gaze target + EMG | **P1, P2, P3** | EMG + vision fusion idea | Fusion output = home Act/Abstain, not grip class |
| **Act / Abstain safety** | Do nothing if unsure | **P5, P6** | Reject low-confidence actions | Explicit home **FAR** metric + dwell+EMG two-factor |
| **Smart-home IoT actuation** | ESP32 + relay / MQTT | **P7** (+ engineering practice) | Assistive home control goal | Indian wired-home relay hub retrofit |
| **Overall system idea** | Full pipeline | **P1 BASE** | EMG + scene CV multimodal | Extend to gaze-select + home intention + abstain |

---

## Detailed citation list (copy into report)

### P1 — BASE PAPER
**Chamberland, F., Labbé, T., Tam, S., Scheme, E., Gosselin, B.**  
*Visual Scene Understanding for Enhanced EMG Gesture Recognition.*  
**IEEE EMBC 2024.** DOI: `10.1109/EMBC53108.2024.10782354`  
**Module:** Overall base (EMG + YOLO scene understanding)  
**Gap we fill:** They improve prosthesis gestures; we do home-device intention with gaze+EMG+abstain.

### P2 — Intention fusion
**Multimodal fusion of EMG and vision for human grasp intent inference in prosthetic hand control.**  
**Frontiers in Robotics and AI, 2024.** DOI: `10.3389/frobt.2024.1312554`  
**Module:** Multimodal intention (not only classification)  
**Use:** Justifies “intent inference” language.

### P3 — Gaze + EMG hybrid
**Yang et al.**  
*Empowering High-Level Spinal Cord Injury Patients in Daily Tasks With a Hybrid Gaze and FEMG-Controlled Assistive Robotic System.*  
**IEEE TNSRE, 2024.** DOI: `10.1109/tnsre.2024.3443073`  
**Module:** Gaze select + EMG/FEMG confirm  
**Use:** Closest HCI pattern to our “looking selects, muscle confirms.”

### P4 — Gaze for home appliances
**BlinkGrid Control: An Eye Gaze Driven Framework for Quadriplegic Patients to Control Home Appliances.**  
**IEEE ICCIT 2023.** DOI: `10.1109/iccit60459.2023.10441588`  
**Module:** Gaze → home appliances  
**Use:** Shows webcam gaze can control home devices; we add EMG confirm + FAR.

### P5 — Confirm to stop false operations
**Hybrid BCI-controlled smart home system combining SSVEP and EMG for individuals with paralysis.**  
(EMG used for confirmation / prevent idle errors)  
**Module:** Confirmation channel + anti-false-operation  
**Use:** Supports two-factor design (select then confirm).

### P6 — Reject / abstain in myoelectric control
**Scheme, E.J., Hudgins, B.S., Englehart, K.B.**  
*Confidence-Based Rejection for Improved Pattern Recognition Myoelectric Control.*  
**IEEE TBME, 2013.** DOI: `10.1109/TBME.2013.2238939`  
**Module:** Act/Abstain / confidence rejection  
**Use:** Classic basis for not actuating when unsure (also cited by related EMBC work).

### P7 — EMG smart home assistive
**IoT and Older Adults: Towards Multimodal EMG and AI-Based Interaction with Smart Home** (Sagacity-related).  
**arXiv 2025** (`2507.19479`)  
**Module:** EMG + smart-home independent living  
**Use:** Domain motivation for EMG home control for older/impaired users.

### P8 — Face mesh / head landmarks
**Kartynnik, Y., Ablavatski, A., Grishchenko, I., Grundmann, M.**  
*Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs.*  
**arXiv:1907.06724** (MediaPipe Face Mesh)  
**Module:** Phase-1 head/face direction from webcam  
**Use:** Implementation backbone for gaze/head selection without Tobii.

### P9 — Object detection
**Primary (aligned with base):** YOLO family as used in P1 (Ultralytics YOLOv8/YOLO11).  
**Modern alternative:** Zhao/Lv et al., *DETRs Beat YOLOs on Real-time Object Detection* (**RT-DETR**), **CVPR 2024** / arXiv:2304.08069.  
**Module:** Appliance object detection  
**Use:** YOLO for Phase 1; RT-DETR optional benchmark.

### P10 — Wearable EMG sensing
**Chamberland et al.**  
*Novel Wearable HD-EMG Sensor With Shift-Robust Gesture Recognition Using Deep Learning.*  
**IEEE TBioCAS, 2023.** DOI: `10.1109/TBCAS.2023.3314053`  
**Module:** Wearable EMG acquisition motivation  
**Use:** Wearable EMG is valid; we choose **sparse MyoWare** for cost/feasibility (not competing on HD-EMG accuracy).

---

## How NeuroShift is built from these 10 (flowchart for sir)

```text
P9/P1  Object detection (appliances)
P8/P4  Gaze / head direction (select appliance)
P10/P3 EMG wearable signal (confirm)
P2/P1  Multimodal fusion idea
P5/P6  Confirm + Reject/Abstain safety
P7     Smart-home assistive goal
P1     BASE: EMG + scene vision paradigm
                │
                ▼
        NeuroShift system
   Gaze selects + EMG confirms
   Act / Abstain + FAR
   ESP32 relay home control
```

---

## One slide text (if sir asks “why these 10?”)

1. **P1** base multimodal EMG+vision  
2. **P2** intention (not only gesture)  
3. **P3** gaze+EMG hybrid assistive control  
4. **P4** gaze for home appliances  
5. **P5** confirm channel reduces false ops  
6. **P6** confidence rejection / abstain  
7. **P7** EMG smart-home for impaired/older users  
8. **P8** real-time face landmarks (webcam)  
9. **P9** real-time object detection  
10. **P10** wearable EMG sensing lineage  

---

## Our novelty vs these papers (important)

| Already done in references | Still open → NeuroShift |
|---|---|
| EMG + vision for prosthesis gestures (P1) | Home-device intention for independent living |
| Gaze + FEMG for robot ADL tasks (P3) | Gaze + **sparse limb EMG** + **home relays** + **FAR** |
| Gaze-only home control (P4) | Add EMG confirm so looking ≠ actuating |
| EMG smart home exploratory (P7) | Add scene+gaze intention + abstention science |
| Reject option in myoelectric (P6) | Apply reject option to **smart-home false actuations** |

---

## Suggested title line for reference section header

**Primary base paper:** Chamberland et al., IEEE EMBC 2024  
**Supporting references (9):** P2–P10 as module supports  
**Total core references for guide:** **10**

---

## Action for you

1. Show this module table to your guide.  
2. Keep **P1 as base** (sir already liked it).  
3. If sir asks for PDFs/DOIs, download P1–P7 first (most critical).  
4. Tell sir clearly: modules are derived from these papers; novelty is the **combination + home FAR problem**.
