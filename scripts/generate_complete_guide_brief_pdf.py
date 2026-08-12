"""Generate master NeuroShift guide brief PDF covering all locked topics."""

from pathlib import Path

from fpdf import FPDF

OUT = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "NeuroShift_Complete_Guide_Brief.pdf"
)


class MasterPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 7, "NeuroShift 2.0 | Complete Guide Brief", align="L")
        self.ln(9)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def title_block(self, title: str, subtitle: str):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(20, 20, 20)
        self.multi_cell(0, 9, title)
        self.ln(1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(70, 70, 70)
        self.multi_cell(0, 5.2, subtitle)
        self.ln(3)

    def section(self, text: str):
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(25, 25, 25)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def sub(self, text: str):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, text)
        self.ln(0.5)

    def body(self, text: str):
        self.set_font("Helvetica", "", 9.2)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 4.8, text)
        self.ln(0.4)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 9.2)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 4.8, f"  -  {text}")
        self.ln(0.15)

    def quote(self, text: str):
        self.set_fill_color(245, 247, 250)
        self.set_font("Helvetica", "I", 9.2)
        self.set_text_color(40, 40, 40)
        self.set_x(self.l_margin + 2)
        self.multi_cell(
            self.w - self.l_margin - self.r_margin - 4, 5, text, fill=True
        )
        self.ln(1.5)

    def code(self, text: str):
        self.set_fill_color(248, 248, 248)
        self.set_font("Courier", "", 7.5)
        self.set_text_color(30, 30, 30)
        for line in text.strip().split("\n"):
            self.set_x(self.l_margin + 2)
            self.multi_cell(
                self.w - self.l_margin - self.r_margin - 4, 4, line, fill=True
            )
        self.ln(1.2)

    def table(self, headers, rows, col_widths):
        self.set_font("Helvetica", "B", 7.5)
        self.set_fill_color(230, 235, 245)
        self.set_text_color(20, 20, 20)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 6, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 7.5)
        fill = False
        for row in rows:
            x0, y0 = self.get_x(), self.get_y()
            heights = []
            for i, cell in enumerate(row):
                self.set_xy(x0 + sum(col_widths[:i]), y0)
                lines = self.multi_cell(
                    col_widths[i], 4, cell, border=0, dry_run=True, output="LINES"
                )
                heights.append(max(len(lines), 1) * 4)
            row_h = max(heights + [6])
            if y0 + row_h > self.h - self.b_margin:
                self.add_page()
                y0 = self.get_y()
                x0 = self.get_x()
            for i, cell in enumerate(row):
                x = x0 + sum(col_widths[:i])
                self.set_xy(x, y0)
                if fill:
                    self.set_fill_color(245, 247, 252)
                else:
                    self.set_fill_color(255, 255, 255)
                self.rect(x, y0, col_widths[i], row_h, style="DF")
                self.set_xy(x + 0.8, y0 + 0.5)
                self.multi_cell(col_widths[i] - 1.6, 4, cell)
            self.set_xy(x0, y0 + row_h)
            fill = not fill
        self.ln(1.8)


def build() -> Path:
    pdf = MasterPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.title_block(
        "NeuroShift 2.0 - Complete Guide Brief",
        "Single document covering base paper extension, novelty, phases, hardware, "
        "Indian home integration, cost, PwD scenarios, cameras, and population need | "
        "July 2026",
    )

    pdf.quote(
        "Principle: Looking selects. Muscle confirms. Unsure -> Abstain. "
        "Novelty: gaze-selected home intention + EMG confirmation + Act/Abstain + FAR metric."
    )

    pdf.section("0. 5-minute pitch for guide")
    pdf.bullet("Problem: motor-impaired users struggle with switches; wrong actuations are unsafe.")
    pdf.bullet("Base paper (EMBC 2024): EMG + vision improves prosthesis GESTURE recognition.")
    pdf.bullet("Our idea: camera detects appliances + gaze selects target; EMG confirms toggle; Act/Abstain.")
    pdf.bullet("Sem 7: working demo (MyoWare + webcam + ESP32 relay hub, 2-3 devices).")
    pdf.bullet("Sem 8: eye-gaze upgrade, evaluation, IEEE-style paper.")
    pdf.bullet("Ask: approve scope, ethics, Sem 7 deliverables, title freeze.")

    # ---- 1 NEED ----
    pdf.section("1. Why this project is needed (population data)")
    pdf.table(
        ["Metric", "Number", "Source type"],
        [
            ["People living with stroke effects", "~94-105 million", "WHO / GBD / WSO"],
            ["New strokes per year", "~12-13 million", "WHO / GBD"],
            ["Lifetime stroke risk", "1 in 4 adults (25+)", "WSO / WHO"],
            ["Stroke economic cost", "> US$890B / year", "WSO / Lancet"],
            ["Spinal cord injury survivors", "~20.6 million (2019)", "GBD"],
            ["Traumatic limb amputees", "~57.7 million (2017)", "GBD-based study"],
            ["India persons with disability", "26.8 million", "Census 2011"],
            ["Movement disability share (India)", "~20.3% of PwD", "Census 2011"],
            ["India stroke prevalence", "~9.4 million (2021)", "GBD / Lancet reporting"],
            ["India new strokes (2021)", "~1.25 million (~10% global)", "GBD / Lancet reporting"],
        ],
        [58, 58, 64],
    )
    pdf.body(
        "NeuroShift targets independent living assistance for people with residual "
        "voluntary muscle activity who cannot easily use remotes/switches."
    )

    # ---- 2 BASE ----
    pdf.add_page()
    pdf.section("2. Base paper + our extension")
    pdf.sub("Base paper")
    pdf.body(
        "Visual Scene Understanding for Enhanced EMG Gesture Recognition | "
        "Chamberland, Labbe, Tam, Scheme, Gosselin | IEEE EMBC 2024 | "
        "DOI 10.1109/EMBC53108.2024.10782354"
    )
    pdf.bullet("EMG (EMaGer 64-ch HD-EMG) + head webcam + YOLOv8 + MediaPipe Hands")
    pdf.bullet("SDCNN classifies 6 hand grips; vision filters object-compatible grips (OLF)")
    pdf.bullet("Domain: myoelectric prosthesis control")
    pdf.bullet("Result: fewer false gesture detections in pilot trials")

    pdf.sub("What they do NOT solve")
    pdf.bullet("Smart-home appliance control")
    pdf.bullet("Gaze-based appliance selection")
    pdf.bullet("Act/Abstain safety for IoT")
    pdf.bullet("False Actuation Rate for home devices")
    pdf.bullet("Low-cost sparse EMG + Indian wired homes")

    pdf.sub("Our extension (one paragraph)")
    pdf.quote(
        "Chamberland et al. use vision to rescue EMG gestures for prosthesis grips. "
        "NeuroShift extends this multimodal idea to assistive smart homes: the camera "
        "detects appliances and estimates which one the user is looking at; sparse EMG "
        "confirms whether they truly want to toggle it; the system Acts or Abstains to "
        "minimize False Actuation Rate."
    )

    pdf.table(
        ["Point", "Base paper", "NeuroShift"],
        [
            ["Predicts", "Gesture / grip class", "Home device action or Abstain"],
            ["Vision role", "Validate grips", "Detect appliances + gaze-select target"],
            ["EMG role", "Classify gesture", "Confirm volition only"],
            ["Selector", "Hand near object", "Head/eye gaze (primary)"],
            ["Safety", "Fewer false movements", "Two-factor + Act/Abstain + FAR"],
            ["Hardware", "Custom 64-ch HD-EMG", "MyoWare + 2xESP32 + relays"],
            ["Setting", "Prosthesis lab scenarios", "Indian wired-home appliances"],
        ],
        [28, 76, 76],
    )

    # ---- 3 NOVELTY ----
    pdf.section("3. Novelty (locked)")
    pdf.quote("Looking selects. Muscle confirms. Unsure -> Abstain.")
    pdf.table(
        ["Novelty piece", "Meaning"],
        [
            ["Gaze-selected home intention", "Camera finds appliances AND which one user is looking at"],
            ["EMG confirmation", "Muscle effort confirms real intent (not a gesture dictionary)"],
            ["Act / Abstain", "If gaze or EMG unclear, do nothing (safer than guessing)"],
            ["FAR metric", "Primary success = False Actuation Rate, then intention F1"],
        ],
        [48, 132],
    )
    pdf.body(
        "We do NOT claim: first EMG+camera fusion, Ninapro SOTA, or Transformer novelty alone."
    )

    pdf.sub("Official real-time pipeline")
    pdf.code(
        """Webcam -> YOLO appliances + Gaze/head direction
        -> Match gaze to appliance (dwell 0.5-1.0 s) -> SELECTED TARGET
MyoWare EMG -> Volition confirm
If gaze stable AND EMG high -> ACT (MQTT -> ESP32 -> relay)
Else -> ABSTAIN
Dashboard logs: target, EMG, decision, reason"""
    )

    # ---- 4 PHASES ----
    pdf.add_page()
    pdf.section("4. Phase 1 (Sem 7) and Phase 2 (Sem 8)")
    pdf.table(
        ["", "Phase 1 / Sem 7", "Phase 2 / Sem 8"],
        [
            ["Goal", "BUILD working prototype + live demo", "PROVE research + IEEE draft"],
            ["Gaze", "Head/face direction (MediaPipe)", "Eye-gaze model + dwell calibration"],
            ["Fusion", "Rule: gaze AND EMG -> Act else Abstain", "Learned fusion + FAR-tuned abstention"],
            ["Extra", "Logger + simple dashboard", "Habit prior + decision XAI + caregiver UI"],
            ["Demo", "2-3 appliances, Act + Abstain scenes", "Full eval tables + polished demo"],
            ["Success", "External sees reliable live control", "Lower FAR vs baselines + paper"],
        ],
        [28, 76, 76],
    )

    pdf.sub("Phase 1 algorithms")
    pdf.bullet("Objects: YOLO11 / YOLOv8 / RT-DETR")
    pdf.bullet("Gaze: MediaPipe Face Mesh / head pose")
    pdf.bullet("EMG: RMS/MAV threshold or small TCN (confirm only)")
    pdf.bullet("IoT: MQTT + ESP32 relay hub")

    pdf.sub("Phase 2 algorithms")
    pdf.bullet("Eye-gaze estimation; calibrated volition; small fusion network")
    pdf.bullet("Personal temporal prior; decision-level explanations")
    pdf.bullet("Baselines: EMG-only, gaze/vision-only, Chamberland-style gate, always-act")

    pdf.sub("Out of scope (say to guide)")
    pdf.bullet("Wheelchair control, hospital system, fall/medicine as Paper-1 core")
    pdf.bullet("Custom HD-EMG like EMaGer; Tobii eye tracker; cloud LLM as sole brain")

    # ---- 5 HARDWARE ----
    pdf.section("5. Hardware stack")
    pdf.code(
        """[MyoWare on arm] --analog--> [ESP32 #1 battery] --Wi-Fi EMG--> [Laptop AI]
Webcam (USB near user) -------------------------------------> [Laptop AI]
[Laptop AI: YOLO + Gaze + EMG + Act/Abstain + Dashboard]
        --Wi-Fi MQTT--> [ESP32 #2 + 8/16-ch relay hub] --> Lamp/Fan/Plug"""
    )
    pdf.table(
        ["Item", "Role", "Notes"],
        [
            ["MyoWare 2.0 + electrodes", "EMG volition", "Not USB-direct; needs ESP32 ADC"],
            ["ESP32 #1", "Wearable EMG node", "Battery/power bank"],
            ["ESP32 #2", "Relay hub", "5V adapter; Wi-Fi MQTT"],
            ["8/16-ch relay board", "Switch appliances", "One ESP32 controls many devices"],
            ["1080p USB webcam", "Face + zone appliances", "C920-class preferred; short USB"],
            ["Laptop", "Main NeuroShift app", "Camera, AI, MQTT, dashboard"],
            ["Lamp + fan (demo)", "Loads", "Via relay demo hub / smart plug"],
        ],
        [42, 40, 98],
    )
    pdf.body(
        "USB is for firmware/debug and short webcam cable. Final demo communication "
        "is Wi-Fi. Do not use one ESP32 per appliance."
    )

    # ---- 6 INDIAN HOME ----
    pdf.add_page()
    pdf.section("6. Indian wired-home integration")
    pdf.body(
        "Most Indian homes have normal switches, not smart bulbs. NeuroShift adds a "
        "relay/smart-switch layer on existing wiring."
    )
    pdf.sub("Option A (Phase 1 demo) - portable relay hub")
    pdf.bullet("Wall socket -> Demo Hub (ESP32 + relays) -> lamp/fan plugs")
    pdf.bullet("No wall switchboard opening required")
    pdf.bullet("Wireless decisions over MQTT; hard switching inside enclosed box")
    pdf.sub("Scaling to many appliances")
    pdf.bullet("1 ESP32 + 8/16-channel relay (cheap) OR modular MQTT smart switches")
    pdf.bullet("AI publishes topic per device; channels scale without redesigning AI")
    pdf.sub("Safety")
    pdf.bullet("Optocoupler relays, fuse, enclosure, manual override, electrician for mains")

    # ---- 7 COST ----
    pdf.section("7. Cost and feasibility")
    pdf.table(
        ["Budget style", "Approx total (INR)"],
        [
            ["Lean Phase 1", "7,000 - 9,000"],
            ["Recommended Phase 1", "10,000 - 15,000"],
            ["Comfortable + camera upgrade", "15,000 - 22,000"],
            ["Software stack", "0 (open source)"],
        ],
        [70, 110],
    )
    pdf.table(
        ["Goal", "Feasible?"],
        [
            ["Live Act/Abstain demo Sem 7", "Yes - High"],
            ["IEEE-style Sem 8 evaluation + draft", "Yes - Medium-High"],
            ["Clinical medical product", "No - out of scope now"],
        ],
        [90, 90],
    )

    # ---- 8 PWD ----
    pdf.section("8. PwD scenarios and limits")
    pdf.table(
        ["Condition", "How NeuroShift works", "Fit"],
        [
            ["Hand weakness / tremor", "Forearm EMG + gaze select", "Excellent"],
            ["Stroke hemiparesis", "EMG on stronger side + gaze", "Very good"],
            ["Arm amputation", "Residual stump EMG + gaze", "Excellent"],
            ["Partial upper paralysis", "Shoulder/upper EMG if available", "Good if signal exists"],
            ["Paraplegia (arms OK)", "Reach assistance for switches", "Good"],
            ["Severe quadriplegia", "Only if residual neck/shoulder EMG exists", "Conditional"],
            ["No voluntary EMG", "Needs gaze/voice/other modalities later", "Not Phase 1 claim"],
        ],
        [40, 90, 50],
    )
    pdf.quote(
        "Correct claim: for motor impairment with some voluntary EMG. "
        "Incorrect claim: works for all paralysis types automatically."
    )

    # ---- 9 CAMERA ----
    pdf.add_page()
    pdf.section("9. Camera FOV, count, and multi-zone")
    pdf.body(
        "A ~78 degree webcam cannot cover an entire 8-16 m room alone. Use zones."
    )
    pdf.sub("Buy recommendation")
    pdf.bullet("Phase 1: 1x 1080p autofocus USB webcam (Logitech C920/C922 class) near laptop")
    pdf.bullet("Phase 2: optional 2nd room/IP/phone camera for far appliances")
    pdf.bullet("Do not buy Tobii / ESP32-CAM for gaze core")
    pdf.sub("USB length")
    pdf.bullet("Keep face cam on short USB (1-2 m). Far views use Wi-Fi phone/IP cams.")
    pdf.sub("Multi-zone home")
    pdf.code(
        """Face cam (near user) -> gaze
Room cam A/B/C (Wi-Fi zones) -> appliances
Laptop merges detections; gaze selects; EMG confirms; Act/Abstain"""
    )

    # ---- 10 DEMO ----
    pdf.section("10. External demo scenes (must rehearse)")
    pdf.table(
        ["Scene", "What happens"],
        [
            ["A Clear Act", "Gaze on lamp + EMG effort -> lamp ON"],
            ["B Abstain look-only", "Gaze on fan, no EMG -> ABSTAIN"],
            ["C Abstain EMG-only", "Muscle noise, no stable gaze -> ABSTAIN"],
            ["D Ambiguity", "Two devices near gaze -> ABSTAIN"],
        ],
        [40, 140],
    )

    # ---- 11 OPEN QUESTIONS ----
    pdf.section("11. Ask guide to confirm")
    pdf.bullet("Ethics/consent for pilot subjects (team vs real PwD)")
    pdf.bullet("Exact Sem 7 deliverables (demo, report, PPT, lit survey length)")
    pdf.bullet("Team role split")
    pdf.bullet("Lab already has webcam/ESP32/relays?")
    pdf.bullet("Approve title and out-of-scope list")
    pdf.bullet("Electrical safety: electrician for mains relay box?")

    pdf.sub("Proposed title")
    pdf.quote(
        "NeuroShift: Gaze-Selected and EMG-Confirmed Smart-Home Intention Inference "
        "with Selective Actuation for Assistive Living"
    )

    pdf.section("12. Bottom line")
    pdf.bullet("Base paper = safer prosthesis gestures with EMG+vision.")
    pdf.bullet("NeuroShift = safer home control with gaze-select + EMG-confirm + Act/Abstain.")
    pdf.bullet("Primary metric = False Actuation Rate (FAR).")
    pdf.bullet("Sem 7 builds demo; Sem 8 proves and writes paper.")
    pdf.bullet("Low-cost MyoWare + 2xESP32 + webcam + relay hub is feasible (~Rs 10-15k).")

    pdf.quote(
        "Ready for guide discussion on concept. Remaining items are logistics: "
        "ethics, Sem 7 marking deliverables, shopping, and safety sign-off."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    print(f"PDF created: {build()}")
