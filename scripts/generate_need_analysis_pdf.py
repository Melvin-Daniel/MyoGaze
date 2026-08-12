"""Generate NeuroShift need-analysis + base-paper PDF."""

from pathlib import Path

from fpdf import FPDF

OUT = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "NeuroShift_Need_Analysis_and_Base_Paper.pdf"
)


class NeedPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(90, 90, 90)
        self.cell(0, 8, "NeuroShift 2.0 | Need Analysis + Base Paper Review", align="L")
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
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def sub_section(self, text: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6.5, text)
        self.ln(1)

    def body(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.2, text)
        self.ln(0.8)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.2, f"  -  {text}")
        self.ln(0.3)

    def quote(self, text: str):
        self.set_fill_color(245, 247, 250)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(45, 45, 45)
        self.set_x(self.l_margin + 3)
        self.multi_cell(self.w - self.l_margin - self.r_margin - 6, 5.5, text, fill=True)
        self.ln(2)

    def table(self, headers: list[str], rows: list[list[str]], col_widths: list[int]):
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(230, 235, 245)
        self.set_text_color(20, 20, 20)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True)
        self.ln()

        self.set_font("Helvetica", "", 8.5)
        fill = False
        for row in rows:
            x0 = self.get_x()
            y0 = self.get_y()
            heights = []
            for i, cell in enumerate(row):
                self.set_xy(x0 + sum(col_widths[:i]), y0)
                lines = self.multi_cell(
                    col_widths[i], 4.5, cell, border=0, dry_run=True, output="LINES"
                )
                heights.append(len(lines) * 4.5)
            row_h = max(heights + [7])
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
                self.set_xy(x + 1, y0 + 0.8)
                self.multi_cell(col_widths[i] - 2, 4.5, cell)
            self.set_xy(x0, y0 + row_h)
            fill = not fill
        self.ln(2)


def build_pdf() -> Path:
    pdf = NeedPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.title_block(
        "Why NeuroShift Matters",
        "Need analysis with real population data + full analysis of base paper "
        "(Chamberland et al., IEEE EMBC 2024) | July 2026",
    )

    pdf.quote(
        "About 100 million people live with stroke effects worldwide. India has "
        "millions with locomotor disability and rising stroke prevalence. The base "
        "paper uses EMG + vision to fix wrong gestures for prostheses. NeuroShift "
        "uses EMG + vision to decide which home device to control - or abstain - "
        "for safer independent living."
    )

    pdf.section("Part A - Population Need (Real Data)")
    pdf.sub_section("A1. Problem")
    pdf.body(
        "Many people cannot easily use switches, remotes, or touchscreens due to "
        "stroke-related weakness/paralysis, spinal cord injury, limb amputation, "
        "age-related decline, or neuromuscular conditions. NeuroShift helps them "
        "control home devices using remaining muscle signals (EMG) + camera context, "
        "with safe abstention when unsure."
    )

    pdf.sub_section("A2. Global numbers")
    pdf.table(
        ["Metric", "Number", "Source"],
        [
            ["People living with stroke effects", "~93.8M (2021); ~104.8M (2023 est.)", "WHO / GBD / WSO"],
            ["New strokes per year", "~11.9 to 13.2 million", "WHO / GBD"],
            ["Stroke deaths per year", "~6.8 to 7.3 million", "WHO / GBD"],
            ["Lifetime stroke risk", "1 in 4 adults over age 25", "WSO / WHO"],
            ["Global stroke economic cost", ">US$890B / year (~0.66% GDP)", "WSO / Lancet Neurology"],
            ["People with spinal cord injury", "~20.6 million (2019)", "GBD / Lancet Neurology"],
            ["Traumatic limb amputation survivors", "~57.7 million (2017)", "GBD-based study"],
        ],
        [58, 62, 60],
    )
    pdf.bullet("Stroke is a leading cause of long-term motor disability.")
    pdf.bullet("WHO: survivors often have persistent motor deficits and loss of independence.")
    pdf.bullet("Indian rehab survey analysis: nearly 90% of stroke survivors report movement impairment.")
    pdf.bullet("Literature often cites 15-30% permanently disabled after stroke.")

    pdf.sub_section("A3. India-specific numbers")
    pdf.table(
        ["Metric", "Number", "Source"],
        [
            ["Persons with disability", "26.8 million", "Census of India 2011"],
            ["Movement / locomotor disability share", "~20.3% of PwD (largest category)", "Census 2011"],
            ["Disability prevalence", "~2.2% of population", "NSS 76th Round (2018)"],
            ["India new stroke cases (2021)", "~1.25 million (~10% of global)", "GBD / Lancet reporting"],
            ["India stroke prevalence", "~4.4M (1990) to ~9.4M (2021) (+47%)", "GBD / Lancet reporting"],
            ["India stroke incidence range", "~108-172 per 100,000 / year", "Jones et al., Int J Stroke 2022"],
        ],
        [58, 72, 50],
    )
    pdf.bullet("Most global stroke burden is in low- and middle-income countries.")
    pdf.bullet("Care is often family-based; caregiver anxiety/depression reported in 17-50% in Indian reviews.")
    pdf.bullet("Low-cost stack (MyoWare + webcam + ESP32) fits Indian college/startup constraints.")

    pdf.add_page()
    pdf.sub_section("A4. Who NeuroShift helps")
    pdf.table(
        ["Group", "Problem with normal controls", "How NeuroShift helps"],
        [
            ["Stroke survivors", "Hard to use remotes/switches", "EMG effort + scene context"],
            ["Partial paralysis / hemiparesis", "One-sided motor loss", "Remaining muscle as confirmation"],
            ["Spinal cord injury (incomplete)", "Limited voluntary movement", "Low-effort volition + affordances"],
            ["Upper-limb amputees", "Related to base paper domain", "Extend grips idea to home devices"],
            ["Older adults / weak hand mobility", "Fatigue, tremor, complex gestures", "No big gesture dictionary"],
            ["Caregivers / families", "High ADL assistance burden", "Safer automation + decision logs"],
        ],
        [42, 68, 70],
    )

    pdf.sub_section("A5. Usefulness in all ways")
    pdf.table(
        ["Dimension", "Why useful"],
        [
            ["Social / humanitarian", "Supports independent living for motor-disabled populations"],
            ["Clinical / rehab", "Extends EMG+vision from prosthesis literature to home ADLs"],
            ["Research / IEEE", "Clear novelty: home intention + Act/Abstain + FAR metric"],
            ["Economic", "Stroke costs hundreds of billions; reducing caregiver load has value"],
            ["India relevance", "Rising stroke prevalence + large locomotor disability population"],
            ["Startup / portfolio", "Problem -> prototype -> paper -> MVP path"],
        ],
        [42, 138],
    )

    pdf.section("Part B - Base Paper Analysis")
    pdf.body(
        "Title: Visual Scene Understanding for Enhanced EMG Gesture Recognition"
    )
    pdf.body(
        "Authors: Chamberland, Labbe, Tam, Scheme, Gosselin | Venue: IEEE EMBC 2024"
    )
    pdf.body("DOI: 10.1109/EMBC53108.2024.10782354")

    pdf.sub_section("B1. What they do (plain words)")
    pdf.bullet("HD-EMG predicts 6 hand gestures using SDCNN.")
    pdf.bullet("Head-mounted webcam + YOLOv8 detects everyday objects.")
    pdf.bullet("MediaPipe tracks the hand.")
    pdf.bullet("Object Likelihood Filtering (OLF) decides likely target object.")
    pdf.bullet("Vision limits allowed grips to those compatible with that object.")
    pdf.bullet("Result: fewer false gesture detections; user stays in control.")
    pdf.bullet("Domain: myoelectric PROSTHESIS control (not smart home).")

    pdf.sub_section("B2. Technical stack")
    pdf.table(
        ["Module", "Their choice"],
        [
            ["EMG sensor", "EMaGer 64-channel HD-EMG @ 1 kHz"],
            ["EMG model", "SDCNN (Siamese CNN) + centroid classifier"],
            ["Gestures", "open, tripod, power, thumbs-up, pinch, pointed index"],
            ["Camera", "EMEET C960 head-mounted, 640x480, ~10 fps"],
            ["Vision", "Custom YOLOv8-small, 28 object classes"],
            ["Hand tracking", "MediaPipe Hands"],
            ["Fusion", "OLF enables object-related grips for EMG selection"],
        ],
        [40, 140],
    )

    pdf.sub_section("B3. Results")
    pdf.body("SDCNN intra-session accuracy: 98.6%. YOLO mAP@[.5,.95]: 0.368.")
    pdf.body("Pilot: 1 able-bodied subject, 2 scenarios x 20 trials.")
    pdf.table(
        ["Scenario", "Transition errors fixed", "Static errors fixed"],
        [
            ["#1 mug -> apple", "100% (5.7 -> 0)", "68.2% (10.7 -> 3.4)"],
            ["#2 bottle -> phone", "60.7% (5.6 -> 2.2)", "93.0% (7.1 -> 0.5)"],
        ],
        [50, 65, 65],
    )
    pdf.body("Takeaway: vision context strongly reduces false EMG gesture predictions.")

    pdf.add_page()
    pdf.sub_section("B4. Strengths")
    pdf.bullet("Clear multimodal architecture (EMG + YOLO + hand tracking).")
    pdf.bullet("Preserves user agency (EMG primary; vision curates options).")
    pdf.bullet("Real-time proof with measurable error reduction.")
    pdf.bullet("Confidence-aware EMG model when gestures are ambiguous.")

    pdf.sub_section("B5. Limitations = NeuroShift starting point")
    pdf.table(
        ["Base paper limitation", "NeuroShift response"],
        [
            ["Predicts gestures, not home actions", "Predict appliance intention (lamp/fan/plug)"],
            ["Prosthesis grip selection domain", "Assistive smart-home independent living"],
            ["64-channel HD-EMG (expensive)", "Sparse MyoWare (low-cost, realistic)"],
            ["Vision filters allowed grips", "Vision proposes device affordances"],
            ["No Act/Abstain for IoT safety", "Selective abstention + False Actuation Rate"],
            ["Pilot = 1 able-bodied subject", "Multi-user NeuroShift-ADL pilot"],
            ["Hard with many nearby objects", "Multi-object ambiguity is our core test"],
            ["No habit prior / caregiver audit", "Sem 8 temporal prior + explanations"],
        ],
        [78, 102],
    )
    pdf.body(
        "Authors themselves note challenges: crowded scenes, occlusion, unknown "
        "objects, and better EMG/vision confidence fusion."
    )

    pdf.sub_section("B6. Extension statement (use in reports)")
    pdf.quote(
        "Chamberland et al. (EMBC 2024) showed that visual scene understanding can "
        "reduce false EMG gesture detections for prosthesis control by enabling only "
        "object-compatible grips. NeuroShift extends this multimodal paradigm from "
        "gesture validation for prostheses to home-device intention inference for "
        "assistive living. Using sparse EMG volition, ambient object/pose affordances, "
        "and personal priors with selective abstention, NeuroShift targets lower false "
        "smart-home actuations for people with motor disabilities."
    )

    pdf.section("Part C - 90-second explanation for guide")
    pdf.bullet(
        "Need: ~100M live with stroke effects globally; India ~9.4M stroke prevalence "
        "and millions with locomotor disability."
    )
    pdf.bullet("Base paper: EMG + camera reduces wrong GESTURES for prostheses.")
    pdf.bullet("Gap: that does not solve wrong HOME DEVICE actuations.")
    pdf.bullet(
        "Our solution: camera proposes feasible devices; EMG confirms effort; Act or Abstain."
    )
    pdf.bullet(
        "Why useful: social impact + research novelty + India-feasible hardware + IEEE path."
    )

    pdf.section("Bottom line")
    pdf.quote(
        "NeuroShift is useful because the population need is large and growing. "
        "The base paper proves EMG + vision works for safer gesture control. "
        "Our contribution turns that idea into safer home intention control for "
        "independent living."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build_pdf()
    print(f"PDF created: {path}")
