import io
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_invoice_pdf(invoice, user, client) -> bytes:
    """Generate a high-quality PDF invoice and return bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    header_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Normal"],
        fontSize=24,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1e1b4b"),
        spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#6b7280"),
        spaceAfter=15,
    )
    meta_header = ParagraphStyle(
        "MetaHeader",
        parent=styles["Normal"],
        fontSize=12,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#111827"),
    )
    meta_body = ParagraphStyle(
        "MetaBody",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#4b5563"),
        leading=14,
    )

    # Business Header & Invoice Number
    biz_name = user.business_name or "Invoice Chaser Business"
    biz_email = user.email

    header_table = Table([
        [
            Paragraph(f"<b>{biz_name}</b><br/><font size=9 color='#6b7280'>{biz_email}</font>", meta_body),
            Paragraph(f"<font size=22 color='#4f46e5'><b>INVOICE</b></font><br/><b>#{invoice.invoice_number}</b>", ParagraphStyle("InvRight", parent=meta_body, alignment=2)),
        ]
    ], colWidths=[3.5 * inch, 3.5 * inch])
    story.append(header_table)
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4f46e5"), spaceAfter=20))

    # Bill To & Dates Table
    curr = invoice.currency or "USD"
    issued_str = invoice.issued_date.strftime("%B %d, %Y")
    due_str = invoice.due_date.strftime("%B %d, %Y")
    status_color = "#16a34a" if invoice.status == "paid" else ("#dc2626" if invoice.status == "overdue" else "#2563eb")

    client_info = f"""
    <b>Bill To:</b><br/>
    {client.name}<br/>
    {f'{client.company}<br/>' if client.company else ''}
    {client.email}
    """

    invoice_meta = f"""
    <b>Invoice Date:</b> {issued_str}<br/>
    <b>Due Date:</b> {due_str}<br/>
    <b>Status:</b> <font color='{status_color}'><b>{invoice.status.upper()}</b></font>
    """

    info_table = Table([
        [Paragraph(client_info, meta_body), Paragraph(invoice_meta, meta_body)]
    ], colWidths=[3.5 * inch, 3.5 * inch])
    story.append(info_table)
    story.append(Spacer(1, 25))

    # Line Items Table
    description = invoice.description or "Professional Services Rendered"
    amt = float(invoice.amount)

    table_data = [
        ["DESCRIPTION", "QTY", "RATE", "AMOUNT"],
        [description, "1", f"{amt:,.2f}", f"{amt:,.2f}"],
        ["", "", "TOTAL DUE:", f"{curr} {amt:,.2f}"]
    ]

    item_table = Table(table_data, colWidths=[4.0 * inch, 0.8 * inch, 1.1 * inch, 1.3 * inch])
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, 1), 0.5, colors.HexColor("#e5e7eb")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#4f46e5")),
        ("FONTNAME", (2, 2), (3, 2), "Helvetica-Bold"),
        ("FONTSIZE", (2, 2), (3, 2), 12),
        ("TEXTCOLOR", (3, 2), (3, 2), colors.HexColor("#4f46e5")),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 35))

    # Payment link note or instructions
    if invoice.payment_url:
        pay_info = f"<b>Pay Online:</b> You can conveniently pay this invoice directly at: {invoice.payment_url}"
        story.append(Paragraph(pay_info, meta_body))
        story.append(Spacer(1, 15))

    note_text = "Thank you for your business! Please remit payment on or before the due date."
    story.append(Paragraph(f"<i>{note_text}</i>", meta_body))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
