# NeuroShift 2.0 — Problem Definition (Frozen Draft)

**Updated:** July 2026 — gaze-select + EMG-confirm pipeline locked.

## Research question

How can **gaze-based appliance selection**, sparse wearable EMG confirmation, ambient visual affordances, and lightweight user-specific temporal priors be combined into a selective intention policy that correctly actuates—or abstains from actuating—smart-home devices for motor-impaired independent living, reducing false actuations relative to gesture-centric and unimodal baselines?

## Core interaction principle

> **Looking selects. Muscle confirms. Unsure → Abstain.**

Gaze alone must never actuate (avoids Midas-touch false activations).

## Hypothesis

H1: Gaze-selected appliance targeting + EMG volition confirmation reduces false actuation rate versus EMG-only, vision-only, and EMBC-style gesture-rescue fusion in multi-object scenes.

H2: Adding a lightweight personal temporal prior further improves intention disambiguation when gaze is weak or multiple devices are near the gaze direction.

H3: Explicit abstention (reject option) when gaze or EMG is missing/ambiguous improves effective reliability without collapsing usability.

## Scope (Paper-1 / Phase 1–2)

**In scope**
- Sparse EMG (MyoWare-class) as **confirmation**, not gesture vocabulary
- Ambient webcam: object detection + **head/face gaze (P1)** / **eye-gaze (P2)**
- Appliance-level intention + Act/Abstain
- MQTT actuation to ESP32/relays (Indian wired-home demo hub)
- Decision-level logging / explanations (P2)
- Small curated pilot dataset

**Out of scope (for Paper-1)**
- HD-sEMG accuracy races
- Clinical hospital integration
- Wheelchair control
- Full fall detection product
- Voice as primary modality
- Cloud LLM as sole decision maker
- Expensive commercial eye-trackers (optional later)

## Target users

People with reduced fine motor control who retain some voluntary muscle activity and can direct gaze/head toward appliances, but struggle with remotes/switches.

## Threat model for errors

False positive actuation is worse than delayed assistance. Primary metric = **False Actuation Rate (FAR)**.

## Success criteria

1. Statistically lower FAR vs EMG-only, vision/gaze-only, and Chamberland-style baselines.
2. Competitive intention F1 among non-abstained decisions.
3. Ablations show each of: gaze selection, EMG confirmation, prior, abstention contribute.
4. Reproducible dataset protocol published with the paper.
