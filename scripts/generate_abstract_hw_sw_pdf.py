"""Generate base paper vs NeuroShift abstract/conclusion/HW-SW comparison PDF."""

from pathlib import Path

from fpdf import FPDF

OUT = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "NeuroShift_Base_vs_Ours_Abstract_HW_SW.pdf"
)


class CompPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(90, 90, 90)
        self.cell(
            0,
            8,
            "NeuroShift 2.0 | Base Paper vs Ours (Abstract, Conclusion, HW/SW)",
            align="L",
        )
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
    pdf = CompPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.title_block(
        "Base Paper vs NeuroShift",
        "Abstract, Conclusion, Hardware and Software comparison | "
        "Base: Chamberland et al., IEEE EMBC 2024",
    )

    pdf.quote(
        "Base paper: safer EMG GESTURE recognition for prosthesis using vision.  "
        "NeuroShift: safer HOME INTENTION control using vision + sparse EMG with "
        "Act/Abstain and FAR metric."
    )

    # ---------- ABSTRACT ----------
    pdf.section("1. Abstract comparison")

    pdf.sub_section("1.1 Base paper abstract (summary)")
    pdf.body(
        "Title: Visual Scene Understanding for Enhanced EMG Gesture Recognition"
    )
    pdf.quote(
        "A multimodal approach combining electromyography (EMG) and computer vision "
        "for robust real-time gesture recognition. Context-aware framework for "
        "myoelectric prosthesis control: EMG hand gesture recognition is augmented by "
        "visual detection of objects, mitigating false movements. SDCNN EMG predictions "
        "are supported by a tailored YOLO model. Pilot experiment shows improved "
        "robustness while keeping user command."
    )
    pdf.bullet("Focus: gesture recognition robustness")
    pdf.bullet("Domain: myoelectric prosthesis")
    pdf.bullet("Vision role: reduce false gesture detections")
    pdf.bullet("Output: gesture class (grip type)")

    pdf.sub_section("1.2 NeuroShift abstract (draft for our project)")
    pdf.quote(
        "NeuroShift is a multimodal AI framework for assistive smart-home control. "
        "The camera detects appliances and which one the user is looking at (gaze/"
        "head direction). Sparse EMG then confirms whether they truly want to toggle "
        "it. Looking alone never actuates. The system Acts or Abstains, targeting "
        "lower False Actuation Rate (FAR). Existing Indian wired appliances are "
        "controlled via ESP32+MQTT relay hub. Phase 1: head-gaze + EMG demo. "
        "Phase 2: eye-gaze, learned fusion, priors, XAI, IEEE evaluation."
    )
    pdf.bullet("Focus: gaze-select + EMG-confirm + safe actuation")
    pdf.bullet("Domain: assistive smart home / independent living")
    pdf.bullet("Vision role: detect appliances + select by gaze")
    pdf.bullet("EMG role: confirm intent only (not gesture classes)")
    pdf.bullet("Output: device action OR abstain")

    pdf.sub_section("1.3 Abstract side-by-side")
    pdf.table(
        ["Point", "Base paper", "NeuroShift"],
        [
            ["Problem", "False EMG gestures in prosthesis control", "False/unsafe home device actuations"],
            ["Users", "Upper-limb prosthesis users", "Motor-impaired users with residual EMG"],
            ["Predicts", "Hand gesture / grip", "Home device intention or abstain"],
            ["Vision job", "Validate/filter grips", "Build affordance candidates"],
            ["EMG job", "Classify gesture", "Confirm volition/effort"],
            ["Safety idea", "Fewer false movements", "Act/Abstain + FAR"],
            ["Setting", "Lab prosthesis scenarios", "Indian wired home appliances"],
        ],
        [28, 76, 76],
    )

    pdf.add_page()
    # ---------- CONCLUSION ----------
    pdf.section("2. Conclusion comparison")

    pdf.sub_section("2.1 Base paper conclusion (summary)")
    pdf.quote(
        "Pilot work shows vision-based object detection can provide context for EMG "
        "gesture recognition while preserving user agency. SDCNN confidence helps when "
        "EMG is ambiguous. Vision fusion corrected many false predictions in real time. "
        "Challenges remain: crowded scenes, occlusion, unknown objects, and better "
        "EMG/vision confidence fusion. Future work: improve YOLO for amputee needs and "
        "explore temporal confidence fusion."
    )
    pdf.bullet("Proved: EMG + vision reduces gesture errors")
    pdf.bullet("Kept: user still chooses grip")
    pdf.bullet("Open issues: multi-object clutter, occlusion, unknown objects")

    pdf.sub_section("2.2 NeuroShift conclusion (draft)")
    pdf.quote(
        "NeuroShift extends scene-aware EMG-vision fusion from prosthetic gesture "
        "rescue to assistive smart-home intention inference. By treating sparse EMG as "
        "volitional confirmation and vision as an affordance proposer, the system can "
        "Act on a target appliance or Abstain under ambiguity, targeting lower False "
        "Actuation Rate in multi-object domestic scenes. Integration via MQTT relays/"
        "smart plugs makes the approach compatible with conventional Indian wired "
        "homes. Phase 1 delivers a working prototype and pilot dataset; Phase 2 "
        "provides learned fusion, personal priors, decision-level explanations, and "
        "IEEE-oriented evaluation against EMG-only, vision-only, and Chamberland-style "
        "baselines."
    )
    pdf.bullet("Proves: intention + abstention can reduce false home actuations")
    pdf.bullet("Keeps: user agency via EMG confirmation")
    pdf.bullet("Addresses base-paper gap: multi-object ambiguity via Abstain")

    pdf.sub_section("2.3 Conclusion side-by-side")
    pdf.table(
        ["Point", "Base paper", "NeuroShift"],
        [
            ["Main finding", "Vision context improves gesture robustness", "Affordance + EMG + abstain improves safe home control"],
            ["Primary metric spirit", "Gesture errors fixed / accuracy", "FAR + intention F1"],
            ["User agency", "User still selects grip", "User confirms volition; system may refuse action"],
            ["Future work they left", "Crowded scenes, better fusion", "We take crowded scenes as core Act/Abstain problem"],
            ["Deployment", "Prosthesis control concept", "ESP32 hub for normal wired homes"],
        ],
        [32, 74, 74],
    )

    pdf.add_page()
    # ---------- HARDWARE ----------
    pdf.section("3. Hardware comparison")
    pdf.table(
        ["Item", "Base paper (used)", "NeuroShift (we will use)"],
        [
            ["EMG sensor", "EMaGer 64-channel HD-EMG @ 1 kHz (custom lab sensor)", "MyoWare 2.0 sparse EMG (commercial)"],
            ["EMG channels", "64 (high-density array)", "1 (expandable to 2 later)"],
            ["Camera", "EMEET C960 webcam, head-mounted, 640x480", "USB webcam / laptop webcam (ambient room view)"],
            ["Compute", "PC + GTX 1080 GPU (reported for YOLO)", "Laptop GPU/CPU (student setup)"],
            ["Actuation target", "Prosthesis gesture/grip output (control interface)", "Lamp / fan / plug via relays or smart plugs"],
            ["IoT / home layer", "Not for home appliances", "ESP32 + MQTT + relay module / smart plug"],
            ["Indian wired homes", "Not addressed", "Yes - retrofit relay interface + manual override"],
            ["Wearable form", "HD-EMG bracelet (EMaGer)", "MyoWare + optional 3D-printed armband"],
            ["Demo appliances", "Mug, apple, bottle, phone (grasp scenarios)", "Real on/off devices (lamp, fan, plug)"],
            ["Cost level", "Research HD-EMG (expensive/custom)", "Approx. Rs 10k-15k student kit"],
        ],
        [32, 74, 74],
    )

    pdf.sub_section("Why we change hardware")
    pdf.bullet("EMaGer is custom 64-ch research hardware - not practical for our timeline/budget.")
    pdf.bullet("Our novelty is intention + Act/Abstain + FAR, not HD-EMG sensor design.")
    pdf.bullet("MyoWare is enough for volition confirmation in assistive home control.")
    pdf.bullet("ESP32/MQTT is required because we control real home appliances.")

    # ---------- SOFTWARE ----------
    pdf.section("4. Software / algorithm comparison")
    pdf.table(
        ["Module", "Base paper", "NeuroShift"],
        [
            ["EMG model", "SDCNN (Siamese Deep CNN) + centroid classifier", "RMS/MAV volition score; Phase2 small TCN/1D-CNN"],
            ["Gesture/intent classes", "6 grips: open, tripod, power, thumbs-up, pinch, point", "Device actions: lamp/fan/plug + ABSTAIN"],
            ["Object detection", "Custom YOLOv8-small (28 classes)", "YOLO11/YOLOv8/RT-DETR (home devices)"],
            ["Selector", "MediaPipe Hands near object", "Phase1 head/face gaze; Phase2 eye-gaze"],
            ["Fusion method", "OLF enables object-related grips", "Gaze selects + EMG confirms + Act/Abstain"],
            ["If unsure", "Mostly still gesture pathway / defaults", "Explicit ABSTAIN (looking != wanting)"],
            ["Backend / UI", "Real-time processing pipeline", "Python + FastAPI + React dashboard + logger"],
            ["IoT software", "Not applicable", "MQTT (Mosquitto) + ESP32 firmware"],
            ["Database", "Not central", "SQLite (P1) / PostgreSQL (P2) trial logs"],
            ["Primary metric", "Gesture errors reduced", "False Actuation Rate (FAR) + intention F1"],
            ["XAI", "Limited (confidence scores)", "Phase 2 decision-level explanations"],
            ["Personalization", "No", "Phase 2 temporal/habit prior"],
        ],
        [32, 74, 74],
    )

    pdf.add_page()
    pdf.section("5. Items list - Base paper used")
    pdf.sub_section("Hardware")
    pdf.bullet("EMaGer HD-EMG bracelet (64 channels, 1 kHz)")
    pdf.bullet("EMEET C960 head-mounted webcam")
    pdf.bullet("PC with GPU (GTX 1080 mentioned for YOLO inference)")
    pdf.sub_section("Software / models")
    pdf.bullet("SDCNN (Siamese CNN) for EMG gesture recognition")
    pdf.bullet("YOLOv8-small custom-trained object detector")
    pdf.bullet("MediaPipe Hands")
    pdf.bullet("Object Likelihood Filtering (OLF) fusion logic")
    pdf.bullet("Training data context from COCO + OpenImages (28 classes)")

    pdf.section("6. Items list - NeuroShift will use")
    pdf.sub_section("Hardware (Phase 1)")
    pdf.bullet("MyoWare 2.0 muscle sensor + electrode pads")
    pdf.bullet("ESP32 DevKit (1-2)")
    pdf.bullet("Relay module and/or MQTT smart plug")
    pdf.bullet("USB/laptop webcam")
    pdf.bullet("Laptop for AI inference")
    pdf.bullet("Table lamp + desk fan (demo) compatible with Indian wired homes")
    pdf.bullet("Optional: 3D-printed armband + hub enclosure")
    pdf.sub_section("Software (Phase 1)")
    pdf.bullet("Python, PyTorch, OpenCV")
    pdf.bullet("YOLOv8 or RT-DETR + MediaPipe/RTMPose")
    pdf.bullet("Rule-based Act/Abstain intention policy")
    pdf.bullet("FastAPI + React dashboard")
    pdf.bullet("MQTT (Mosquitto) + ESP32 firmware")
    pdf.bullet("SQLite/CSV trial logger")
    pdf.sub_section("Software (Phase 2 add)")
    pdf.bullet("Learned fusion model (MLP / small cross-attention)")
    pdf.bullet("Calibrated abstention for FAR")
    pdf.bullet("Personal temporal prior")
    pdf.bullet("Decision-level XAI + caregiver views")
    pdf.bullet("PostgreSQL + full evaluation scripts")

    pdf.section("7. One-page takeaway for guide")
    pdf.table(
        ["Layer", "They did", "We do"],
        [
            ["Abstract aim", "Better prosthesis gestures with vision", "Safer home intentions with Act/Abstain"],
            ["Conclusion aim", "Vision reduces EMG gesture errors", "Vision+EMG+abstain reduces false home actuations"],
            ["EMG hardware", "Custom 64-ch EMaGer", "MyoWare sparse EMG"],
            ["Vision software", "YOLO + MediaPipe + OLF", "YOLO/RT-DETR + pose + affordance policy"],
            ["Output", "Grip class", "Device action or Abstain"],
            ["Home integration", "No", "ESP32 + MQTT relays for wired appliances"],
        ],
        [28, 76, 76],
    )

    pdf.quote(
        "We keep the base paper's multimodal idea (EMG + vision), change the problem "
        "(home intention), change the safety policy (Act/Abstain), change the metric "
        "(FAR), and change the hardware to a low-cost MyoWare + ESP32 stack suitable "
        "for Indian homes and college implementation."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    print(f"PDF created: {build_pdf()}")
