"""
RutasFast - PDF Generator (Formato oficial/serio)
Genera PDFs A4 con identidad FAST para inspección
"""
import io
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from datetime import datetime


def get_logo_path():
    """Get path to logo file"""
    logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
    if os.path.exists(logo_path):
        return logo_path
    return None


def get_logo_image(max_width_mm=35, max_height_mm=25):
    """
    Get logo Image maintaining aspect ratio.
    Returns None if logo not found.
    """
    logo_path = get_logo_path()
    if not logo_path:
        return None
    
    try:
        from PIL import Image as PILImage
        
        # Get original dimensions
        with PILImage.open(logo_path) as img:
            orig_width, orig_height = img.size
        
        # Calculate aspect ratio
        aspect = orig_width / orig_height
        
        # Calculate dimensions maintaining aspect ratio
        # Try fitting to max width first
        width = max_width_mm * mm
        height = width / aspect
        
        # If height exceeds max, fit to height instead
        if height > max_height_mm * mm:
            height = max_height_mm * mm
            width = height * aspect
        
        return Image(logo_path, width=width, height=height)
    except Exception as e:
        print(f"Error loading logo: {e}")
        return None


class AnnulledWatermark(canvas.Canvas):
    """Canvas that adds ANULADA watermark for annulled sheets"""
    
    def __init__(self, *args, is_annulled=False, **kwargs):
        self.is_annulled = is_annulled
        super().__init__(*args, **kwargs)
    
    def showPage(self):
        if self.is_annulled:
            self.saveState()
            self.setFont('Helvetica-Bold', 60)
            self.setFillColor(colors.Color(0.9, 0.1, 0.1, alpha=0.3))
            self.translate(A4[0]/2, A4[1]/2)
            self.rotate(45)
            self.drawCentredString(0, 0, "ANULADA")
            self.restoreState()
        super().showPage()


def generate_route_sheet_pdf(sheet: dict, user: dict, config: dict, driver_name: str) -> io.BytesIO:
    """Generate a single route sheet PDF with official format"""
    buffer = io.BytesIO()
    
    is_annulled = sheet.get('status') == 'ANNULLED'
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=12*mm,
        bottomMargin=15*mm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=2*mm,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a1a1a')
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#444444'),
        spaceAfter=1*mm
    )
    
    section_header = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#701111'),
        spaceBefore=4*mm,
        spaceAfter=2*mm,
        borderPadding=2*mm,
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica-Bold'
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1a1a1a')
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#888888'),
        alignment=TA_CENTER
    )
    
    sheet_number_style = ParagraphStyle(
        'SheetNumber',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#701111'),
        alignment=TA_RIGHT
    )
    
    elements = []
    
    # ============== HEADER ==============
    # Logo + Title side by side
    logo = get_logo_image(max_width_mm=35, max_height_mm=25)
    
    header_left = []
    if logo:
        header_left.append(logo)
    else:
        # Fallback to text
        header_left.append(Paragraph('<font color="#701111" size="24"><b>FAST</b></font>', styles['Normal']))
    
    # Sheet number
    sheet_number = f"{sheet['seq_number']:03d}/{sheet['year']}"
    
    header_right = []
    header_right.append(Paragraph(config.get('header_title', 'HOJA DE RUTA'), title_style))
    header_right.append(Paragraph(config.get('header_line1', ''), subtitle_style))
    header_right.append(Paragraph(config.get('header_line2', ''), subtitle_style))
    
    # Annulled stamp in header
    if is_annulled:
        header_right.append(Spacer(1, 2*mm))
        annul_stamp = ParagraphStyle('AnnulStamp', fontSize=14, fontName='Helvetica-Bold', 
                                      textColor=colors.white, alignment=TA_CENTER,
                                      backColor=colors.HexColor('#DC2626'))
        header_right.append(Paragraph('*** HOJA ANULADA ***', annul_stamp))
    
    header_table = Table([
        [header_left, header_right]
    ], colWidths=[45*mm, 130*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
    ]))
    elements.append(header_table)
    
    # Horizontal line
    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#701111')))
    elements.append(Spacer(1, 2*mm))
    
    # Sheet number prominent
    elements.append(Paragraph(f"Nº de Hoja: <b>{sheet_number}</b>", sheet_number_style))
    elements.append(Spacer(1, 4*mm))
    
    # ============== DATOS DEL TITULAR ==============
    elements.append(Paragraph('DATOS DEL TITULAR Y VEHÍCULO', section_header))
    
    titular_data = [
        ['Titular:', user.get('full_name', '-'), 'DNI/CIF:', user.get('dni_cif', '-')],
        ['Nº Licencia:', user.get('license_number', '-'), 'Concejo:', user.get('license_council', '-')],
        ['Teléfono:', user.get('phone', '-'), '', ''],
        ['Vehículo:', f"{user.get('vehicle_brand', '')} {user.get('vehicle_model', '')}", 'Matrícula:', user.get('vehicle_plate', '-')],
    ]
    
    if driver_name != "Titular":
        titular_data.append(['Conductor:', driver_name, '', ''])
    
    titular_table = Table(titular_data, colWidths=[25*mm, 60*mm, 25*mm, 60*mm])
    titular_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
        ('TEXTCOLOR', (3, 0), (3, -1), colors.HexColor('#1a1a1a')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e5e5')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
    ]))
    elements.append(titular_table)
    
    # ============== DATOS DE CONTRATACIÓN ==============
    elements.append(Paragraph('DATOS DE CONTRATACIÓN', section_header))
    
    contractor_contact = []
    if sheet.get('contractor_phone'):
        contractor_contact.append(f"Tel: {sheet['contractor_phone']}")
    if sheet.get('contractor_email'):
        contractor_contact.append(f"Email: {sheet['contractor_email']}")
    contractor_str = ' | '.join(contractor_contact) if contractor_contact else '-'
    
    contract_data = [
        ['Contratante:', contractor_str],
        ['Fecha precontratación:', sheet.get('prebooked_date', '-')],
        ['Localidad precontratación:', sheet.get('prebooked_locality', '-')],
    ]
    
    contract_table = Table(contract_data, colWidths=[45*mm, 125*mm])
    contract_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e5e5')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
    ]))
    elements.append(contract_table)
    
    # ============== DATOS DEL SERVICIO ==============
    elements.append(Paragraph('DATOS DEL SERVICIO', section_header))
    
    # Pickup location
    if sheet.get('pickup_type') == 'AIRPORT':
        pickup_location = f"Aeropuerto de Asturias - Vuelo: {sheet.get('flight_number', '-')}"
    else:
        pickup_location = sheet.get('pickup_address', '-')
    
    # Format datetime
    pickup_dt = sheet.get('pickup_datetime', '-')
    if pickup_dt and pickup_dt != '-':
        try:
            if isinstance(pickup_dt, str):
                dt = datetime.fromisoformat(pickup_dt.replace('Z', '+00:00'))
                pickup_dt = dt.strftime('%d/%m/%Y %H:%M')
        except:
            pass
    
    service_data = [
        ['Tipo de recogida:', 'Aeropuerto' if sheet.get('pickup_type') == 'AIRPORT' else 'Otra dirección'],
        ['Lugar de recogida:', pickup_location],
        ['Fecha y hora:', pickup_dt],
        ['Destino:', sheet.get('destination', '-')],
    ]
    
    service_table = Table(service_data, colWidths=[45*mm, 125*mm])
    service_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e5e5')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
    ]))
    elements.append(service_table)
    
    # ============== ANNULLED INFO ==============
    if is_annulled:
        elements.append(Spacer(1, 4*mm))
        annul_info = [
            ['MOTIVO DE ANULACIÓN:', sheet.get('annul_reason', 'No especificado')],
        ]
        if sheet.get('annulled_at'):
            annul_date = sheet['annulled_at']
            if isinstance(annul_date, datetime):
                annul_date = annul_date.strftime('%d/%m/%Y %H:%M')
            annul_info.append(['Fecha de anulación:', str(annul_date)])
        
        annul_table = Table(annul_info, colWidths=[45*mm, 125*mm])
        annul_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#DC2626')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEE2E2')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#DC2626')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
            ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ]))
        elements.append(annul_table)
    
    # ============== FOOTER ==============
    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc')))
    elements.append(Spacer(1, 3*mm))
    
    # Legend
    legend_text = config.get('legend_text', 'Es obligatorio conservar los registros durante 12 meses desde la fecha de recogida del servicio.')
    elements.append(Paragraph(legend_text, footer_style))
    elements.append(Spacer(1, 2*mm))
    
    # Organization
    elements.append(Paragraph('RutasFast / Federación Asturiana Sindical del Taxi (FAST)', footer_style))
    elements.append(Spacer(1, 3*mm))
    
    # Large sheet number at bottom
    final_number = ParagraphStyle('FinalNumber', fontSize=16, fontName='Helvetica-Bold',
                                   textColor=colors.HexColor('#701111'), alignment=TA_CENTER)
    elements.append(Paragraph(f"Hoja Nº {sheet_number}", final_number))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_multi_sheet_pdf(sheets: list, user: dict, config: dict, drivers_map: dict) -> io.BytesIO:
    """Generate PDF with multiple route sheets (one per page)"""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=12*mm,
        bottomMargin=15*mm
    )
    
    all_elements = []
    
    for i, sheet in enumerate(sheets):
        if i > 0:
            all_elements.append(PageBreak())
        
        driver_name = "Titular"
        if sheet.get("conductor_driver_id"):
            driver_name = drivers_map.get(sheet["conductor_driver_id"], "Titular")
        
        # Generate single sheet content inline
        single_buffer = generate_route_sheet_pdf(sheet, user, config, driver_name)
        
        # For multi-page, we rebuild inline (simplified)
        # This duplicates some code but ensures consistency
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', fontSize=18, alignment=TA_CENTER,
                                      fontName='Helvetica-Bold', textColor=colors.HexColor('#1a1a1a'))
        subtitle_style = ParagraphStyle('Subtitle', fontSize=10, alignment=TA_CENTER,
                                         textColor=colors.HexColor('#444444'))
        section_header = ParagraphStyle('SectionHeader', fontSize=11, fontName='Helvetica-Bold',
                                         textColor=colors.HexColor('#701111'), spaceBefore=4*mm, spaceAfter=2*mm)
        footer_style = ParagraphStyle('Footer', fontSize=8, textColor=colors.HexColor('#888888'), alignment=TA_CENTER)
        sheet_number_style = ParagraphStyle('SheetNumber', fontSize=14, fontName='Helvetica-Bold',
                                             textColor=colors.HexColor('#701111'), alignment=TA_RIGHT)
        
        is_annulled = sheet.get('status') == 'ANNULLED'
        sheet_number = f"{sheet['seq_number']:03d}/{sheet['year']}"
        
        # Header
        logo = get_logo_image(max_width_mm=30, max_height_mm=20)
        if logo:
            all_elements.append(logo)
        else:
            all_elements.append(Paragraph('<font color="#701111" size="24"><b>FAST</b></font>', styles['Normal']))
        
        all_elements.append(Paragraph(config.get('header_title', 'HOJA DE RUTA'), title_style))
        all_elements.append(Paragraph(config.get('header_line1', ''), subtitle_style))
        all_elements.append(Paragraph(config.get('header_line2', ''), subtitle_style))
        
        if is_annulled:
            all_elements.append(Spacer(1, 2*mm))
            annul_p = ParagraphStyle('Annul', fontSize=12, fontName='Helvetica-Bold',
                                      textColor=colors.HexColor('#DC2626'), alignment=TA_CENTER)
            all_elements.append(Paragraph('*** HOJA ANULADA ***', annul_p))
        
        all_elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#701111')))
        all_elements.append(Paragraph(f"Nº de Hoja: <b>{sheet_number}</b>", sheet_number_style))
        all_elements.append(Spacer(1, 3*mm))
        
        # Compact data for multi-sheet
        all_elements.append(Paragraph('TITULAR Y VEHÍCULO', section_header))
        data1 = [
            ['Titular:', user.get('full_name', '-'), 'Licencia:', user.get('license_number', '-')],
            ['Vehículo:', f"{user.get('vehicle_brand', '')} {user.get('vehicle_model', '')}", 'Matrícula:', user.get('vehicle_plate', '-')],
        ]
        if driver_name != "Titular":
            data1.append(['Conductor:', driver_name, '', ''])
        
        t1 = Table(data1, colWidths=[22*mm, 55*mm, 22*mm, 55*mm])
        t1.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ]))
        all_elements.append(t1)
        
        all_elements.append(Paragraph('SERVICIO', section_header))
        
        pickup_loc = f"Aeropuerto - {sheet.get('flight_number', '')}" if sheet.get('pickup_type') == 'AIRPORT' else sheet.get('pickup_address', '-')
        
        data2 = [
            ['Contratante:', sheet.get('contractor_phone') or sheet.get('contractor_email') or '-'],
            ['Recogida:', pickup_loc],
            ['Fecha/Hora:', sheet.get('pickup_datetime', '-')],
            ['Destino:', sheet.get('destination', '-')],
        ]
        
        t2 = Table(data2, colWidths=[30*mm, 125*mm])
        t2.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ]))
        all_elements.append(t2)
        
        # Footer
        all_elements.append(Spacer(1, 5*mm))
        all_elements.append(Paragraph(config.get('legend_text', ''), footer_style))
        all_elements.append(Paragraph('RutasFast / FAST', footer_style))
        
        final_num = ParagraphStyle('Num', fontSize=14, fontName='Helvetica-Bold',
                                    textColor=colors.HexColor('#701111'), alignment=TA_CENTER)
        all_elements.append(Paragraph(f"Hoja Nº {sheet_number}", final_num))
    
    doc.build(all_elements)
    buffer.seek(0)
    return buffer
