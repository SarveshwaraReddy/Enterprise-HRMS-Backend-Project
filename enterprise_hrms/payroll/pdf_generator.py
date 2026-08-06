import os
import io
import qrcode
from pathlib import Path
from decimal import Decimal
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
)


def generate_qr_code_image(data_text):
    """
    Generates a QR code image as BytesIO stream.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=2,
    )
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generate_payslip_pdf(payslip):
    """
    Generates a PDF payslip for a given Payslip instance (or legacy Payroll instance).
    Saves to media/payslips/ and updates payslip.pdf_path if attribute exists.
    Returns bytes content of the PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CompanyTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E3A8A'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'CompanySubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4B5563')
    )
    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E3A8A'),
        fontName='Helvetica-Bold',
        spaceAfter=6
    )
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1F2937')
    )
    bold_style = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1F2937'),
        fontName='Helvetica-Bold'
    )

    story = []

    emp = payslip.employee
    if hasattr(payslip, 'payroll_run') and payslip.payroll_run:
        run = payslip.payroll_run
        month = run.payroll_month
        year = run.payroll_year
        status_str = run.status.capitalize()
    else:
        month = getattr(payslip, 'month', 1)
        year = getattr(payslip, 'year', 2026)
        status_str = str(getattr(payslip, 'status', 'generated')).capitalize()

    gross_salary = Decimal(str(getattr(payslip, 'gross_salary', getattr(payslip, 'basic_salary', Decimal('0.00')) + getattr(payslip, 'allowances', Decimal('0.00')))))
    total_deductions = Decimal(str(getattr(payslip, 'total_deductions', getattr(payslip, 'deductions', Decimal('0.00')))))
    net_salary = Decimal(str(getattr(payslip, 'net_salary', Decimal('0.00'))))

    working_days = getattr(payslip, 'working_days', 30)
    present_days = getattr(payslip, 'present_days', Decimal('30.0'))
    leave_days = getattr(payslip, 'leave_days', Decimal('0.0'))
    overtime_hours = Decimal(str(getattr(payslip, 'overtime_hours', Decimal('0.00'))))

    payslip_id = getattr(payslip, 'id', 'N/A')

    qr_text = (
        f"PAYSLIP VERIFICATION\n"
        f"Payslip ID: {payslip_id}\n"
        f"Employee: {emp.first_name} {emp.last_name} ({emp.employee_id})\n"
        f"Period: {month:02d}/{year}\n"
        f"Net Salary: ${net_salary:,.2f}"
    )
    qr_buffer = generate_qr_code_image(qr_text)
    qr_img = Image(qr_buffer, width=70, height=70)

    header_text = [
        [
            Paragraph("ENTERPRISE HRMS CORP", title_style),
            qr_img
        ],
        [
            Paragraph("100 Corporate Parkway, Suite 500 &bull; HR & Payroll Operations", subtitle_style),
            Paragraph("<b>QR Verification</b>", subtitle_style)
        ]
    ]

    header_table = Table(header_text, colWidths=[400, 140])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=15))

    story.append(Paragraph(f"<b>PAYSLIP FOR THE MONTH OF {month:02d}/{year}</b>", header_style))
    story.append(Spacer(1, 8))

    emp_info_data = [
        [
            Paragraph("<b>Employee ID:</b>", bold_style), Paragraph(str(emp.employee_id), normal_style),
            Paragraph("<b>Department:</b>", bold_style), Paragraph(str(emp.department.name if emp.department else 'N/A'), normal_style),
        ],
        [
            Paragraph("<b>Employee Name:</b>", bold_style), Paragraph(f"{emp.first_name} {emp.last_name}", normal_style),
            Paragraph("<b>Designation:</b>", bold_style), Paragraph(str(emp.designation), normal_style),
        ],
        [
            Paragraph("<b>Email:</b>", bold_style), Paragraph(str(emp.email), normal_style),
            Paragraph("<b>Status:</b>", bold_style), Paragraph(status_str, normal_style),
        ]
    ]
    emp_info_table = Table(emp_info_data, colWidths=[110, 160, 110, 160])
    emp_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F3F4F6')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(emp_info_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Attendance Summary</b>", header_style))
    attendance_data = [
        [
            Paragraph("<b>Working Days</b>", bold_style),
            Paragraph("<b>Present Days</b>", bold_style),
            Paragraph("<b>Leave Days</b>", bold_style),
            Paragraph("<b>Overtime Hours</b>", bold_style),
        ],
        [
            Paragraph(str(working_days), normal_style),
            Paragraph(str(present_days), normal_style),
            Paragraph(str(leave_days), normal_style),
            Paragraph(f"{overtime_hours:.2f} hrs", normal_style),
        ]
    ]
    attendance_table = Table(attendance_data, colWidths=[135, 135, 135, 135])
    attendance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E5E7EB')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
    ]))
    story.append(attendance_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Earnings & Deductions Breakdown</b>", header_style))

    salary_struct = emp.salary_structures.filter(status='active').first() if hasattr(emp, 'salary_structures') else None
    basic = salary_struct.basic_salary if salary_struct else getattr(payslip, 'basic_salary', Decimal('0.00'))
    hra = salary_struct.house_rent_allowance if salary_struct else Decimal('0.00')
    special = salary_struct.special_allowance if salary_struct else Decimal('0.00')
    travel = salary_struct.travel_allowance if salary_struct else Decimal('0.00')
    medical = salary_struct.medical_allowance if salary_struct else getattr(payslip, 'allowances', Decimal('0.00'))

    pf = salary_struct.provident_fund if salary_struct else Decimal('0.00')
    ptax = salary_struct.professional_tax if salary_struct else Decimal('0.00')
    itax = salary_struct.income_tax if salary_struct else Decimal('0.00')
    other_ded = salary_struct.other_deductions if salary_struct else getattr(payslip, 'deductions', Decimal('0.00'))

    breakdown_data = [
        [
            Paragraph("<b>Earnings</b>", bold_style), Paragraph("<b>Amount ($)</b>", bold_style),
            Paragraph("<b>Deductions</b>", bold_style), Paragraph("<b>Amount ($)</b>", bold_style)
        ],
        [Paragraph("Basic Salary", normal_style), Paragraph(f"{basic:,.2f}", normal_style), Paragraph("Provident Fund (PF)", normal_style), Paragraph(f"{pf:,.2f}", normal_style)],
        [Paragraph("House Rent Allowance (HRA)", normal_style), Paragraph(f"{hra:,.2f}", normal_style), Paragraph("Professional Tax", normal_style), Paragraph(f"{ptax:,.2f}", normal_style)],
        [Paragraph("Special Allowance", normal_style), Paragraph(f"{special:,.2f}", normal_style), Paragraph("Income Tax (TDS)", normal_style), Paragraph(f"{itax:,.2f}", normal_style)],
        [Paragraph("Travel Allowance", normal_style), Paragraph(f"{travel:,.2f}", normal_style), Paragraph("Other Deductions", normal_style), Paragraph(f"{other_ded:,.2f}", normal_style)],
        [Paragraph("Medical Allowance", normal_style), Paragraph(f"{medical:,.2f}", normal_style), Paragraph("LWP / Other Adjustments", normal_style), Paragraph(f"{(total_deductions - pf - ptax - itax - other_ded):,.2f}", normal_style)],
        [
            Paragraph("<b>Total Gross Earnings</b>", bold_style), Paragraph(f"<b>${gross_salary:,.2f}</b>", bold_style),
            Paragraph("<b>Total Deductions</b>", bold_style), Paragraph(f"<b>${total_deductions:,.2f}</b>", bold_style)
        ]
    ]

    breakdown_table = Table(breakdown_data, colWidths=[170, 100, 170, 100])
    breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#DBEAFE')),
        ('BACKGROUND', (2, 0), (3, 0), colors.HexColor('#FEE2E2')),
        ('BACKGROUND', (0, -1), (1, -1), colors.HexColor('#EFF6FF')),
        ('BACKGROUND', (2, -1), (3, -1), colors.HexColor('#FEF2F2')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
    ]))
    story.append(breakdown_table)
    story.append(Spacer(1, 15))

    net_box_data = [
        [
            Paragraph("<b>NET SALARY PAYABLE:</b>", ParagraphStyle('NetTitle', parent=bold_style, fontSize=12, textColor=colors.HexColor('#1E3A8A'))),
            Paragraph(f"<b>${net_salary:,.2f}</b>", ParagraphStyle('NetValue', parent=bold_style, fontSize=14, textColor=colors.HexColor('#065F46'), alignment=2))
        ]
    ]
    net_box = Table(net_box_data, colWidths=[300, 240])
    net_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#D1FAE5')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#10B981')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(net_box)
    story.append(Spacer(1, 25))

    footer_data = [
        [
            Paragraph("<b>Employee Signature</b><br/><br/>______________________", normal_style),
            Paragraph("<b>Authorized Signatory</b><br/><br/>______________________", normal_style)
        ]
    ]
    footer_table = Table(footer_data, colWidths=[270, 270])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(footer_table)

    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()

    filename = f"payslip_{emp.employee_id}_{month}_{year}.pdf"
    relative_path = f"payslips/{filename}"

    media_dir = Path(settings.MEDIA_ROOT) / "payslips"
    os.makedirs(media_dir, exist_ok=True)

    file_path = media_dir / filename
    with open(file_path, "wb") as f:
        f.write(pdf_content)

    if hasattr(payslip, 'pdf_path'):
        payslip.pdf_path.name = relative_path
        if hasattr(payslip, 'save'):
            payslip.save(update_fields=['pdf_path'])

    return pdf_content
