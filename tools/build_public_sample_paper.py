from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


root = Path(__file__).resolve().parents[1]
target = root / "Inbox" / "paper-guide" / "public-sample" / "synthetic-research-note.pdf"
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="PaperTitle", parent=styles["Title"], fontSize=20, leading=25, alignment=TA_CENTER, spaceAfter=14))
styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=14, leading=18, textColor=colors.HexColor("#173F5F"), spaceBefore=10, spaceAfter=8))
styles.add(ParagraphStyle(name="BodyWide", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=8))


def footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(20 * mm, 12 * mm, "Synthetic public sample - no real measurements")
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {document.page}")
    canvas.restoreState()


story = [
    Paragraph("Analyzer-angle signatures of linear and circular polarization", styles["PaperTitle"]),
    Paragraph("A synthetic teaching paper for testing Research Starter Paper Guide", styles["Heading3"]),
    Spacer(1, 6 * mm),
    Paragraph("Abstract", styles["Section"]),
    Paragraph(
        "We compare idealized analyzer-angle scans for nominally linear and circular polarization. "
        "The linear series follows Malus' law, while the circular series remains nearly angle independent. "
        "A small offset and deterministic perturbation are included to illustrate baseline subtraction, uncertainty, "
        "model checking, and the distinction between an observation and a physical conclusion.", styles["BodyWide"]),
    Paragraph("Questions addressed", styles["Section"]),
    Paragraph("1. Which angular signature distinguishes the two prepared states?<br/>2. How does a detector offset alter normalized contrast?<br/>3. Which conclusions require calibration evidence beyond the plotted curves?", styles["BodyWide"]),
    Paragraph("Key equations", styles["Section"]),
    Paragraph("Linear model: I(theta) = I0 cos^2(theta - theta0) + b", styles["BodyWide"]),
    Paragraph("Visibility: V = (Imax - Imin) / (Imax + Imin)", styles["BodyWide"]),
    PageBreak(),
    Paragraph("1. Synthetic method", styles["Section"]),
    Paragraph(
        "A source is prepared in two nominal states and measured after a rotating linear analyzer. "
        "Angles span 0 to 180 degrees in 15 degree steps. Each point represents the mean of five synthetic repeats. "
        "The detector offset b is estimated from a blocked-source reading and subtracted before normalization.", styles["BodyWide"]),
    Table([
        ["Parameter", "Linear run", "Circular run"],
        ["Analyzer step", "15 deg", "15 deg"],
        ["Synthetic repeats", "5", "5"],
        ["Blocked offset", "0.030", "0.030"],
        ["Mean normalized intensity", "0.515", "0.502"],
        ["Visibility", "0.91", "0.04"],
    ], colWidths=[55 * mm, 50 * mm, 50 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173F5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#AAB4C0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F8")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ])),
    Paragraph("Reproducibility note", styles["Section"]),
    Paragraph("The values are deliberately synthetic. They are internally consistent enough to support calculation and critique, but they must never be presented as experimental evidence.", styles["BodyWide"]),
    PageBreak(),
    Paragraph("2. Results and interpretation", styles["Section"]),
    Paragraph(
        "The linear series has maxima near 30 and 210 degrees and minima approximately 90 degrees away. "
        "The circular series changes by less than five percent across analyzer angle. Offset subtraction increases "
        "the estimated linear visibility from 0.86 to 0.91, showing why baseline treatment matters.", styles["BodyWide"]),
    Table([
        ["Angle (deg)", "Linear", "Circular"],
        ["0", "0.78", "0.50"], ["30", "1.00", "0.51"], ["60", "0.76", "0.49"],
        ["90", "0.26", "0.50"], ["120", "0.05", "0.52"], ["150", "0.27", "0.48"], ["180", "0.79", "0.50"],
    ], colWidths=[45 * mm, 45 * mm, 45 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F6690")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C2CC")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("PADDING", (0, 0), (-1, -1), 5),
    ])),
    Paragraph("Alternative explanations", styles["Section"]),
    Paragraph("A flat scan does not by itself prove perfect circular polarization. Rapid polarization drift, analyzer misalignment, detector saturation, or averaging over unresolved states can produce a similar pattern.", styles["BodyWide"]),
    PageBreak(),
    Paragraph("3. Discussion prompts", styles["Section"]),
    Paragraph("Use these prompts to test follow-up discussion in the Paper Guide workspace:", styles["BodyWide"]),
    Paragraph("- Derive the visibility after subtracting the stated offset.<br/>- Explain why a flat analyzer scan is necessary but not sufficient evidence of circular polarization.<br/>- Propose one calibration and one control measurement.<br/>- Compare the table with Malus' law and identify the largest residual.<br/>- Rewrite the conclusion with a clear separation between observation, inference, and limitation.", styles["BodyWide"]),
    Paragraph("Conclusion", styles["Section"]),
    Paragraph("The synthetic data reproduce the expected qualitative contrast between linear and circular states. A defensible interpretation still depends on detector linearity, analyzer calibration, repeatability, and explicit uncertainty reporting.", styles["BodyWide"]),
]

target.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(target), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm).build(story, onFirstPage=footer, onLaterPages=footer)
print(target)
