# MioGaze vs Base Paper — Lin et al. IEEE TNSRE 2024

**Status:** Guide-selected base paper (locked July 2026)  
**Project:** MioGaze: Gaze-Selected and EMG-Confirmed Smart-Home Intention Inference with Selective Actuation for Assistive Living

---

## 1. One-line summary for sir

| | Base paper (Lin TNSRE 2024) | MioGaze (ours) |
|---|---|---|
| **Idea** | Gaze selects target; facial EMG confirms; robot helps SCI ADLs | Gaze selects **home appliance**; wearable EMG confirms; Act/Abstain for safe home control |

> **Base:** Looking selects + muscle confirms for assistive **robot**.  
> **Ours:** Looking selects + muscle confirms for assistive **smart home**, with Abstain + FAR.

---

## 2. Base paper

**Title:** Empowering High-Level Spinal Cord Injury Patients in Daily Tasks With a Hybrid Gaze and FEMG-Controlled Assistive Robotic System  
**Authors:** Chengyu Lin, Xiaoyu Yan, Zezheng Fu, Yuquan Leng, Chenglong Fu  
**Venue:** IEEE TNSRE, 2024  
**DOI:** 10.1109/TNSRE.2024.3443073

### What they do
```
Gaze tracker  →  select object / grasp point
Facial EMG    →  confirm intended action
Robot arm     →  pick-place / feed / pour
```

### What we take
- Two-factor HCI: **gaze = select**, **muscle = confirm**
- Assistive goal for motor-impaired / SCI users
- Proof that hybrid control beats gaze-only or EMG-only

### What we change
- Robot ADLs → **home appliances** (lamp / fan / plug)
- Costly eye tracker + FEMG → **webcam gaze/head + MyoWare**
- Always execute task → **Act / Abstain** policy
- Task time metric → primary **False Actuation Rate (FAR)**

---

## 3. Chamberland EMBC 2024 role (important)

Chamberland is **not** the base anymore.  
It remains a **strong supporting paper** for the module: EMG + camera scene understanding / YOLO.

---

## 4. Novelty statement (use in viva)

> Lin et al. already show that gaze should select and muscle should confirm for assistive control.  
> MioGaze extends that hybrid principle from robotic ADLs to **smart-home appliance actuation**, using low-cost webcam + wearable EMG, and adds **selective abstention** evaluated by **False Actuation Rate**.
