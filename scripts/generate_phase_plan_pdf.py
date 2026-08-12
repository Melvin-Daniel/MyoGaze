"""Generate Phase 1 / Phase 2 solution plan PDF."""

from pathlib import Path

from fpdf import FPDF

OUT = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "NeuroShift_Phase1_Phase2_Solution_Plan.pdf"
)


class PlanPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(90, 90, 90)
        self.cell(0, 8, "NeuroShift 2.0 | Phase 1 & Phase 2 Solution Plan", align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def title_block(self, title: str, subtitle: str):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(20, 20, 20)
        self.multi_cell(0, 9, title)
        self.ln(1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 5.5, subtitle)
        self.ln(3)

    def section(self, text: str):
        self.ln(2)
        self.set_font("Helvetica", "B", 12.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def sub_section(self, text: str):
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, text)
        self.ln(0.8)

    def body(self, text: str):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, text)
        self.ln(0.6)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, f"  -  {text}")
        self.ln(0.2)

    def quote(self, text: str):
        self.set_fill_color(245, 247, 250)
        self.set_font("Helvetica", "I", 9.5)
        self.set_text_color(45, 45, 45)
        self.set_x(self.l_margin + 3)
        self.multi_cell(self.w - self.l_margin - self.r_margin - 6, 5.2, text, fill=True)
        self.ln(2)

    def code_block(self, text: str):
        self.set_fill_color(248, 248, 248)
        self.set_font("Courier", "", 8)
        self.set_text_color(30, 30, 30)
        for line in text.strip().split("\n"):
            self.set_x(self.l_margin + 2)
            self.multi_cell(self.w - self.l_margin - self.r_margin - 4, 4.2, line, fill=True)
        self.ln(1.5)

    def table(self, headers: list[str], rows: list[list[str]], col_widths: list[int]):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(230, 235, 245)
        self.set_text_color(20, 20, 20)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 6.5, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 8)
        fill = False
        for row in rows:
            x0 = self.get_x()
            y0 = self.get_y()
            heights = []
            for i, cell in enumerate(row):
                self.set_xy(x0 + sum(col_widths[:i]), y0)
                lines = self.multi_cell(
                    col_widths[i], 4.2, cell, border=0, dry_run=True, output="LINES"
                )
                heights.append(len(lines) * 4.2)
            row_h = max(heights + [6.5])
            if y0 + row_h > self.h - self.b_margin:
                self.add_page()
                y0 = self.get_y()
                x0 = self.get_x()
            for i, cell in enumerate(row):
                x = x0 + sum(col_widths[:i])
                self.set_xy(x, y0)
                self.set_fill_color(245, 247, 252) if fill else self.set_fill_color(255, 255, 255)
                self.rect(x, y0, col_widths[i], row_h, style="DF")
                self.set_xy(x + 1, y0 + 0.6)
                self.multi_cell(col_widths[i] - 2, 4.2, cell)
            self.set_xy(x0, y0 + row_h)
            fill = not fill
        self.ln(2)


def build_pdf() -> Path:
    pdf = PlanPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.title_block(
        "Phase 1 & Phase 2 Solution Plan",
        "What we build, requirements, algorithms, and how to demo to external examiners",
    )

    pdf.quote(
        "NeuroShift uses camera context and sparse EMG to decide which home device "
        "a motor-impaired user intends to control - and abstains when unsure - to "
        "reduce false actuations."
    )

    pdf.section("1. Our solution")
    pdf.body(
        "Camera finds feasible devices. EMG confirms user effort. Intention policy "
        "chooses ACT or ABSTAIN. ESP32+MQTT controls lamp/fan/plug. Dashboard logs why."
    )
    pdf.code_block(
        """Camera -> Objects + Pose -> Candidate devices (affordances)
EMG    -> Volition score     -> Is user trying to act?
Context-> Habit prior (P2)   -> Reweight options
              |
       Intention Policy -> Act / Abstain
              |
       MQTT + ESP32 -> Lamp / Fan / Plug"""
    )

    pdf.section("2. Phase split")
    pdf.table(
        ["", "Phase 1 (Sem 7 NOW)", "Phase 2 (Sem 8 NEXT)"],
        [
            ["Goal", "Working prototype + pilot data", "Research proof + IEEE paper"],
            ["Fusion", "Rule-based Act/Abstain", "Learned fusion + calibrated abstention"],
            ["Context", "Device state + basic time", "Personal habit prior"],
            ["XAI", "Decision log", "Caregiver explanations + dashboard"],
            ["Demo", "Live hardware demo", "Live demo + graphs + paper"],
            ["Deliverable", "Prototype + report + dataset start", "Evaluation + paper + MVP polish"],
        ],
        [28, 76, 76],
    )

    pdf.section("3. Phase 1 - What we build")
    pdf.bullet("EMG acquisition (MyoWare -> ESP32/Python)")
    pdf.bullet("Volition encoder: P(user trying to act)")
    pdf.bullet("Vision: YOLO/RT-DETR + MediaPipe/RTMPose")
    pdf.bullet("Affordance map: objects -> candidate device actions")
    pdf.bullet("Basic intention policy: Act or Abstain")
    pdf.bullet("MQTT -> ESP32 relay / smart plug")
    pdf.bullet("Logger + simple React dashboard")

    pdf.sub_section("Phase 1 algorithms")
    pdf.table(
        ["Stage", "Algorithm", "Why"],
        [
            ["EMG preprocess", "RMS / MAV features", "Standard for sparse EMG"],
            ["Volition", "Threshold or small 1D-CNN/TCN", "Effort detection, not gesture race"],
            ["Objects", "YOLOv8 or RT-DETR", "Real-time; same family as base paper"],
            ["Pose/hand", "MediaPipe or RTMPose", "Fast on laptop webcam"],
            ["Affordance", "Rule table object->action", "Explainable in viva"],
            ["Fusion", "Late fusion rules + thresholds", "Extends Chamberland gating"],
            ["IoT", "MQTT + ESP32 relay", "Reliable live demo"],
        ],
        [32, 58, 90],
    )

    pdf.sub_section("Phase 1 fusion logic")
    pdf.code_block(
        """IF EMG_volition < T_low: ABSTAIN
ELSE IF one feasible device AND score > T_act: ACT
ELSE IF multiple feasible devices: ABSTAIN (or top if dominant)
ELSE: ABSTAIN"""
    )

    pdf.add_page()
    pdf.section("4. Phase 1 requirements")
    pdf.sub_section("Hardware (must have)")
    pdf.bullet("MyoWare EMG + electrodes")
    pdf.bullet("ESP32 DevKit")
    pdf.bullet("Relay module (2-3 channels) or MQTT smart plug")
    pdf.bullet("USB webcam + laptop")
    pdf.bullet("Lamp + fan (demo devices)")
    pdf.bullet("Mosquitto MQTT broker, wires, power supply")
    pdf.sub_section("Software")
    pdf.bullet("Python, PyTorch, OpenCV, YOLO/RT-DETR, MediaPipe")
    pdf.bullet("FastAPI + React + SQLite/PostgreSQL")
    pdf.bullet("ESP32 firmware + paho-mqtt")

    pdf.section("5. Phase 2 - What we add")
    pdf.table(
        ["Module", "Algorithm / approach"],
        [
            ["Learned fusion", "MLP / small cross-attention over EMG+vision+context"],
            ["Calibrated abstention", "Reject option / selective prediction tuned for FAR"],
            ["Personal prior", "Time-of-day + recent device-use counts/sequence model"],
            ["Decision XAI", "Structured reason: objects, EMG, prior, decision"],
            ["Caregiver dashboard", "React history + alerts + explanations"],
            ["Evaluation", "FAR, F1, ablations vs 4 baselines"],
            ["Paper", "IEEE EMBC-style draft"],
        ],
        [45, 135],
    )

    pdf.section("6. How to DEMO to external (8-10 min)")
    pdf.table(
        ["Time", "Show", "Say"],
        [
            ["0-1 min", "Need slide with population data", "~100M stroke survivors; India ~9.4M"],
            ["1-2 min", "Base paper vs NeuroShift", "Gestures -> home intention + abstain"],
            ["2-3 min", "Architecture", "Sensors -> policy -> MQTT -> devices"],
            ["3-6.5 min", "LIVE DEMO (3 scenes)", "See scenes below"],
            ["6.5-8 min", "Results table", "FAR vs baselines"],
            ["8-9 min", "Sem7 done / Sem8 next", "Clear roadmap"],
            ["9-10 min", "Q&A", "Novelty, ethics, limits"],
        ],
        [24, 58, 98],
    )

    pdf.sub_section("Live demo scenes (must rehearse)")
    pdf.bullet("Scene A CLEAR: hand/lamp focus + EMG effort -> lamp ON (success)")
    pdf.bullet("Scene B AMBIGUOUS: lamp+fan visible, weak signal -> ABSTAIN (safety)")
    pdf.bullet("Scene C CONTRAST: always-act/EMG-only fails; NeuroShift abstains")
    pdf.bullet("Scene D (optional): normal hand movement without intent -> ABSTAIN")

    pdf.sub_section("Demo survival tips")
    pdf.bullet("Pre-wire and tape relays night before")
    pdf.bullet("Keep backup video if live fails")
    pdf.bullet("Fix camera position; high-contrast objects")
    pdf.bullet("Project dashboard decision panel")
    pdf.bullet("Never skip the abstain scene - that is your novelty")

    pdf.add_page()
    pdf.section("7. External examiner Q&A cheat sheet")
    pdf.table(
        ["They ask", "You answer"],
        [
            ["Novelty?", "Home intention + Act/Abstain, not gesture accuracy"],
            ["Base paper?", "Chamberland EMBC 2024; extend gesture rescue to home intention"],
            ["Why useful?", "Stroke/paralysis population + independent living"],
            ["Algorithms?", "YOLO/MediaPipe + EMG volition + fusion policy + MQTT"],
            ["Evaluation?", "FAR + intention F1 vs EMG-only / vision-only / Chamberland-gate"],
            ["If it fails?", "Occlusion/noise -> abstain by design"],
            ["Ethics?", "Consent for data; not a clinical medical device claim in Phase 1"],
        ],
        [35, 145],
    )

    pdf.section("8. Phase 1 week plan")
    pdf.table(
        ["Weeks", "Focus"],
        [
            ["1-2", "MyoWare + ESP32 stream + relay blink"],
            ["3-4", "YOLO + MediaPipe + affordance map"],
            ["5-6", "Fusion rules + MQTT end-to-end control"],
            ["7-8", "Dashboard + logger + pilot data collection"],
            ["9-10", "Baselines + FAR table + polish demo"],
            ["11-12", "Report, PPT, external rehearsal"],
        ],
        [28, 152],
    )

    pdf.section("9. Do NOT do")
    pdf.bullet("Chase Ninapro SOTA / Transformer as novelty")
    pdf.bullet("Add fall/medicine/wheelchair into Phase 1 claims")
    pdf.bullet("Depend on cloud LLM for core decision")
    pdf.bullet("Demo without an abstain scene")

    pdf.section("10. Ownership sentences")
    pdf.quote(
        "Phase 1: We built a working EMG + vision + IoT intention prototype with "
        "Act/Abstain and pilot data."
    )
    pdf.quote(
        "Phase 2: We proved affordance-conditioned fusion + abstention + personal "
        "prior reduces false actuations vs baselines, and wrote the IEEE paper."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    print(f"PDF created: {build_pdf()}")
