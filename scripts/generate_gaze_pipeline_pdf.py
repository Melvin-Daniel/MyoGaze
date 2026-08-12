"""Generate official Gaze-Select + EMG-Confirm pipeline PDF."""

from pathlib import Path

from fpdf import FPDF

OUT = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "NeuroShift_Gaze_EMG_Pipeline.pdf"
)


class PipePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(90, 90, 90)
        self.cell(0, 8, "NeuroShift 2.0 | Official Pipeline (Gaze + EMG)", align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def title_block(self, title: str, subtitle: str):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(20, 20, 20)
        self.multi_cell(0, 8, title)
        self.ln(1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 5.2, subtitle)
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
        self.ln(0.6)

    def body(self, text: str):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, text)
        self.ln(0.5)

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
        self.multi_cell(
            self.w - self.l_margin - self.r_margin - 6, 5.2, text, fill=True
        )
        self.ln(2)

    def code_block(self, text: str):
        self.set_fill_color(248, 248, 248)
        self.set_font("Courier", "", 8)
        self.set_text_color(30, 30, 30)
        for line in text.strip().split("\n"):
            self.set_x(self.l_margin + 2)
            self.multi_cell(
                self.w - self.l_margin - self.r_margin - 4, 4.2, line, fill=True
            )
        self.ln(1.5)

    def table(self, headers, rows, col_widths):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(230, 235, 245)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 6.5, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 8)
        fill = False
        for row in rows:
            x0, y0 = self.get_x(), self.get_y()
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
    pdf = PipePDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.title_block(
        "Official Pipeline: Gaze Selects + EMG Confirms",
        "Updated NeuroShift real-time design for Phase 1 and Phase 2 | July 2026",
    )

    pdf.quote(
        "Looking selects. Muscle confirms. Unsure -> Abstain. "
        "Gaze alone must never turn a device on or off."
    )

    pdf.section("1. Why this design")
    pdf.bullet("Camera finds appliances AND which one the user is looking at.")
    pdf.bullet("EMG confirms whether they truly want to toggle it.")
    pdf.bullet("Prevents Midas-touch: looking without intent does nothing.")
    pdf.bullet("Better for motor-impaired users: eyes often work when hands do not.")
    pdf.bullet("Stronger novelty vs base paper (hand/object grip validation).")

    pdf.section("2. Real-time pipeline")
    pdf.code_block(
        """Webcam frame
  |- YOLO11/YOLOv8/RT-DETR -> appliance boxes (lamp, fan, plug)
  |- MediaPipe Face Mesh (P1) / Eye-gaze model (P2)
  |      -> gaze / head direction
  |- Match gaze to appliance (+ dwell 0.5-1.0 s) -> SELECTED TARGET
                |
         Target stable?
            |           |
           NO          YES
            v           v
         ABSTAIN    EMG volition high?
                      |           |
                     NO          YES
                      v           v
                   ABSTAIN     ACT -> MQTT -> ESP32 -> Relay -> Appliance"""
    )

    pdf.section("3. Two-factor safety table")
    pdf.table(
        ["Signal", "Role", "Alone enough to actuate?"],
        [
            ["Gaze / head direction", "SELECT appliance", "NO"],
            ["EMG effort", "CONFIRM intent", "NO (needs selected target)"],
            ["Gaze + EMG together", "Complete intention", "YES -> Act"],
            ["Either missing / unclear", "Unsafe", "ABSTAIN"],
        ],
        [48, 55, 77],
    )

    pdf.section("4. Phase 1 vs Phase 2 gaze")
    pdf.table(
        ["Phase", "Gaze method", "Why"],
        [
            ["Phase 1 (Sem 7)", "Head/face orientation (MediaPipe Face Mesh)", "Reliable demo, low compute"],
            ["Phase 2 (Sem 8)", "Eye-gaze estimation + dwell calibration", "Higher precision, stronger paper"],
            ["Both", "Dwell 0.5-1.0 s before EMG counts", "Blocks accidental glances"],
        ],
        [35, 80, 65],
    )

    pdf.add_page()
    pdf.section("5. Demo examples")
    pdf.sub_section("Clear Act")
    pdf.bullet("User looks at lamp for 0.8 s -> target = lamp")
    pdf.bullet("EMG spike -> ACT lamp ON via relay hub")
    pdf.sub_section("Abstain: look only")
    pdf.bullet("User glances at fan, no EMG -> ABSTAIN (looking != wanting)")
    pdf.sub_section("Abstain: EMG without gaze")
    pdf.bullet("Muscle tense while talking, no device gaze -> ABSTAIN")
    pdf.sub_section("Abstain: ambiguous")
    pdf.bullet("Lamp and fan both near gaze / low confidence -> ABSTAIN")

    pdf.section("6. Algorithms locked")
    pdf.table(
        ["Stage", "Phase 1", "Phase 2"],
        [
            ["Objects", "YOLO11s / YOLOv8s (or RT-DETR)", "Same + optional open-vocab assist"],
            ["Gaze", "MediaPipe Face Mesh / head pose", "Eye-gaze model (iris / L2CS-style)"],
            ["EMG", "RMS/MAV threshold or small TCN", "Calibrated volition score"],
            ["Policy", "gaze AND EMG -> Act else Abstain", "Learned fusion + FAR-tuned abstention"],
            ["IoT", "MQTT + ESP32 + relay demo hub", "Same + caregiver XAI dashboard"],
            ["Metric", "FAR + intention accuracy (pilot)", "FAR + F1 + ablations + paper"],
        ],
        [28, 76, 76],
    )

    pdf.section("7. Delta over base paper (EMBC 2024)")
    pdf.table(
        ["Point", "Chamberland et al.", "NeuroShift"],
        [
            ["Vision role", "Validate prosthesis grips", "Detect appliances + gaze-select target"],
            ["EMG role", "Classify gesture", "Confirm toggle intent only"],
            ["Selector", "Hand near object (MediaPipe Hands)", "Head/eye gaze (primary)"],
            ["Output", "Grip class", "Device Act or Abstain"],
            ["Safety", "Fewer false gestures", "Two-factor + FAR metric"],
        ],
        [28, 76, 76],
    )

    pdf.section("8. Viva one-liner")
    pdf.quote(
        "NeuroShift uses the camera to detect appliances and which one the user is "
        "looking at; the EMG sensor then confirms whether they truly want to toggle "
        "it. If either signal is unclear, the system abstains to reduce false actuations."
    )

    pdf.body("Full markdown: research/07_gaze_emg_pipeline.md")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    print(f"PDF created: {build_pdf()}")
