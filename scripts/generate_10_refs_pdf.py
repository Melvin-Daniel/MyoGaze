"""Generate 10 module-wise reference papers PDF for guide."""

from pathlib import Path
from fpdf import FPDF

OUT = Path(__file__).resolve().parent.parent / "docs" / "NeuroShift_10_Module_References.pdf"


class RefPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 7, "NeuroShift | 10 Module-wise Reference Papers", align="L")
        self.ln(9)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def h1(self, t):
        self.set_font("Helvetica", "B", 16)
        self.multi_cell(0, 8, t)
        self.ln(2)

    def h2(self, t):
        self.ln(1)
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(0, 6, t)
        self.ln(1)

    def body(self, t):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 4.8, t)
        self.ln(0.4)

    def bullet(self, t):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 4.8, f"  -  {t}")
        self.ln(0.1)

    def quote(self, t):
        self.set_fill_color(245, 247, 250)
        self.set_font("Helvetica", "I", 9)
        self.set_x(self.l_margin + 2)
        self.multi_cell(self.w - self.l_margin - self.r_margin - 4, 5, t, fill=True)
        self.ln(1.5)

    def table(self, headers, rows, widths):
        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(230, 235, 245)
        for i, h in enumerate(headers):
            self.cell(widths[i], 5.5, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 7)
        fill = False
        for row in rows:
            x0, y0 = self.get_x(), self.get_y()
            heights = []
            for i, cell in enumerate(row):
                self.set_xy(x0 + sum(widths[:i]), y0)
                lines = self.multi_cell(widths[i], 3.8, cell, border=0, dry_run=True, output="LINES")
                heights.append(max(len(lines), 1) * 3.8)
            rh = max(heights + [5.5])
            if y0 + rh > self.h - self.b_margin:
                self.add_page()
                y0 = self.get_y()
                x0 = self.get_x()
            for i, cell in enumerate(row):
                x = x0 + sum(widths[:i])
                self.set_xy(x, y0)
                self.set_fill_color(245, 247, 252) if fill else self.set_fill_color(255, 255, 255)
                self.rect(x, y0, widths[i], rh, style="DF")
                self.set_xy(x + 0.6, y0 + 0.4)
                self.multi_cell(widths[i] - 1.2, 3.8, cell)
            self.set_xy(x0, y0 + rh)
            fill = not fill
        self.ln(1.5)


def build():
    pdf = RefPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.h1("NeuroShift: 10 Reference Papers (Module-wise)")
    pdf.body("For guide review | Base paper: Chamberland et al., IEEE EMBC 2024 | July 2026")
    pdf.quote(
        "We selected 10 relevant papers. Chamberland EMBC 2024 is the BASE. "
        "Each NeuroShift module maps to one or more of these papers. "
        "Novelty = gaze selects + EMG confirms + Act/Abstain + FAR for smart-home assistance."
    )

    pdf.h2("1. Explain to guide (30 seconds)")
    pdf.bullet("Surveyed EMG, vision, gaze, fusion, smart-home assistive, and abstention literature.")
    pdf.bullet("Chose 10 key papers; P1 Chamberland is base (sir already approved direction).")
    pdf.bullet("Built modules from these papers; novelty is the combination for home FAR safety.")

    pdf.h2("2. The 10 papers")
    pdf.table(
        ["#", "Paper (short)", "Module", "Role for NeuroShift"],
        [
            ["P1", "Chamberland EMBC 2024: Visual Scene Understanding for Enhanced EMG Gesture Recognition", "BASE + EMG+vision", "Base paper; extend gestures -> home intention"],
            ["P2", "Frontiers 2024: Multimodal EMG+vision grasp INTENT inference", "Fusion / intention", "Supports intent (not only gesture class)"],
            ["P3", "IEEE TNSRE 2024: Hybrid Gaze + FEMG assistive control (SCI)", "Gaze select + EMG confirm", "Closest pattern: looking selects, muscle confirms"],
            ["P4", "IEEE ICCIT 2023: BlinkGrid gaze control of home appliances", "Gaze -> home devices", "Webcam gaze for appliances; we add EMG+FAR"],
            ["P5", "Hybrid smart home SSVEP+EMG (confirm / anti-idle errors)", "Confirm + safety", "EMG confirms selection; reduces false ops"],
            ["P6", "Scheme TBME 2013: Confidence-based rejection myoelectric control", "Act/Abstain", "Classic reject option when unsure"],
            ["P7", "arXiv 2025 Sagacity: EMG multimodal smart-home for older/impaired", "Smart-home EMG domain", "Assistive home IoT motivation"],
            ["P8", "MediaPipe Face Mesh (arXiv 1907.06724)", "Head/face landmarks", "Phase-1 head direction from webcam"],
            ["P9", "YOLO (as in P1) / RT-DETR CVPR 2024", "Object detection", "Detect lamp/fan/plug in real time"],
            ["P10", "Chamberland TBioCAS 2023 wearable HD-EMG (lineage)", "Wearable EMG sensing", "Wearable EMG valid; we use sparse MyoWare"],
        ],
        [12, 78, 38, 52],
    )

    pdf.add_page()
    pdf.h2("3. Module-wise mapping (what sir asked)")
    pdf.table(
        ["Our module", "Does what", "Main papers", "We improve by"],
        [
            ["Appliance detection", "Find devices in camera", "P1, P9", "Home appliances, not only grasp objects"],
            ["Gaze / head select", "Which device user looks at", "P3, P4, P8", "Select for home; Phase1 head, Phase2 eyes"],
            ["EMG confirm", "Confirm real toggle intent", "P3, P5, P10", "Sparse MyoWare confirm, not gesture dictionary"],
            ["Multimodal fusion", "Combine gaze target + EMG", "P1, P2, P3", "Output = Act/Abstain for home"],
            ["Act / Abstain", "No action if unsure", "P5, P6", "Home False Actuation Rate (FAR)"],
            ["Smart-home IoT", "ESP32 + relay control", "P7", "Indian wired-home relay retrofit"],
            ["Overall system", "Full pipeline", "P1 BASE", "Gaze-select + EMG-confirm home intention"],
        ],
        [32, 42, 28, 78],
    )

    pdf.h2("4. Flow from papers to our idea")
    pdf.body("P9/P1 detect appliances -> P8/P4 gaze selects -> P10/P3 EMG confirms -> P2/P1 fuse -> P5/P6 abstain if unsure -> P7 home assistive goal.")
    pdf.body("BASE = P1 Chamberland. Novelty = combination for safer home intention (FAR).")

    pdf.h2("5. Key DOIs / IDs")
    pdf.bullet("P1 BASE DOI: 10.1109/EMBC53108.2024.10782354")
    pdf.bullet("P2 DOI: 10.3389/frobt.2024.1312554")
    pdf.bullet("P3 DOI: 10.1109/tnsre.2024.3443073")
    pdf.bullet("P4 DOI: 10.1109/iccit60459.2023.10441588")
    pdf.bullet("P6 DOI: 10.1109/TBME.2013.2238939")
    pdf.bullet("P7 arXiv: 2507.19479")
    pdf.bullet("P8 arXiv: 1907.06724")
    pdf.bullet("P9 RT-DETR arXiv: 2304.08069 / CVPR 2024")
    pdf.bullet("P10 DOI: 10.1109/TBCAS.2023.3314053")

    pdf.h2("6. Novelty vs these 10")
    pdf.bullet("Not claiming first EMG+camera or first gaze home control.")
    pdf.bullet("Claiming: gaze-select + sparse EMG-confirm + Act/Abstain for home devices, measured by FAR.")
    pdf.bullet("Extends P1 from prosthesis gesture rescue to assistive smart-home intention.")

    pdf.quote(
        "Primary base paper: Chamberland et al., IEEE EMBC 2024. "
        "Supporting module references: P2-P10. Total core set for guide: 10 papers."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    print(f"PDF created: {build()}")
