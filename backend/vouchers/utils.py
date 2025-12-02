import qrcode
import os
from io import BytesIO
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from datetime import datetime


def generate_qr_code(token, voucher_code):
    """Generate QR code image for voucher"""
    qr_dir = os.path.join(settings.MEDIA_ROOT, "vouchers/qr/")
    os.makedirs(qr_dir, exist_ok=True)
    qr_path = os.path.join(qr_dir, f"{voucher_code}.png")

    img = qrcode.make(f"{settings.FRONTEND_URL}/public/voucher/{token}")
    img.save(qr_path)
    return f"vouchers/qr/{voucher_code}.png"


def generate_voucher_pdf(voucher, qr_path):
    """Generate a professional PDF for the voucher with agency letterhead"""
    pdf_dir = os.path.join(settings.MEDIA_ROOT, "vouchers/pdfs/")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{voucher.voucher_code}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # === Agency Letterhead (Logo + Info) ===
    y_top = height - 60
    agency_logo = None
    if voucher.agency and voucher.agency.logo:
        try:
            logo_path = voucher.agency.logo.path
            if os.path.exists(logo_path):
                agency_logo = ImageReader(logo_path)
        except Exception as e:
            print("Logo error:", e)

    if agency_logo:
        c.drawImage(agency_logo, 50, y_top - 40, width=100, height=40, preserveAspectRatio=True, mask="auto")

    # Agency Details (right side of header)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, y_top, voucher.agency.name if voucher.agency else "Travel Agency")

    c.setFont("Helvetica", 10)
    y_details = y_top - 15
    if hasattr(voucher.agency, "address") and voucher.agency.address:
        c.drawString(200, y_details, f"Address: {voucher.agency.address}")
        y_details -= 12
    if hasattr(voucher.agency, "phone") and voucher.agency.phone:
        c.drawString(200, y_details, f"Phone: {voucher.agency.phone}")
        y_details -= 12
    if hasattr(voucher.agency, "email") and voucher.agency.email:
        c.drawString(200, y_details, f"Email: {voucher.agency.email}")

    # === Voucher Title ===
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, y_top - 80, "Travel Voucher")

    # === Voucher Details Table ===
    data = [
        ["Field", "Value"],
        ["Voucher Code", voucher.voucher_code],
        ["Status", voucher.status.title()],
        ["Booking ID", str(voucher.booking.id)],
        ["Version", str(voucher.version)],
        ["Created By", str(voucher.created_by)],
        ["Approved By", str(voucher.approved_by) if voucher.approved_by else "-"],
    ]

    table = Table(data, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    table.wrapOn(c, width, height)
    table.drawOn(c, 50, y_top - 220)

    # === QR Code ===
    qr_full_path = os.path.join(settings.MEDIA_ROOT, qr_path)
    if os.path.exists(qr_full_path):
        c.drawImage(qr_full_path, width - 180, y_top - 250, width=120, height=120)

    # === Footer ===
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(50, 40, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawRightString(width - 40, 40, "Powered by Nahd Travels System")

    c.showPage()
    c.save()

    return f"vouchers/pdfs/{voucher.voucher_code}.pdf"
