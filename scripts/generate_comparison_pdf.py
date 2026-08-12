"""Generate NeuroShift base-paper comparison PDF."""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent.parent / "docs" / "NeuroShift_Base_Paper_Comparison.pdf"


class ComparisonPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(90, 90, 90)
        self.cell(0, 8, "NeuroShift 2.0 | Base Paper Comparison", align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def title_block(self, title: str, subtitle: str):
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(20, 20, 20)
        self.multi_cell(0, 10, title)
        self.ln(2)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 6, subtitle)
        self.ln(4)

    def section(self, text: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 8, text)
        self.ln(2)

    def sub_section(self, text: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def body(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, f"  -  {text}")
        self.ln(0.5)

    def quote(self, text: str):
        self.set_fill_color(245, 247, 250)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(50, 50, 50)
        x = self.l_margin + 4
        self.set_x(x)
        self.multi_cell(self.w - self.l_margin - self.r_margin - 8, 6, text, fill=True)
        self.ln(3)

    def code_block(self, text: str):
        self.set_fill_color(248, 248, 248)
        self.set_font("Courier", "", 9)
        self.set_text_color(30, 30, 30)
        for line in text.strip().split("\n"):
            self.set_x(self.l_margin + 3)
            self.multi_cell(self.w - self.l_margin - self.r_margin - 6, 5, line, fill=True)
        self.ln(2)

    def table(self, headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None):
        if col_widths is None:
            usable = self.w - self.l_margin - self.r_margin
            col_widths = [int(usable / len(headers))] * len(headers)

        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(230, 235, 245)
        self.set_text_color(20, 20, 20)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, h, border=1, fill=True)
        self.ln()

        self.set_font("Helvetica", "", 9)
        fill = False
        for row in rows:
            x0 = self.get_x()
            y0 = self.get_y()
            heights = []
            lines_per_cell = []
            for i, cell in enumerate(row):
                self.set_xy(x0 + sum(col_widths[:i]), y0)
                lines = self.multi_cell(col_widths[i], 5, cell, border=0, dry_run=True, output="LINES")
                lines_per_cell.append(lines)
                heights.append(len(lines) * 5)
            row_h = max(heights + [8])
            if y0 + row_h > self.h - self.b_margin:
                self.add_page()
                y0 = self.get_y()
            for i, cell in enumerate(row):
                x = x0 + sum(col_widths[:i])
                self.set_xy(x, y0)
                if fill:
                    self.set_fill_color(245, 247, 252)
                else:
                    self.set_fill_color(255, 255, 255)
                self.rect(x, y0, col_widths[i], row_h, style="DF")
                self.set_xy(x + 1, y0 + 1)
                self.multi_cell(col_widths[i] - 2, 5, cell)
            self.set_xy(x0, y0 + row_h)
            fill = not fill
        self.ln(3)


def build_pdf() -> Path:
    pdf = ComparisonPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.title_block(
        "NeuroShift vs Base Paper",
        "Easy comparison draft for guide discussion | July 2026",
    )

    pdf.quote(
        "The base paper improves how reliably we recognize a gesture. "
        "NeuroShift uses gaze to select an appliance and EMG to confirm the toggle, "
        "or abstains when unsure."
    )

    pdf.section("1. One-line summary")
    pdf.table(
        ["", "Base paper", "NeuroShift (our work)"],
        [
            ["Idea", "Use camera to make EMG gestures more reliable", "Gaze selects appliance; EMG confirms toggle; Act/Abstain"],
        ],
        [28, 78, 78],
    )
    pdf.body("Base paper: Better gesture recognition.")
    pdf.body("Our paper: Safer smart-home intention understanding.")

    pdf.section("2. Base paper")
    pdf.body("Title: Visual Scene Understanding for Enhanced EMG Gesture Recognition")
    pdf.body("Authors: Chamberland, Labbe, Tam, Scheme, Gosselin")
    pdf.body("Venue: IEEE EMBC 2024")
    pdf.body("DOI: 10.1109/EMBC53108.2024.10782354")

    pdf.sub_section("What they do")
    pdf.code_block(
        """EMG signal  ->  Gesture classifier  ->  Gesture class
                     ^
Camera      ->  Object detection   ->  Accept / Reject gesture"""
    )
    pdf.bullet("User wears EMG sensors.")
    pdf.bullet("System classifies hand gestures.")
    pdf.bullet("Camera detects objects in the scene.")
    pdf.bullet("Vision checks if the gesture makes sense (reduce false movements).")
    pdf.bullet("Target: myoelectric prosthesis control.")

    pdf.sub_section("What they solve")
    pdf.bullet("False / unstable gesture predictions during onset and holding.")
    pdf.bullet("More robust EMG control using scene context.")

    pdf.sub_section("What they do NOT solve")
    pdf.bullet("Smart-home appliance control")
    pdf.bullet("User intention beyond predefined gestures")
    pdf.bullet("Act vs Abstain for safety in multi-object rooms")
    pdf.bullet("Personal habit / routine learning")
    pdf.bullet("Caregiver explanation of why a device fired")

    pdf.add_page()
    pdf.section("3. Our idea - NeuroShift")
    pdf.body(
        "Working title: NeuroShift: Affordance-Conditioned Multimodal Intention "
        "Inference with Selective Actuation for Assistive Smart Homes"
    )
    pdf.sub_section("What we do")
    pdf.code_block(
        """Camera  ->  YOLO appliances     ->  Devices in scene
Camera  ->  Gaze / head direction ->  Which device is selected
EMG     ->  Volition score        ->  Confirm real intent?
Context ->  Time / habit (Sem 8)  ->  Reweight if needed
                    |
           Intention Policy
                    |
         Act / Abstain / Clarify
                    |
         ESP32 + MQTT -> Lamp / Fan / Plug"""
    )
    pdf.bullet("Camera finds appliances AND which one the user is looking at.")
    pdf.bullet("EMG confirms the user truly wants to toggle it.")
    pdf.bullet("Looking alone never actuates (Midas-touch protection).")
    pdf.bullet("Target: assistive smart home for motor-impaired users.")

    pdf.section("4. Side-by-side comparison")
    pdf.table(
        ["Point", "Base paper", "NeuroShift"],
        [
            ["Research question", "How to make EMG gestures more robust with vision?", "How to infer home-device intention and avoid wrong actuations?"],
            ["Domain", "Prosthesis / gesture control", "Assistive smart home / independent living"],
            ["Input", "EMG + camera", "EMG + camera + context (Sem 8)"],
            ["What AI predicts", "Gesture class", "Device action or abstain"],
            ["Role of vision", "Validate / rescue gesture", "Detect appliances + gaze-select target"],
            ["Role of EMG", "Classify gesture", "Confirm toggle intent only"],
            ["Selector", "Hand near object", "Head/eye gaze (primary)"],
            ["If scene is confusing", "Gesture correctness focus", "System can ABSTAIN (safer)"],
            ["Main metric", "Gesture accuracy / robustness", "False Actuation Rate + intention F1"],
            ["User burden", "Learn a gesture set", "Look + confirm with muscle effort"],
            ["Hardware", "Lab prosthesis setup", "MyoWare + webcam + ESP32 relay hub"],
        ],
        [34, 74, 74],
    )

    pdf.section("5. Simple analogy")
    pdf.table(
        ["Analogy", "Base paper", "NeuroShift"],
        [
            ["Like...", "Spell-checker for hand gestures", "Smart assistant for what you want to do at home"],
            ["Example", "User did a fist - is that valid near this object?", "Lamp + fan visible; EMG shows effort - turn lamp or wait?"],
            ["Failure mode", "Wrong gesture / false movement", "Wrong device turns on / unsafe actuation"],
        ],
        [28, 78, 78],
    )

    pdf.add_page()
    pdf.section("6. Our novelty")
    pdf.sub_section("We are NOT claiming")
    pdf.bullet("First paper to combine EMG + camera")
    pdf.bullet("Highest gesture accuracy on Ninapro")
    pdf.bullet("A new Transformer just for EMG")

    pdf.sub_section("We ARE claiming")
    pdf.bullet("From gestures to home intentions: appliance action, not gesture class.")
    pdf.bullet("Selective actuation (Act / Abstain): prefer no action over wrong action.")
    pdf.bullet("Sparse EMG as confirmation, not a gesture dictionary.")
    pdf.bullet("Personal context + explanations in Sem 8 for caregivers.")

    pdf.section("7. Extension statement")
    pdf.quote(
        "Chamberland et al. (EMBC 2024) demonstrated that visual scene understanding "
        "can enhance EMG-based gesture recognition by reducing false movements in "
        "prosthesis control. NeuroShift extends this multimodal paradigm from gesture "
        "validation to assistive smart-home intention inference. Instead of recognizing "
        "predefined gestures, our system combines ambient visual affordances with sparse "
        "EMG volition and personal temporal priors to decide which device to actuate or "
        "whether to abstain, targeting reduced false actuations for motor-impaired "
        "independent living."
    )

    pdf.section("8. Two-semester plan")
    pdf.table(
        ["Semester", "Phase", "Deliverables"],
        [
            ["Sem 7", "Phase 1 - Prototype", "EMG + vision + MQTT + logging + 3 baselines"],
            ["Sem 8", "Phase 2 - Research", "Fusion, Act/Abstain, prior, XAI, evaluation, IEEE paper"],
        ],
        [24, 38, 120],
    )

    pdf.section("9. Flowchart comparison")
    pdf.sub_section("Base paper")
    pdf.code_block(
        """EMG --> Gesture model --> Gesture
              ^
Camera --> Objects -----> Gate (accept/reject)"""
    )
    pdf.sub_section("NeuroShift")
    pdf.code_block(
        """Camera --> Objects + Pose --> Candidate devices
EMG    --> Volition score --> Confirm effort
Context--> Habit prior    --> Reweight options (Sem 8)
                 |
          Intention Policy
                 |
        Act / Abstain / Explain
                 |
         Smart home device"""
    )

    pdf.section("10. Closing line")
    pdf.quote(
        "The base paper improves how reliably we recognize a gesture. "
        "NeuroShift uses gaze to select an appliance and EMG to confirm the toggle, "
        "or abstains when unsure. That is our novelty."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build_pdf()
    print(f"PDF created: {path}")
