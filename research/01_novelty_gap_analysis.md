# NeuroShift 2.0 — Novelty & Research Gap Analysis

**Status:** Phase 0 (frozen draft for Paper-1 scoping)  
**Date:** 2026-07-24  
**Rule:** A feature enters Paper-1 only if it closes a gap below. Product backlog ≠ research claim.

---

## 1. What is already saturated (do NOT claim as novelty)

| Claim | Why it is weak | Representative prior art |
|---|---|---|
| EMG gesture recognition with deep learning | Extremely crowded; accuracy races on Ninapro/CapgMyo | Hundreds of CNN/LSTM/Transformer/Mamba papers |
| EMG + vision improves gesture accuracy | Explicitly done | Chamberland EMBC 2024; ROBIO TFVF 2024; M2VIP 2024 |
| Multimodal fusion for grasp intent (prosthesis) | Strong SOTA already | Frontiers 2024 Bayesian EMG+vision+gaze (~95%) |
| VLM guides EMG decoding | Recent, strong | VLM-EMG IEEE 2025 |
| Smart-home intent via LLM/ontology (no EMG) | Growing fast | CIDER 2025; VCU-LLM 2025 |
| SHAP/attention XAI on EMG channels | Done for feature/sensor selection | TMRB 2024; EMGCipher EMBC 2024; TCE 2023 GNN-XAI |
| EMG smart-home button mapping | HCI / living-lab exploratory | Sagacity/HASE 2025; Manitoba subtle-EMG smart home |

**Verdict:** “We fuse EMG + YOLO + Transformer and get higher accuracy” will be rejected as incremental.

---

## 2. Open gaps with real novelty potential

Ranked by **publishability × feasibility with MyoWare + webcam + ESP32**.

### Gap A — ★★★★★ PRIMARY (Paper-1 core)

**Appliance-level intention under visual ambiguity, with selective abstention**

**Problem.** Prosthesis papers predict *grasp type*. Smart-home LLM agents predict *text/voice intent*. Almost nobody predicts:

> Which *device action* should fire now, given sparse EMG volition + multi-object scene, with the option to **abstain** instead of falsely actuating.

**Why open.**
- Chamberland et al. use vision to *validate/rescue gestures*, not to rank home actions.
- Grasp-intent fusion assumes a single target object during reach.
- Wake-gesture literature (JNE 2025) fights false activations via an EMG toggle, not via scene affordances.
- Selective prediction / reject-option ML is mature in theory, underused in EMG–home control.

**NeuroShift claim.**
**Gaze selects the appliance; EMG confirms intent**; calibrated **Act / Abstain** minimizes **false actuation rate** in multi-object rooms (avoids Midas-touch from gaze alone).

**Gap closed:** safety-critical home control under open-set ADL interference + visual ambiguity.

---

### Gap B — ★★★★☆ STRONG SECONDARY

**Sparse-channel EMG as volitional confirmation, not gesture vocabulary**

**Problem.** Motor-impaired users may not produce crisp gesture classes. Most systems still require “gesture 1 = light, gesture 2 = fan.”

**Why open.**
- Subtle-EMG smart-home HCI exists, but remains gesture→command.
- HD-sEMG Transformers/Mamba optimize classification under dense arrays—wrong hardware regime for MyoWare.
- Assistive living needs *binary/graded effort + context*, not 8-class gesture dictionaries.

**NeuroShift claim.**
Treat sparse EMG as **P(volition)** / effort confirmation; let **gaze + object detection** select the appliance; EMG confirms or rejects.

**Gap closed:** realistic wearable constraint + reduced motor burden for impaired users.

---

### Gap C — ★★★★☆ STRONG SECONDARY

**Personal temporal prior for the same scene → different intention**

**Problem.** Same visual scene (desk lamp + fan + bottle) maps to different intended actions by time-of-day and user routine. Pure perception systems ignore this; pure CASAS HAR ignores EMG volition.

**Why open.**
- Ambient HAR (CASAS-style) models routines without EMG confirmation.
- EMG systems rarely condition on long-horizon personal priors.
- LLM home agents personalize language, not physiology-grounded actuation risk.

**NeuroShift claim.**
Lightweight **user-specific prior** (time, recent actions, preferred devices) that reweights intention candidates *before* actuation.

**Gap closed:** disambiguation when vision+EMG alone are underdetermined.

**Keep modest:** Bayesian / count-based / small sequence model—not “lifelong RL” cosplay in Paper-1.

---

### Gap D — ★★★☆☆ EVALUATION / TRUST AXIS

**Decision-level explainability for caregivers (not channel SHAP)**

**Problem.** Existing EMG XAI explains *which electrode/feature* mattered. Caregivers need: *why did the light turn on?*

**Why open.**
- SHAP/attention papers stop at representation attribution.
- Smart-home LLM agents can verbalize plans but lack EMG grounding.
- No standard metric for explanation usefulness in EMG–IoT actuation.

**NeuroShift claim.**
Structured explanation: `{candidate actions, winning action, modality contributions, abstention reason, objects involved}`.

**Gap closed:** auditable assistive actuation.

**Important:** XAI is a **contribution axis**, not the sole novelty.

---

### Gap E — ★★★☆☆ DATASET / BENCHMARK (high value for MS + IEEE)

**No public benchmark for EMG + ambient scene → home-device intention**

Existing datasets:

| Dataset | What it has | Missing for NeuroShift |
|---|---|---|
| Ninapro / CapgMyo / MYO | EMG gestures | No home devices / ambient scene intention |
| Chamberland-style prosthesis setups | EMG + objects for grasp | Grasp labels, not appliance actions |
| PULSE / egocentric EMG+RGB | ADL / grasp / motor primitives | Not appliance actuation labels |
| MOVMUS-UJI | EMG + hand kinematics ADL | Ergonomics, not IoT control |
| EPFL-Smart-Kitchen | Vision/IMU/gaze kitchen | No EMG |
| CASAS / MHAD | Home activity / physio | No EMG→device intention |
| CIDER/VCU-LLM setups | Language home intent | No EMG |

**NeuroShift claim.**
Release **NeuroShift-ADL**: synchronized sparse EMG + ambient RGB + pose/objects + **target device action** + ambiguity tags + abstention labels.

**Gap closed:** enables reproducible research beyond proprietary lab demos.

---

## 3. Gaps that look attractive but are weak / crowded

| Tempting idea | Verdict | Reason |
|---|---|---|
| New EMG Transformer/Mamba backbone | Reject as Paper-1 headline | Wrong sensor regime; crowded |
| Beat SOTA on Ninapro | Reject | Orthogonal to assistive-home thesis |
| VLM end-to-end home agent | Risky as sole novelty | CIDER/VCU-LLM/ACKnowledge already there |
| Fall detection + medicine + wheelchair | Product only | Not one coherent IEEE contribution |
| Graph Neural Network “because modern” | Only if topology is justified | Need electrode/object graph rationale |

---

## 4. Recommended Paper-1 title options

1. **NeuroShift: Affordance-Conditioned Multimodal Intention Inference with Selective Actuation for Assistive Smart Homes**
2. **From Gestures to Home Intentions: Sparse EMG and Scene Affordance Fusion with Calibrated Abstention**
3. **Reducing False Smart-Home Actuations via EMG-Confirmed Visual Affordance Reasoning**

Prefer (1) or (3) for clarity of contribution.

---

## 5. Contribution freeze (Paper-1)

**Include**
1. Affordance-conditioned home-action intention (Gap A)
2. Sparse-EMG volitional confirmation (Gap B)
3. Lightweight personal temporal prior (Gap C)
4. Decision-level explanations + false-actuation metrics (Gap D)
5. Dataset protocol / NeuroShift-ADL (Gap E) — even if small pilot N

**Exclude from research claims**
- Gesture dictionary mapping as the scientific contribution
- HD-EMG model races
- Full caregiver product suite
- Hospital / wheelchair / voice-first as core novelty

---

## 6. Minimum viable experimental story (IEEE-ready)

**Task.** Multi-object desk/room scenes; candidate devices {light, fan, plug, alert}; labels = intended device action OR abstain.

**Baselines (mandatory)**
1. EMG-only classifier → device
2. Vision-only (object+pose) → device
3. EMBC-style late gate (vision validates EMG gesture)
4. Always-act fusion (no abstention)
5. Optional: LLM/ontology agent without EMG

**Primary metrics**
- Intention macro-F1
- **False Actuation Rate (FAR)** — most important for assistive safety
- Abstention precision/recall
- Time-to-decision
- Explanation completeness score (structured checklist)

**Ablations**
- − prior, − abstention, − EMG, − vision, − object affordances

---

## 7. Novelty scorecard (honest)

| Contribution | Novelty | Feasibility | IEEE fit | Keep? |
|---|---|---|---|---|
| Affordance + abstention home intention | High | High | High | YES — core |
| Sparse EMG as confirmation | High | High | High | YES |
| Personal temporal prior | Medium-High | High | Medium-High | YES (modest) |
| Decision-level XAI | Medium | High | Medium | YES (axis) |
| New public dataset | High | Medium | High | YES |
| EMG Transformer SOTA | Low | Medium | Low | NO |
| Full product dashboard | Low (research) | High | Low | MVP only |

---

## 8. One-sentence research identity

> NeuroShift is not a better gesture recognizer; it is a **gaze-select + EMG-confirm intention policy** that decides *which* smart-home appliance to control and *whether* to act—or abstain—under ambiguous domestic scenes.

## 9. Official interaction principle (locked July 2026)

> **Looking selects. Muscle confirms. Unsure → Abstain.**

See `research/07_gaze_emg_pipeline.md` for the full real-time pipeline.
