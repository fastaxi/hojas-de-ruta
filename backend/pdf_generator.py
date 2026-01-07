"""
RutasFast - PDF Generator using ReportLab
Generates A4 route sheet PDFs
"""
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os


def get_logo_path():
    """Get path to logo file"""
    logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
    if os.path.exists(logo_path):
        return logo_path
    return None


def generate_route_sheet_pdf(sheet: dict, user: dict, config: dict, driver_name: str) -> io.BytesIO:
    """
    Generate a single route sheet PDF
    Returns BytesIO buffer with PDF content
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=3*mm,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#701111')
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#57534E'),
        spaceAfter=2*mm
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1C1917'),
        spaceBefore=5*mm,
        spaceAfter=3*mm
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#57534E'),
        fontName='Helvetica-Bold'
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1C1917')
    )
    
    legend_style = ParagraphStyle(
        'Legend',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#A8A29E'),
        alignment=TA_CENTER,
        spaceBefore=10*mm
    )
    
    sheet_number_style = ParagraphStyle(
        'SheetNumber',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#701111'),
        alignment=TA_RIGHT
    )
    
    elements = []
    
    # Header with logo
    logo_path = get_logo_path()
    header_data = []
    
    if logo_path:
        try:
            logo = Image(logo_path, width=40*mm, height=16*mm)
            header_data.append([logo, ''])
        except:
            header_data.append([Paragraph('<b style="color:#701111;font-size:20px;">FAST</b>', styles['Normal']), ''])
    else:
        header_data.append([Paragraph('<font color="#701111" size="20"><b>FAST</b></font>', styles['Normal']), ''])
    
    header_table = Table(header_data, colWidths=[50*mm, 120*mm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 5*mm))
    
    # Title
    elements.append(Paragraph(config.get('header_title', 'HOJA DE RUTA'), title_style))
    
    # Subtitle lines
    elements.append(Paragraph(config.get('header_line1', ''), header_style))
    elements.append(Paragraph(config.get('header_line2', ''), header_style))
    elements.append(Spacer(1, 3*mm))
    
    # Organization info
    elements.append(Paragraph('RutasFast / Federación Asturiana Sindical del Taxi (FAST)', header_style))
    elements.append(Spacer(1, 5*mm))
    
    # Sheet number
    sheet_number = f"{sheet['seq_number']:03d}/{sheet['year']}"
    elements.append(Paragraph(f"Nº Hoja: {sheet_number}", sheet_number_style))
    elements.append(Spacer(1, 5*mm))
    
    # Driver/Vehicle Section
    elements.append(Paragraph('DATOS DEL SERVICIO', section_title))
    
    # Create data table
    data = [
        ['Titular:', user.get('full_name', ''), 'DNI/CIF:', user.get('dni_cif', '')],
        ['Conductor:', driver_name, 'Licencia:', user.get('license_number', '')],
        ['Vehículo:', f"{user.get('vehicle_brand', '')} {user.get('vehicle_model', '')}", 'Matrícula:', user.get('vehicle_plate', '')],
    ]
    
    info_table = Table(data, colWidths=[25*mm, 60*mm, 25*mm, 60*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#57534E')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#57534E')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1C1917')),
        ('TEXTCOLOR', (3, 0), (3, -1), colors.HexColor('#1C1917')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    elements.append(info_table)
    
    # Service details
    elements.append(Paragraph('DETALLES DEL SERVICIO', section_title))
    
    # Contractor info
    contractor_info = []
    if sheet.get('contractor_phone'):
        contractor_info.append(f"Tel: {sheet['contractor_phone']}")
    if sheet.get('contractor_email'):
        contractor_info.append(f"Email: {sheet['contractor_email']}")
    
    service_data = [
        ['Contratante:', ' | '.join(contractor_info) if contractor_info else '-'],
        ['Precontratado:', f"{sheet.get('prebooked_date', '')} en {sheet.get('prebooked_locality', '')}"],
        ['Recogida:', f"{sheet.get('pickup_type', '')} - {sheet.get('pickup_address', '') or 'Aeropuerto de Asturias'}"],
        ['Fecha/Hora:', sheet.get('pickup_datetime', '')],
    ]
    
    if sheet.get('flight_number'):
        service_data.append(['Nº Vuelo:', sheet['flight_number']])
    
    service_data.append(['Destino:', sheet.get('destination', '')])
    
    service_table = Table(service_data, colWidths=[30*mm, 140*mm])
    service_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#57534E')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1C1917')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#E5E5E5')),
    ]))
    elements.append(service_table)
    
    # Status if annulled
    if sheet.get('status') == 'ANNULLED':
        elements.append(Spacer(1, 5*mm))
        annul_style = ParagraphStyle(
            'Annulled',
            parent=styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#DC2626'),
            alignment=TA_CENTER
        )
        elements.append(Paragraph('** HOJA ANULADA **', annul_style))
        if sheet.get('annul_reason'):
            elements.append(Paragraph(f"Motivo: {sheet['annul_reason']}", header_style))
    
    # Legend
    elements.append(Spacer(1, 15*mm))
    legend_text = config.get('legend_text', 'Es obligatorio conservar los registros durante 12 meses desde la fecha de recogida del servicio.')
    elements.append(Paragraph(legend_text, legend_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_multi_sheet_pdf(sheets: list, user: dict, config: dict, drivers_map: dict) -> io.BytesIO:
    """
    Generate PDF with multiple route sheets (one per page)
    """
    buffer = io.BytesIO()
    
    from reportlab.platypus import PageBreak
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    all_elements = []
    
    for i, sheet in enumerate(sheets):
        driver_name = "Titular"
        if sheet.get("conductor_driver_id"):
            driver_name = drivers_map.get(sheet["conductor_driver_id"], "Titular")
        
        # Generate single sheet content
        single_buffer = generate_route_sheet_pdf(sheet, user, config, driver_name)
        
        # For multi-page, we need to rebuild
        # This is a simplified approach - append content with page breaks
        if i > 0:
            all_elements.append(PageBreak())
        
        # Re-read and add elements (simplified for now - in production, refactor to share elements)
        # For simplicity, we'll regenerate inline
    
    # For now, return combined PDF using a different approach
    # Use PyPDF2 or similar to merge - but keeping it simple with reportlab
    
    # Simplified: generate all in one doc
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=3*mm,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#701111')
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#57534E'),
        spaceAfter=2*mm
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1C1917'),
        spaceBefore=5*mm,
        spaceAfter=3*mm
    )
    
    sheet_number_style = ParagraphStyle(
        'SheetNumber',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#701111'),
        alignment=TA_RIGHT
    )
    
    legend_style = ParagraphStyle(
        'Legend',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#A8A29E'),
        alignment=TA_CENTER,
        spaceBefore=10*mm
    )
    
    from reportlab.platypus import PageBreak
    
    for i, sheet in enumerate(sheets):
        if i > 0:
            all_elements.append(PageBreak())
        
        driver_name = "Titular"
        if sheet.get("conductor_driver_id"):
            driver_name = drivers_map.get(sheet["conductor_driver_id"], "Titular")
        
        # Header
        logo_path = get_logo_path()
        if logo_path:
            try:
                logo = Image(logo_path, width=40*mm, height=16*mm)
                all_elements.append(logo)
            except:
                all_elements.append(Paragraph('<font color="#701111" size="20"><b>FAST</b></font>', styles['Normal']))
        else:
            all_elements.append(Paragraph('<font color="#701111" size="20"><b>FAST</b></font>', styles['Normal']))
        
        all_elements.append(Spacer(1, 5*mm))
        all_elements.append(Paragraph(config.get('header_title', 'HOJA DE RUTA'), title_style))
        all_elements.append(Paragraph(config.get('header_line1', ''), header_style))
        all_elements.append(Paragraph(config.get('header_line2', ''), header_style))
        all_elements.append(Paragraph('RutasFast / Federación Asturiana Sindical del Taxi (FAST)', header_style))
        
        sheet_number = f"{sheet['seq_number']:03d}/{sheet['year']}"
        all_elements.append(Paragraph(f"Nº Hoja: {sheet_number}", sheet_number_style))
        all_elements.append(Spacer(1, 5*mm))
        
        # Data tables
        all_elements.append(Paragraph('DATOS DEL SERVICIO', section_title))
        
        data = [
            ['Titular:', user.get('full_name', ''), 'DNI/CIF:', user.get('dni_cif', '')],
            ['Conductor:', driver_name, 'Licencia:', user.get('license_number', '')],
            ['Vehículo:', f"{user.get('vehicle_brand', '')} {user.get('vehicle_model', '')}", 'Matrícula:', user.get('vehicle_plate', '')],
        ]
        
        info_table = Table(data, colWidths=[25*mm, 60*mm, 25*mm, 60*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#57534E')),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#57534E')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4*mm),
        ]))
        all_elements.append(info_table)
        
        all_elements.append(Paragraph('DETALLES DEL SERVICIO', section_title))
        
        contractor_info = []
        if sheet.get('contractor_phone'):
            contractor_info.append(f"Tel: {sheet['contractor_phone']}")
        if sheet.get('contractor_email'):
            contractor_info.append(f"Email: {sheet['contractor_email']}")
        
        service_data = [
            ['Contratante:', ' | '.join(contractor_info) if contractor_info else '-'],
            ['Precontratado:', f"{sheet.get('prebooked_date', '')} en {sheet.get('prebooked_locality', '')}"],
            ['Recogida:', f"{sheet.get('pickup_type', '')} - {sheet.get('pickup_address', '') or 'Aeropuerto de Asturias'}"],
            ['Fecha/Hora:', sheet.get('pickup_datetime', '')],
        ]
        
        if sheet.get('flight_number'):
            service_data.append(['Nº Vuelo:', sheet['flight_number']])
        
        service_data.append(['Destino:', sheet.get('destination', '')])
        
        service_table = Table(service_data, colWidths=[30*mm, 140*mm])
        service_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#57534E')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ]))
        all_elements.append(service_table)
        
        # Status if annulled
        if sheet.get('status') == 'ANNULLED':
            annul_style = ParagraphStyle(
                'Annulled',
                parent=styles['Normal'],
                fontSize=12,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#DC2626'),
                alignment=TA_CENTER
            )
            all_elements.append(Spacer(1, 5*mm))
            all_elements.append(Paragraph('** HOJA ANULADA **', annul_style))
        
        # Legend
        all_elements.append(Spacer(1, 10*mm))
        all_elements.append(Paragraph(config.get('legend_text', ''), legend_style))
    
    doc.build(all_elements)
    buffer.seek(0)
    return buffer
