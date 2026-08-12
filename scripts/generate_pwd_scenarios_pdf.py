"""Generate PwD real-time scenarios + phase workload PDF."""

from pathlib import Path

from fpdf import FPDF

OUT = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "NeuroShift_Realtime_PwD_Scenarios.pdf"
)


class ScenarioPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(90, 90, 90)
        self.cell(
            0,
            8,
            "NeuroShift 2.0 | Real-time PwD Scenarios + Phase Workload",
            align="L",
        )
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def title_block(self, title: str, subtitle: str):
        self.set_font("Helvetica", "B", 17)
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
                if fill:
                    self.set_fill_color(245, 247, 252)
                else:
                    self.set_fill_color(255, 255, 255)
                self.rect(x, y0, col_widths[i], row_h, style="DF")
                self.set_xy(x + 1, y0 + 0.6)
                self.multi_cell(col_widths[i] - 2, 4.2, cell)
            self.set_xy(x0, y0 + row_h)
            fill = not fill
        self.ln(2)


def build_pdf() -> Path:
    pdf = ScenarioPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.title_block(
        "Real-time PwD Scenarios + Phase 1 / Phase 2 Work",
        "How NeuroShift works for different motor disabilities, and what major work "
        "happens in each semester | July 2026",
    )

    pdf.quote(
        "NeuroShift helps people who still have some voluntary muscle signal. "
        "It is a home-control assistant (Act/Abstain), not a cure for paralysis "
        "and not full-body movement restoration."
    )

    pdf.section("1. Will there be major work in BOTH phases?")
    pdf.body("YES. Both semesters have major, different work. Neither is 'light'.")
    pdf.table(
        ["", "Phase 1 (Sem 7)", "Phase 2 (Sem 8)"],
        [
            ["Nature", "BUILD the system", "PROVE the research"],
            [
                "Major work",
                "Hardware + software pipeline + live demo",
                "Fusion/abstention science + evaluation + paper",
            ],
            [
                "Hard parts",
                "EMG noise, wiring, YOLO desk scene, MQTT reliability",
                "FAR tuning, priors, ablations, writing IEEE draft",
            ],
            [
                "Success looks like",
                "External sees lamp/fan Act and Abstain live",
                "Tables show lower FAR vs baselines + paper draft",
            ],
            [
                "Effort level",
                "High (engineering heavy)",
                "High (research + polish heavy)",
            ],
        ],
        [28, 76, 76],
    )

    pdf.sub_section("Phase 1 major work checklist")
    pdf.bullet("MyoWare + ESP32 streaming and calibration")
    pdf.bullet("Relay/smart-plug control for normal Indian wired appliances")
    pdf.bullet("YOLO/RT-DETR + MediaPipe affordance pipeline")
    pdf.bullet("Rule-based intention policy (Act/Abstain)")
    pdf.bullet("Dashboard + synchronized trial logger")
    pdf.bullet("Pilot dataset start + 3 baselines")
    pdf.bullet("Rehearsed live external demo")

    pdf.sub_section("Phase 2 major work checklist")
    pdf.bullet("Learned multimodal fusion (replace pure rules)")
    pdf.bullet("Calibrated abstention tuned for False Actuation Rate (FAR)")
    pdf.bullet("Personal temporal prior (time/habit)")
    pdf.bullet("Decision-level explanations + caregiver dashboard")
    pdf.bullet("Full evaluation + ablations on NeuroShift-ADL")
    pdf.bullet("IEEE paper draft + final report/viva")

    pdf.quote(
        "Phase 1 ownership: We built a working EMG+vision+IoT intention prototype "
        "with Act/Abstain.  |  Phase 2 ownership: We proved lower FAR with fusion + "
        "abstention + prior, and wrote the paper."
    )

    pdf.add_page()
    pdf.section("2. Common real-time loop (all users)")
    pdf.code_block(
        """1. Camera sees room + devices + body/hand pose (if visible)
2. System lists feasible actions (lamp / fan / plug)
3. EMG checks remaining voluntary muscle effort
4. Policy decides: ACT one device  OR  ABSTAIN
5. ESP32 / MQTT controls that appliance
6. Dashboard logs why"""
    )

    pdf.section("3. Real-time scenarios by PwD type")

    pdf.sub_section("3.1 Mild hand weakness / tremor / arthritis")
    pdf.body("EMG: forearm or biceps. Vision: medium importance.")
    pdf.bullet("User orients to lamp and slightly raises arm.")
    pdf.bullet("Camera marks lamp as feasible; EMG detects effort.")
    pdf.bullet("Decision: ACT -> lamp ON.")
    pdf.bullet("If lamp+fan both unclear: ABSTAIN.")
    pdf.body("Fit: Excellent (best Phase 1 target).")

    pdf.sub_section("3.2 Hemiparesis (one side weak after stroke)")
    pdf.body("EMG on stronger side residual muscle (forearm/biceps/shoulder).")
    pdf.bullet("User turns toward fan; tenses good-side muscle.")
    pdf.bullet("Camera supports fan candidate; EMG confirms volition.")
    pdf.bullet("Decision: ACT -> fan ON.")
    pdf.bullet("Accidental tensing without clear target -> ABSTAIN.")
    pdf.body("Fit: Very good.")

    pdf.sub_section("3.3 Upper-limb amputation")
    pdf.body("EMG on residual stump. Closest to base-paper users, but output is home devices.")
    pdf.bullet("User faces bedside lamp.")
    pdf.bullet("Camera: lamp candidate. User contracts residual muscles.")
    pdf.bullet("Decision: ACT -> lamp ON.")
    pdf.bullet("No need for gesture dictionary (gesture1/gesture2).")
    pdf.body("Fit: Excellent; strong extension of Chamberland EMBC 2024.")

    pdf.sub_section("3.4 Partial upper-body paralysis")
    pdf.body("EMG on best residual site (trapezius/deltoid/biceps). Vision does more work.")
    pdf.bullet("Camera views bed + lamp + fan.")
    pdf.bullet("User orients to lamp and gives small shoulder shrug.")
    pdf.bullet("If one device clearly favored: ACT. Else ABSTAIN/clarify.")
    pdf.body("Fit: Good, if a stable EMG site exists.")

    pdf.add_page()
    pdf.sub_section("3.5 Severe quadriplegia / shoulder-to-leg paralysis")
    pdf.body(
        "Honest limit: arm MyoWare may fail if no usable limb EMG. Works only if "
        "residual neck/shoulder/face EMG exists. Otherwise need future modalities "
        "(gaze/voice/sip-puff) - not Phase 1 claim."
    )
    pdf.bullet("If residual EMG exists and vision strongly favors one device: ACT.")
    pdf.bullet("Otherwise: ABSTAIN (critical for safety).")
    pdf.body("Fit: Conditional. State this clearly to guide/external.")

    pdf.sub_section("3.6 Paraplegia (legs paralyzed, arms OK)")
    pdf.body("Arms often usable; issue is reach/wheelchair access/fatigue.")
    pdf.bullet("User cannot reach wall switch from wheelchair.")
    pdf.bullet("Orients to fan + intentional forearm contraction.")
    pdf.bullet("Decision: ACT -> fan.")
    pdf.body("Fit: Good for independence on unreachable switches.")

    pdf.sub_section("3.7 Cerebral palsy / inconsistent motor control")
    pdf.body("Involuntary spikes can create false EMG - Act/Abstain is essential.")
    pdf.bullet("Involuntary jerk + no clear visual target -> ABSTAIN.")
    pdf.bullet("Later intentional orientation to lamp + clearer pattern -> ACT.")
    pdf.body("Fit: Medium-good with strict FAR tuning.")

    pdf.sub_section("3.8 Elderly with low vision + weak hands")
    pdf.bullet("User wants night lamp; cannot use remote buttons easily.")
    pdf.bullet("Camera finds bedside lamp; EMG confirms effort -> ACT.")
    pdf.bullet("Caregiver dashboard shows decision log.")
    pdf.body("Fit: Good.")

    pdf.section("4. Quick fit matrix")
    pdf.table(
        ["Condition", "EMG placement", "Vision role", "Works now?"],
        [
            ["Hand weakness / tremor", "Forearm", "Medium", "Yes"],
            ["Stroke hemiparesis", "Stronger limb", "High", "Yes"],
            ["Arm amputee", "Residual stump", "High", "Yes"],
            ["Partial upper paralysis", "Shoulder/upper arm", "Very high", "Yes if signal"],
            ["Paraplegia (arms OK)", "Forearm", "Medium", "Yes"],
            ["Severe quadriplegia", "Neck/face if available", "Very high", "Only if EMG exists"],
            ["No voluntary EMG at all", "-", "-", "No (need other modalities)"],
        ],
        [42, 40, 32, 66],
    )

    pdf.section("5. Day-in-life example (stroke, weak right arm)")
    pdf.bullet("Evening: lamp and fan both visible.")
    pdf.bullet("User turns to lamp and contracts left forearm.")
    pdf.bullet("Fusion: lamp high, fan low, EMG high -> ACT lamp.")
    pdf.bullet("Later: shifts in chair (EMG noise), no clear target -> ABSTAIN.")
    pdf.bullet("Dashboard: 'Abstain reason: ambiguity + low confidence'.")
    pdf.body("This is novelty in daily life: intention when clear, safety when unclear.")

    pdf.add_page()
    pdf.section("6. What to claim vs not claim")
    pdf.sub_section("Correct claim")
    pdf.quote(
        "NeuroShift is for people with motor impairment who retain some voluntary "
        "muscle activity, enabling safer smart-home control through scene "
        "understanding + EMG confirmation + abstention."
    )
    pdf.sub_section("Incorrect claim")
    pdf.quote(
        "It works for all paralysis types automatically / restores full movement."
    )

    pdf.section("7. Which users for which phase")
    pdf.table(
        ["Phase", "Practical users"],
        [
            ["Phase 1 demo", "Able-bodied pilot + simulated weakness; stump/forearm EMG"],
            ["Phase 2 study", "Consenting volunteers: hemiparesis / amputation / elderly weak grip"],
            ["Future work", "Gaze/voice fallback for severe quadriplegia without limb EMG"],
        ],
        [35, 145],
    )

    pdf.section("8. Bottom line")
    pdf.bullet("YES - major work in Phase 1 AND Phase 2 (different kinds of major).")
    pdf.bullet("Phase 1 = build reliable real-time demo for Indian wired homes.")
    pdf.bullet("Phase 2 = prove FAR reduction and write IEEE paper.")
    pdf.bullet("Best-fit users: residual voluntary EMG + need for lamp/fan/plug control.")
    pdf.bullet("Severe complete paralysis with zero EMG needs extra modalities later.")

    pdf.quote(
        "Real-time promise: when intention is clear, Act. When unsure, Abstain. "
        "Measure success mainly by False Actuation Rate."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    print(f"PDF created: {build_pdf()}")
