# Literature Comparison Matrix (Seed — Phase 0)

> Goal: expand toward ~100 papers. This seed set anchors novelty claims.
> Columns are comparison axes, not summaries.

| ID | Paper | Venue/Year | Task | Modalities | Fusion | Personalization | XAI | Home vs Prosthesis | Gap left for NeuroShift |
|---|---|---|---|---|---|---|---|---|---|
| P01 | Chamberland et al. Visual Scene Understanding for Enhanced EMG Gesture Recognition | EMBC 2024 | Gesture robustness | EMG + YOLO objects | Late gate / validation | No | Limited | Prosthesis | Gesture rescue ≠ appliance intention; no abstention policy |
| P02 | Multimodal fusion of EMG and vision for grasp intent | Frontiers RA 2024 | Grasp type intent | EMG + egocentric video + gaze | Bayesian evidence fusion | No | Limited | Prosthesis | Single-object reach assumption; not IoT actuation |
| P03 | Lightweight VLM-Guided Gesture Recognition based on EMG | IEEE 2025 | Gesture under sensor shift | EMG + VLM vision | VLM pseudolabels EMG | Cross-subject robustness | Limited | Rehab/assistive device | Still gesture decoding; not home-action policy |
| P04 | TFVF-CNN multimodal sEMG + visual features | ROBIO 2024 | Gesture accuracy | sEMG + images | Feature fusion CNN | No | No | HCI/rehab | Accuracy-centric; no context reasoning for devices |
| P05 | Multimodal Hand Gesture Recognition Fusion of sEMG and Vision | M2VIP 2024 | Gesture + robot control | sEMG + skeleton | CNN fusion | No | No | HRI | Predefined gestures; no smart-home intention |
| P06 | MoEMba Mamba MoE for HD-sEMG | arXiv 2025 | Gesture (inter-session) | HD-sEMG | SSM/MoE | Session robustness | No | HCI | Wrong sensor density for MyoWare; gesture labels |
| P07 | EMamba heatmap + ResNet-SSM | Biomed Signal Proc. 2026 | Gesture cross-subject | sEMG | Hybrid SSM | Cross-subject | No | Wearable HMI | Backbone novelty, not intention/home |
| P08 | CIDER ontology-augmented on-device sLLM intent | IEEE Access 2025 | Vague smart-home intent | Language + ontology KG | RAG/agent | User context | Process transparency | Smart home | No physiological grounding; excludes non-verbal users |
| P09 | VCU-LLM vague command understanding | ACM 2025/26 | Vague commands → device plans | On-device LLM | Prompt retrieval | Household simulation | Limited | Smart home | Text/voice-first; no EMG confirmation |
| P10 | Sagacity EMG/EOG multimodal smart home (older adults) | arXiv 2025 | SHT interaction | EMG + EOG | Exploratory multimodal | Living-lab | Qualitative | Smart home | Exploratory HCI; not affordance intention + FAR science |
| P11 | Subtle EMG gestures for reduced hand mobility | Manitoba HCI | Smart-home gestures | EMG | Direct mapping | Accessibility focus | No | Smart home | Still gesture→command; fatigue noted as issue |
| P12 | EMG wake gestures for false activations in ADL | JNE 2025 | Reject out-of-set ADL | EMG wake gesture | DTW toggle | Online user-in-loop | No | Myoelectric interfaces | Sleep/wake toggle ≠ scene-aware intention |
| P13 | Explainable AI SHAP for EMG channels/features | TMRB 2024 | Gesture + feature selection | EMG | Classical/ensemble | No | SHAP channels | Prosthesis | Explains sensors, not device decisions |
| P14 | EMGCipher XAI resource optimization | EMBC 2024 | Gesture + sensor importance | sEMG | DL + XAI | No | Sensor/feature XAI | Assistive limb | Same limitation as P13 |
| P15 | XAI GNN HD-EMG gesture intention | TCE 2023 | Fine gesture intention | HD-EMG | GNN | Topology refine via XAI | Yes (graph) | Consumer/HCI | HD-EMG; gesture intention ≠ home action |
| P16 | DMPS dynamic multimodal path selection | ICIVP 2025 | Intent for assisted older adults | Multi (gesture etc.) | Dynamic path + Transformer | Task-specific | Limited | Assistive fetch | Not EMG+ambient home appliances |
| P17 | Temporal-spatial elderly care smart home | WorldSUAS 2025 | Routine/anomaly | Ambient sensors | LSTM + ontology | Routine patterns | Limited | Smart home | No EMG volition confirmation |
| P18 | ACKnowledge affordance interaction planning | CHI 2025 | Affordance-compatible agent plans | VLM + LLM + KG | Symbolic+neural | Personalization | Understandable process | Household agents | No EMG; agent planning not sparse-wearable confirmation |
| P19 | MindEye-OmniAssist gaze + LLM assistive robot | arXiv 2025 | Implicit intention | Gaze + VLM/LLM | LLM planning | Open vocabulary | Limited | Assistive robot | Gaze-centric; not EMG home IoT |
| P20 | CASPER VLM intents for assistive teleoperation | CoRL 2025 | Diverse teleop intents | Vision + control inputs | VLM reasoning | Skill library | Limited | Teleoperation | Robot teleop, not smart-home EMG |
| P21 | Multimodal domestic service robot for declined expression | ISR 2023 | Multimodal HRI intent | Multi incl. physio/behavior | Adaptive multimodal | Preference learning noted | Limited | Domestic robot | Robot HRI; dataset scarcity for disabled users noted |
| P22 | EEG + eye + gesture intention fusion | Sci Reports 2025 | 6-class interaction intent | EEG, eye, gesture | Cross-attention ensemble | No | Limited | HCI | No home devices; clinical sensors |
| P23 | PULSE multimodal daily activity dataset | HF 2025 | Scene/action/grasp onset | EMG+IMU+eye+MoCap+cam | Benchmark suite | Missing-modality | N/A | Daily activity | No appliance actuation labels |
| P24 | Egocentric RGB-D + EMG/IMU household | HF | Manipulation / IL | EMG+IMU+RGB-D | Dataset | N/A | N/A | Household robot learning | No smart-home device intention |
| P25 | MOVMUS-UJI EMG+kinematics ADL | Zenodo 2024 | Ergonomic ADL | EMG + CyberGlove | Dataset | Product tags | N/A | Ergonomics | No IoT labels |
| P26 | EPFL-Smart-Kitchen-30 | 2025 | Kitchen behavior | Multi-cam, IMU, gaze | Multi benchmarks | N/A | VLM QA | Kitchen | No EMG |
| P27 | MHAD home video + physiological | ICASSP 2025 | Home activity | Multi-angle video + vitals | Dataset | N/A | N/A | Home | No EMG→device |
| P28 | Machine learning with reject option (survey) | Survey | Selective prediction | General | Theory | N/A | Reliability framing | General ML | Not instantiated for EMG–smart-home FAR |
| P29 | Reliable VQA: abstain rather than answer | arXiv 2022 | Selective VQA | Vision+language | Selective prediction | N/A | Reliability | Vision-language | Method transfer opportunity for NeuroShift |
| P30 | Real-time intent sensing assistive devices | Prosthesis journal | Intent + maintenance | EMG (+ future smart home) | Modular sensors | Mentions drop-in sensors | Limited | Assistive | Suggests smart-home networking as future work — NeuroShift occupies that |

---

## Pattern synthesis

1. **Prosthesis multimodal stacks** optimize grasp/gesture under egocentric views.
2. **Smart-home intent stacks** optimize language/ontology without EMG safety grounding.
3. **EMG smart-home HCI** still mostly maps gestures to commands.
4. **False activation** is known (wake gestures), but solved via EMG toggles—not affordance policies.
5. **Abstention/selective prediction** is mature elsewhere; rare in EMG–IoT actuation papers.
6. **Datasets** never jointly label sparse EMG + ambient scene + appliance action + abstain.

## White space (NeuroShift)

```
EMG volition (sparse)
   × visual affordances (multi-object ambient)
   × selective actuation (act/abstain)
   × personal temporal prior
   × appliance-level labels
   × decision-level audit
```

No seeded paper occupies this full intersection.

## Expansion plan to ~100

Fill evenly across:
1. EMG temporal models (Transformer/TCN/SSM) — cite as baselines, not novelty
2. Object detection / pose / affordance
3. Multimodal fusion theory
4. Ambient intelligence / HAR
5. Assistive HCI for motor impairment
6. VLM/LLM agents for homes
7. XAI for physiological sensing
8. Selective prediction / uncertainty / calibration

For each added paper: fill the same comparison axes; update gap column.
