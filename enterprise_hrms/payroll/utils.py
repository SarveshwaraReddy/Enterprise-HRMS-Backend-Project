import datetime
import calendar
from io import BytesIO
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from enterprise_hrms.leave_management.models import LeaveRequest

def calculate_unpaid_leave_days(employee, month, year):
    """
    Finds approved 'unpaid' leaves for the employee that overlap with the target month/year,
    and returns the total count of unpaid days.
    """
    _, last_day = calendar.monthrange(year, month)
    month_start = datetime.date(year, month, 1)
    month_end = datetime.date(year, month, last_day)
    
    unpaid_leaves = LeaveRequest.objects.filter(
        employee=employee,
        leave_type='unpaid',
        status='approved',
        start_date__lte=month_end,
        end_date__gte=month_start
    )
    
    total_days = 0
    for leave in unpaid_leaves:
        overlap_start = max(leave.start_date, month_start)
        overlap_end = min(leave.end_date, month_end)
        days = (overlap_end - overlap_start).days + 1
        total_days += days
        
    return total_days


def generate_payslip_pdf(payroll):
    """
    Generates a PDF bytes buffer containing a beautiful Salary Slip for the given payroll record.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles for payslip
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1A365D'), # Navy
        alignment=1 # Centered
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2B6CB0') # Soft Blue
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4A5568') # Charcoal
    )
    
    val_style = ParagraphStyle(
        'ValueStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2D3748')
    )
    
    total_style = ParagraphStyle(
        'TotalStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1A202C')
    )

    elements = []
    
    # Title
    elements.append(Paragraph("ENTERPRISE HRMS", title_style))
    elements.append(Paragraph("SALARY SLIP", ParagraphStyle('Sub', parent=title_style, fontSize=14, leading=18)))
    elements.append(Spacer(1, 15))
    
    # Metadata block: Employee & Period Details
    emp = payroll.employee
    month_name = calendar.month_name[payroll.month]
    
    meta_data = [
        [Paragraph("Employee ID:", label_style), Paragraph(emp.employee_id, val_style),
         Paragraph("Pay Period:", label_style), Paragraph(f"{month_name} {payroll.year}", val_style)],
        [Paragraph("Employee Name:", label_style), Paragraph(f"{emp.first_name} {emp.last_name}", val_style),
         Paragraph("Designation:", label_style), Paragraph(emp.designation, val_style)],
        [Paragraph("Email:", label_style), Paragraph(emp.email, val_style),
         Paragraph("Department:", label_style), Paragraph(emp.department.name if emp.department else "N/A", val_style)]
    ]
    
    meta_table = Table(meta_data, colWidths=[1.3*inch, 2.2*inch, 1.2*inch, 2.3*inch])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    
    elements.append(meta_table)
    elements.append(Spacer(1, 20))
    
    # Financial breakdown Table
    financial_data = [
        [Paragraph("Earnings", header_style), Paragraph("Amount ($)", header_style),
         Paragraph("Deductions", header_style), Paragraph("Amount ($)", header_style)],
        [Paragraph("Basic Salary", label_style), Paragraph(f"{payroll.basic_salary:,.2f}", val_style),
         Paragraph("Unpaid Leave Deductions", label_style), Paragraph(f"{payroll.deductions:,.2f}", val_style)],
        [Paragraph("Allowances", label_style), Paragraph(f"{payroll.allowances:,.2f}", val_style),
         Paragraph("", label_style), Paragraph("", val_style)],
        [Paragraph("Total Earnings", total_style), Paragraph(f"{(payroll.basic_salary + payroll.allowances):,.2f}", total_style),
         Paragraph("Total Deductions", total_style), Paragraph(f"{payroll.deductions:,.2f}", total_style)]
    ]
    
    fin_table = Table(financial_data, colWidths=[1.8*inch, 1.7*inch, 1.8*inch, 1.7*inch])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#EBF8FF')),
        ('BACKGROUND', (2,0), (3,0), colors.HexColor('#FFF5F5')),
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor('#CBD5E0')),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#CBD5E0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E0')),
    ]))
    elements.append(fin_table)
    elements.append(Spacer(1, 20))
    
    # Net Salary Summary Box
    net_data = [
        [Paragraph("NET SALARY", ParagraphStyle('NetLabel', parent=total_style, fontSize=12, leading=16, textColor=colors.white)),
         Paragraph(f"${payroll.net_salary:,.2f}", ParagraphStyle('NetValue', parent=total_style, fontSize=12, leading=16, textColor=colors.white))]
    ]
    net_table = Table(net_data, colWidths=[3.5*inch, 3.5*inch])
    net_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#2B6CB0')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 40))
    
    # Signature line
    sig_data = [
        [Paragraph("_____________________________", label_style), Paragraph("_____________________________", label_style)],
        [Paragraph("Employer Signature", val_style), Paragraph("Employee Signature", val_style)]
    ]
    sig_table = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
