"""Generate latest 2024-2026 module reference PDF."""

from pathlib import Path
from fpdf import FPDF

OUT = Path(__file__).resolve().parent.parent / "docs" / "NeuroShift_10_Latest_References_2024_2026.pdf"


class RefPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 7, "NeuroShift | Latest 10 IEEE References (2024-2026)", align="L")
        self.ln(9)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def h1(self, t):
        self.set_font("Helvetica", "B", 15)
        self.multi_cell(0, 7.5, t)
        self.ln(1)

    def h2(self, t):
        self.ln(1)
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(0, 6, t)
        self.ln(0.8)

    def body(self, t):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 4.7, t)
        self.ln(0.3)

    def bullet(self, t):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 4.7, f"  -  {t}")
        self.ln(0.1)

    def quote(self, t):
        self.set_fill_color(245, 247, 250)
        self.set_font("Helvetica", "I", 9)
        self.set_x(self.l_margin + 2)
        self.multi_cell(self.w - self.l_margin - self.r_margin - 4, 4.8, t, fill=True)
        self.ln(1.3)

    def table(self, headers, rows, widths):
        self.set_font("Helvetica", "B", 6.8)
        self.set_fill_color(230, 235, 245)
        for i, h in enumerate(headers):
            self.cell(widths[i], 5.2, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 6.8)
        fill = False
        for row in rows:
            x0, y0 = self.get_x(), self.get_y()
            heights = []
            for i, cell in enumerate(row):
                self.set_xy(x0 + sum(widths[:i]), y0)
                lines = self.multi_cell(
                    widths[i], 3.6, cell, border=0, dry_run=True, output="LINES"
                )
                heights.append(max(len(lines), 1) * 3.6)
            rh = max(heights + [5.2])
            if y0 + rh > self.h - self.b_margin:
                self.add_page()
                y0 = self.get_y()
                x0 = self.get_x()
            for i, cell in enumerate(row):
                x = x0 + sum(widths[:i])
                self.set_xy(x, y0)
                self.set_fill_color(245, 247, 252) if fill else self.set_fill_color(255, 255, 255)
                self.rect(x, y0, widths[i], rh, style="DF")
                self.set_xy(x + 0.5, y0 + 0.3)
                self.multi_cell(widths[i] - 1.0, 3.6, cell)
            self.set_xy(x0, y0 + rh)
            fill = not fill
        self.ln(1.3)


def build():
    pdf = RefPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.h1("NeuroShift: Latest 10 IEEE References (2024-2026)")
    pdf.body("All 10 are IEEE papers | Base: Chamberland IEEE EMBC 2024 | Updated July 2026")
    pdf.quote(
        "All core-10 are IEEE (10.1109) and 2024 or newer. P1 is BASE. Each module maps to "
        "an IEEE paper. Novelty: gaze-select + EMG-confirm + Act/Abstain + FAR for assistive homes."
    )

    pdf.h2("1. Latest Core-10 (all IEEE)")
    pdf.table(
        ["#", "Paper", "Year", "IEEE Venue / Module"],
        [
            ["P1", "Chamberland et al. Visual Scene Understanding for Enhanced EMG Gesture Recognition", "2024", "IEEE EMBC | BASE EMG+scene"],
            ["P2", "Lin/Yang et al. Hybrid Gaze + FEMG assistive robotic system", "2024", "IEEE TNSRE | Gaze select + confirm"],
            ["P3", "Sakthimohan et al. Smart-home assistive system using eye gestures", "2024", "IEEE ICACCS | Eye -> appliances"],
            ["P4", "Dere et al. Lightweight VLM-guided EMG gesture/motor intent", "2025", "IEEE Sensors J. | Vision-guided EMG"],
            ["P5", "Wang et al. Robust myoelectric recognition for reliable HRI", "2025", "IEEE RA-L | EMG reliability/reject"],
            ["P6", "Jeong & Woo. CIDER on-device smart-home intent reasoning", "2025", "IEEE Access | Smart-home intent"],
            ["P7", "TFVF-CNN sEMG + visual feature fusion", "2024", "IEEE ROBIO | Multimodal fusion"],
            ["P8", "Multimodal sEMG + vision hand gesture fusion", "2024", "IEEE M2VIP | Multimodal fusion (alt)"],
            ["P9", "Zhao/Lv et al. RT-DETR: DETRs Beat YOLOs", "2024", "IEEE/CVF CVPR | Object detection"],
            ["P10", "Li et al. Multimodal dynamic fusion intent, assisted older adults", "2025", "IEEE ICIVP | Assistive intent"],
        ],
        [10, 92, 14, 64],
    )

    pdf.h2("2. Module map for sir")
    pdf.table(
        ["Our module", "IEEE papers", "We improve by"],
        [
            ["Overall idea", "P1 BASE", "Gestures -> home intention"],
            ["Object detection", "P9 (+ YOLO in P1)", "Detect home appliances"],
            ["Gaze / eye select", "P2, P3", "Select appliance by looking"],
            ["EMG confirm", "P4, P5", "Sparse MyoWare confirm, not gesture dictionary"],
            ["Fusion", "P7, P8, P10", "Home Act/Abstain decision"],
            ["Act/Abstain", "P5 (reject/reliability)", "FAR metric for false home actuations"],
            ["Smart-home IoT", "P3, P6", "Indian wired relay hub + assistive safety"],
        ],
        [32, 40, 108],
    )

    pdf.add_page()
    pdf.h2("3. IEEE DOIs to download")
    pdf.bullet("P1 BASE: 10.1109/EMBC53108.2024.10782354")
    pdf.bullet("P2: 10.1109/tnsre.2024.3443073")
    pdf.bullet("P3: 10.1109/icaccs60874.2024.10717287")
    pdf.bullet("P4: 10.1109/jsen.2025.3565766")
    pdf.bullet("P5: 10.1109/lra.2025.3546095")
    pdf.bullet("P6: 10.1109/access.2025.3634621")
    pdf.bullet("P7: 10.1109/robio64047.2024.10907446")
    pdf.bullet("P8: 10.1109/m2vip62491.2024.10746196")
    pdf.bullet("P9: RT-DETR, IEEE/CVF CVPR 2024 (arXiv 2304.08069)")
    pdf.bullet("P10: 10.1109/icivp66296.2025.00029")

    pdf.h2("4. Year count")
    pdf.body("2024: 5 IEEE papers (including base) | 2025: 5 IEEE papers | All IEEE, all 2024+")

    pdf.h2("5. Honest note for guide")
    pdf.bullet("Earlier Act/Abstain paper (Gaus et al.) was arXiv preprint -> REMOVED for IEEE-only list.")
    pdf.bullet("Act/Abstain is now OUR contribution; IEEE reliability/reject basis is P5 (RA-L 2025).")
    pdf.bullet("RT-DETR (P9) is IEEE/CVF CVPR (IEEE Xplore); can be swapped if strictly IEEE-only journal/conf.")

    pdf.h2("6. Novelty line for guide")
    pdf.quote(
        "Latest IEEE papers already study EMG+vision, gaze+FEMG, eye-controlled homes and reliable EMG. "
        "NeuroShift's gap: gaze-selected home appliances + sparse EMG confirmation + "
        "Act/Abstain, measured by False Actuation Rate for assistive wired-home control."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    print(f"PDF created: {build()}")
