# NeuroShift — Latest 10 IEEE Reference Papers (2024–2026)

**For guide review**  
**Base paper:** Chamberland et al., IEEE EMBC 2024  
**Filter:** ALL 10 are **IEEE** (IEEE Xplore, 10.1109 DOIs), years **2024–2026**. Non-IEEE papers (Frontiers / arXiv / ROBOMECH) removed from the core-10.

---

## How to tell your guide

> Sir, all 10 are **IEEE papers** from **2024–2026**.  
> **P1 Chamberland EMBC 2024** is our **base paper**.  
> Each NeuroShift module maps to one IEEE paper.  
> Our novelty is: **gaze selects appliance + EMG confirms + Act/Abstain + FAR** for assistive smart-home control.

---

## Latest Core-10 (all IEEE, module-wise)

| # | Paper | Year | IEEE Venue | Module | Why chosen |
|---|---|---|---|---|---|
| **P1 BASE** | Chamberland et al., *Visual Scene Understanding for Enhanced EMG Gesture Recognition* | **2024** | IEEE EMBC | Overall base: EMG + scene vision | Sir-approved base; EMG + YOLO scene context |
| **P2** | Lin / Yang et al., *Hybrid Gaze and FEMG-Controlled Assistive Robotic System* | **2024** | IEEE TNSRE | Gaze select + muscle confirm | Closest to “looking selects, muscle confirms” |
| **P3** | Sakthimohan et al., *Automated Smart Home Assistive System Using Eye Gestures* | **2024** | IEEE ICACCS | Gaze / eye → home appliances | Webcam eye control of home devices |
| **P4** | Dere et al., *Lightweight Vision Language Model-Guided Gesture Recognition Based on EMG* | **2025** | IEEE Sensors Journal | Vision-guided EMG / motor intent | Latest vision + EMG motor-intent pipeline |
| **P5** | Wang et al., *Robust Myoelectric Gesture Recognition for Reliable Human–Robot Interaction* | **2025** | IEEE RA-L | EMG reliability / reject → confirm | Reliable EMG under uncertainty (Act/Hold basis) |
| **P6** | Jeong & Woo, *CIDER: On-Device Smart-Home Intent Reasoning* | **2025** | IEEE Access | Smart-home intent reasoning | On-device intent inference for the home |
| **P7** | *TFVF-CNN: sEMG + Visual Feature Fusion* (ROBIO) | **2024** | IEEE ROBIO | Multimodal sEMG + vision fusion | Fuses muscle + camera features |
| **P8** | *Multimodal sEMG + Vision Hand Gesture Fusion* (M2VIP) | **2024** | IEEE M2VIP | Multimodal fusion (alt) | Second EMG + vision fusion evidence |
| **P9** | Zhao / Lv et al., *RT-DETR: DETRs Beat YOLOs on Real-Time Object Detection* | **2024** | IEEE/CVF CVPR (IEEE Xplore) | Object detection | Modern real-time detector for appliances |
| **P10** | Li et al., *Multi-modal Dynamic Fusion Network for Intent Understanding in Assisted Older Adults* | **2025** | IEEE ICIVP | Assistive multimodal intent | Latest assistive multimodal intent fusion |

---

## Module ← paper map (what sir asked)

| NeuroShift module | Latest IEEE paper(s) | What we take | What we change |
|---|---|---|---|
| **Overall architecture** | **P1 Chamberland 2024 (BASE)** | EMG + camera scene understanding | Prosthesis gestures → **home intention** |
| **Appliance / object detection** | **P9 RT-DETR 2024** (+ YOLO in P1) | Real-time detection | Detect lamp/fan/plug for home |
| **Gaze / eye / head selection** | **P2 2024, P3 2024** | Gaze/eye as selector | Select **appliance**, not robot grasp |
| **EMG confirmation / volition** | **P4 2025, P5 2025** | Muscle signal as intent + reliability | Sparse **MyoWare confirm**, not gesture dictionary |
| **Multimodal fusion** | **P7 2024, P8 2024, P10 2025** | Fuse vision + physiology | Output = home **Act/Abstain** |
| **Act / Abstain safety** | **P5 2025** (reliability/reject) | Reject when uncertain | Apply to **False Actuation Rate** on home devices |
| **Smart-home assistive goal** | **P3 2024, P6 2025** | Independent living / intent | Add EMG confirm + FAR + Indian wired relay hub |

---

## Exact IEEE citations / DOIs (download these)

### P1 — BASE
Chamberland, F., Labbé, T., Tam, S., Scheme, E., Gosselin, B.  
*Visual Scene Understanding for Enhanced EMG Gesture Recognition.*  
**IEEE EMBC 2024.** DOI: **10.1109/EMBC53108.2024.10782354**

### P2
Lin, C., Yan, X., Fu, Z., Leng, Y., Fu, C. (and coauthors as listed on IEEE)  
*Empowering High-Level Spinal Cord Injury Patients… Hybrid Gaze and FEMG-Controlled Assistive Robotic System.*  
**IEEE TNSRE, 2024.** DOI: **10.1109/tnsre.2024.3443073**

### P3
Sakthimohan, M., Sakthi, S., Pugalmani, R., Harish Kumar, R., Elizabeth Rani, G.  
*Automated Smart Home Assistive System Implementation for Physically Impaired Community Using Eye Gestures.*  
**IEEE ICACCS 2024.** DOI: **10.1109/icaccs60874.2024.10717287**

### P4
Dere, M.D., Cheong, S., Jo, J.-H., Ku, G., Lee, B.  
*Lightweight Vision Language Model-Guided Gesture Recognition Based on Electromyography.*  
**IEEE Sensors Journal, 2025.** DOI: **10.1109/jsen.2025.3565766**

### P5
Wang et al.  
*Robust Myoelectric Gesture Recognition for Reliable Human–Robot Interaction.*  
**IEEE Robotics and Automation Letters (RA-L), 2025.** DOI: **10.1109/lra.2025.3546095**

### P6
Jeong, Woo.  
*CIDER: On-Device Smart-Home Intent Reasoning.*  
**IEEE Access, 2025.** DOI: **10.1109/access.2025.3634621**

### P7
*TFVF-CNN: sEMG and Visual Feature Fusion CNN for Gesture Recognition.*  
**IEEE ROBIO 2024.** DOI: **10.1109/robio64047.2024.10907446**

### P8
*Multimodal sEMG and Vision Hand Gesture Recognition Fusion.*  
**IEEE M2VIP 2024.** DOI: **10.1109/m2vip62491.2024.10746196**

### P9
Zhao, Y., Lv, W., Xu, S., et al.  
*DETRs Beat YOLOs on Real-Time Object Detection (RT-DETR).*  
**IEEE/CVF CVPR 2024** (IEEE Xplore). arXiv: **2304.08069**

### P10
Li, Z., Dong, L., Xu, T., Sun, J., Zhu, G., Guo, Z.  
*Multi-modal Dynamic Fusion Network for Intent Understanding in Assisted Older Adults.*  
**IEEE ICIVP 2025.** DOI: **10.1109/icivp66296.2025.00029**

---

## Year mix (honest)

| Year | Count |
|---|---|
| 2024 | 5 (incl. base) |
| 2025 | 5 |

All core-10 are **IEEE** and **2024 or newer**.

---

## Note for sir (honest disclosure)

- The earlier "Act/Abstain" paper (Gaus et al.) was an **arXiv preprint**, so it is **removed** from the IEEE-only list.
- **Act/Abstain is now our own contribution.** The IEEE reliability/reject basis is **P5 (RA-L 2025)**.
- **RT-DETR (P9)** was published at **IEEE/CVF CVPR 2024** (indexed in IEEE Xplore); if your guide wants strictly journal/conference-IEEE only, it can be dropped and replaced with an IEEE detection paper.

---

## Novelty statement vs latest IEEE papers

Latest IEEE papers already cover:
- EMG + vision fusion
- Gaze + FEMG hybrid
- Eye-gesture smart homes
- Smart-home intent reasoning
- Reliable / reject EMG recognition

**Still open for NeuroShift:**
> Gaze-selected **home appliance** targeting + **sparse wearable EMG confirmation** + **Act/Abstain**, evaluated mainly by **False Actuation Rate**, for **Indian wired-home** assistive control.

That is what we claim — not “first EMG+camera.”

---

## Optional IEEE extras (if sir asks for more than 10)

1. IEEE MATEC/related **2025** — Economical eye-tracking with MediaPipe facial landmarks (`10.1051/matecconf/202541710001`) *(note: not 10.1109)*
2. Additional IEEE EMBC / EMBS 2024–2025 EMG-intent papers (search IEEE Xplore: "EMG intent assistive 2025")
