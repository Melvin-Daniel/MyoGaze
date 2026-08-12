# Why NeuroShift Matters — Need Analysis + Base Paper Review

**For guide / review panel**  
**Date:** July 2026  
**Sources:** WHO, World Stroke Organization (WSO), Global Burden of Disease (GBD), Census of India 2011, NSS 76th Round, peer-reviewed literature

---

## Part A — Why this project is useful (real population data)

### A1. The core problem NeuroShift addresses

Many people cannot easily use switches, remotes, or touchscreens because of:
- stroke-related motor weakness / paralysis
- spinal cord injury
- limb amputation / limited hand function
- age-related motor decline
- neuromuscular conditions

**NeuroShift goal:** help them control home devices (light, fan, plug) using **remaining muscle signals (EMG) + camera context**, with **safe abstention** when unsure.

---

### A2. Global need (authoritative numbers)

| Condition / metric | Approximate number | Source |
|---|---|---|
| People living with stroke effects | **~93.8 million** (2021); newer estimates ~**104.8 million** (2023) | WHO / GBD / WSO Global Stroke Fact Sheet |
| New strokes per year | **~11.9–13.2 million** | WHO / GBD |
| Stroke deaths per year | **~6.8–7.3 million** | WHO / GBD |
| Lifetime stroke risk | **1 in 4 adults** over age 25 | WSO / WHO |
| Stroke cost to world economy | **>~US$890 billion/year** (~0.66% global GDP); projected toward **US$1 trillion** by 2030 | WSO / Lancet Neurology Commission |
| People living with spinal cord injury | **~20.6 million** (2019) | GBD 2019 / Lancet Neurology |
| People living with traumatic limb amputation | **~57.7 million** (2017) | Prosthetics & Orthotics International (GBD-based) |

**Clinical relevance for NeuroShift:**
- Stroke is a leading cause of **long-term motor disability**.
- WHO notes survivors often face **persistent motor deficits**, reduced ability to do daily activities, and **loss of independence**.
- Indian rehab survey data: nearly **90% of stroke survivors** report movement impairment in upper or lower limb (national survey analysis).
- Literature commonly cites: **15–30%** of stroke survivors remain permanently disabled; many need ongoing care support.

---

### A3. India-specific need (important for local relevance)

| Metric | Number / fact | Source |
|---|---|---|
| Persons with disability (Census 2011) | **26.8 million** | Census of India 2011 |
| Movement / locomotor disability share | **~20.3%** of disabled persons (largest single category in 2011 typology) | Census of India 2011 |
| Disability prevalence (NSS 2018) | **~2.2%** of population | NSS 76th Round |
| Living alone among PwD | **~3.7%** | NSS 76th Round |
| India new stroke cases (2021) | **>~1.25 million** (about **10% of global** new strokes) | GBD / Lancet Neurology reporting |
| India stroke prevalence trend | From **~4.4 million (1990)** to **~9.4 million (2021)** (~**+47%**) | Lancet Neurology / WSO reporting |
| India stroke incidence (systematic review) | Roughly **108–172 per 100,000 / year** | Jones et al., Int J Stroke 2022 |

**Why this matters in India:**
- Most global stroke burden is in **low- and middle-income countries**.
- Care is often family-based; caregiver anxiety/depression reported in **17–50%** of stroke caregivers in Indian setting reviews.
- Affordable, non-invasive home assistance (MyoWare + webcam + ESP32) is more realistic than hospital-only solutions.

---

### A4. Who NeuroShift can help (target groups)

| Group | Why they struggle with normal controls | How NeuroShift helps |
|---|---|---|
| Stroke survivors with weak hand/arm | Remotes, switches, phones hard to use | Sparse EMG effort + scene context controls devices |
| People with partial paralysis / hemiparesis | One-sided motor loss | Remaining muscle activity as confirmation signal |
| Spinal cord injury (incomplete) | Limited voluntary movement | Low-effort volition + camera affordances |
| Upper-limb amputees / prosthesis users | Related to base paper domain | Our work extends same idea from prosthesis grips → home devices |
| Older adults with reduced hand mobility | Fatigue, arthritis, tremor | Avoid complex gesture dictionaries |
| Caregivers / families | High burden, constant assistance for ADLs | Safer automation + decision logs (Sem 8) |

---

### A5. Usefulness in all dimensions (say this to your guide)

| Dimension | Why useful |
|---|---|
| **Social / humanitarian** | Supports independent living for millions with motor disability |
| **Clinical / rehab** | Extends multimodal EMG+vision from prosthesis literature to daily home ADLs |
| **Technical / research** | Novel focus: home intention + Act/Abstain + FAR (not just gesture accuracy) |
| **Economic** | Stroke alone costs hundreds of billions globally; reducing caregiver dependence has value |
| **India relevance** | Rising stroke prevalence; large locomotor disability population; low-cost hardware stack |
| **Startup / portfolio** | Clear problem → prototype → paper → MVP path |
| **Academic (IEEE)** | Clean extension of EMBC 2024 base paper with measurable safety metric |

---

## Part B — Base paper analysis (full read)

**Paper:** *Visual Scene Understanding for Enhanced EMG Gesture Recognition*  
**Authors:** Félix Chamberland, Thomas Labbé, Simon Tam, Erik Scheme, Benoit Gosselin  
**Venue:** IEEE EMBC 2024  
**DOI:** 10.1109/EMBC53108.2024.10782354  
**Affiliation:** Université Laval + University of New Brunswick

---

### B1. What the paper claims (in plain words)

They build a **real-time multimodal system** where:
1. **HD-EMG** predicts hand **gestures** (6 classes).
2. A **head-mounted webcam + YOLO** detects everyday objects.
3. **MediaPipe** tracks the hand.
4. An **Object Likelihood Filtering (OLF)** module decides which object the user is likely trying to grab.
5. Vision then **limits allowed gestures** to grips that make sense for that object.
6. Result: fewer false gesture detections during transitions and static holds, while keeping the user in control.

**Domain:** myoelectric **prosthesis** control (not smart home).

---

### B2. System components (technical)

| Module | What they used |
|---|---|
| EMG sensor | **EMaGer** 64-channel HD-EMG bracelet (1 kHz) |
| EMG model | **SDCNN** (Siamese Deep CNN) + Euclidean nearest centroid; confidence via softmax of distance complements |
| Gesture classes (6) | open-hand, tripod, power, thumbs-up, pinch, pointed index |
| Camera | EMEET C960 webcam, head-mounted, 640×480, ~10 fps |
| Vision | Custom **YOLOv8-small**, 28 object classes from COCO + OpenImages |
| Hand tracking | MediaPipe Hands |
| Fusion idea | Object Likelihood Filtering (presence + confidence + distance to hand over 2 s) enables object-related grips |
| Fallback | If no object detected: neutral + power grip with proportional control |

**SDCNN accuracy (intra-session):** 98.6%  
**YOLO mAP@[.5,.95]:** 0.368 · classification precision ~57%  
**YOLO inference:** ~10 ms on GTX 1080

---

### B3. Experiment and results

**Ethics:** Laval University REC approval 2019-268…  
**Pilot:** 1 able-bodied subject, 2 scenarios × 20 trials each  
**Comparison:** EMG-only vs EMG+vision

| Scenario | Transition errors fixed | Static-hold errors fixed |
|---|---|---|
| #1 (mug tripod → apple power) | **100%** (5.7 → 0) | **68.2%** (10.7 → 3.4) |
| #2 (bottle → phone thumbs-up → point) | **60.7%** (5.6 → 2.2) | **93.0%** (7.1 → 0.5) |

**Takeaway they prove:** vision context can strongly reduce false EMG gesture predictions.

---

### B4. Strengths of the base paper

1. Clear multimodal architecture (EMG + YOLO + hand tracking).
2. Preserves user agency (EMG stays primary; vision curates options).
3. Real-time proof-of-concept with measurable error reduction.
4. Confidence-aware EMG model (useful when gesture is ambiguous).
5. Good motivation: prosthesis control is unintuitive and EMG-only is fragile.

---

### B5. Limitations (important — this is where NeuroShift begins)

| Limitation in base paper | Why it matters | NeuroShift response |
|---|---|---|
| Predicts **gestures**, not home-device actions | Not directly about independent living at home | Predict **appliance intention** (lamp/fan/plug) |
| Target = **prosthesis grip selection** | Different problem than smart-home control | Assistive smart-home domain |
| Uses **64-channel HD-EMG** | Expensive / not student-prototype friendly | Sparse **MyoWare** (realistic low-cost) |
| Vision role = **filter allowed grips** | Does not choose “which device to actuate” | Vision builds **affordance candidates** |
| No explicit **Act / Abstain** for IoT safety | False device actuation is critical at home | Selective abstention + **FAR** metric |
| Pilot = **1 able-bodied subject** | Limited generalization | Multi-user NeuroShift-ADL pilot (Sem 7–8) |
| Hard when many nearby objects / occlusion | Authors admit this | Our core test case = multi-object ambiguity |
| No personal habit prior | Same scene always treated similarly | Sem 8 temporal prior |
| No caregiver decision audit | Not needed for prosthesis demo | Decision-level explanation log |

**Authors themselves note:** crowded scenes, occlusion, unknown objects, and better fusion of EMG/vision confidence need future work.

---

### B6. Exact extension statement (use in reports)

> Chamberland et al. (EMBC 2024) showed that visual scene understanding can reduce false EMG gesture detections for prosthesis control by enabling only object-compatible grips. NeuroShift extends this multimodal paradigm from **gesture validation for prostheses** to **home-device intention inference for assistive living**. Using sparse EMG volition, ambient object/pose affordances, and (in Phase 2) personal priors with selective abstention, NeuroShift targets lower **false smart-home actuations** for people with motor disabilities.

---

## Part C — How to explain usefulness + base paper in 90 seconds

1. **Need:** ~100 million people live with stroke effects globally; India alone has ~9+ million prevalent stroke cases and millions with locomotor disability. Many struggle with switches/remotes.  
2. **Base paper:** EMG + camera reduces wrong **gestures** for prostheses.  
3. **Gap:** That does not solve wrong **home device actuations** for independent living.  
4. **Our solution:** Camera proposes feasible devices; EMG confirms effort; system Acts or Abstains.  
5. **Why useful:** social impact + research novelty + low-cost India-feasible hardware + IEEE path.

---

## Part D — Key citations (for slides / report)

1. WHO Stroke Fact Sheet — ~93.8M prevalent strokes (2021), 11.9M new cases, 1 in 4 lifetime risk.  
2. WSO Global Stroke Fact Sheet / Lancet Neurology Commission — economic cost >US$890B; burden rising in LMICs.  
3. GBD SCI analysis — ~20.6M people living with spinal cord injury (2019).  
4. McDonald et al. — ~57.7M living with traumatic limb amputation (2017 estimate).  
5. Census of India 2011 — 26.8M PwD; movement disability ~20.3%.  
6. NSS 76th Round (2018) — disability prevalence ~2.2%.  
7. India stroke reporting (GBD/Lancet) — ~1.25M new cases in 2021; prevalence ~9.4M.  
8. Chamberland et al., IEEE EMBC 2024 — base paper.

---

## Bottom line

NeuroShift is useful because **the population need is large and growing**, especially for stroke and motor disability in India and globally.  
The base paper proves **EMG + vision works for safer gesture control**.  
Our contribution is to turn that idea into **safer home intention control** for independent living.
