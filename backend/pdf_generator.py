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
from zoneinfo import ZoneInfo

# Timezone constants
MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")


def _coerce_datetime(value):
    """Accepts datetime or ISO string; returns aware datetime in UTC if possible, else None."""
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    else:
        return None

    # If naive, assume UTC (Mongo sometimes returns naive depending on driver/config)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt


def format_date_es(value) -> str:
    """Format date to dd/mm/aaaa in Europe/Madrid timezone"""
    dt = _coerce_datetime(value)
    if not dt:
        # value could already be "YYYY-MM-DD" string, try parse minimal
        if isinstance(value, str) and len(value) >= 10:
            try:
                dt2 = datetime.fromisoformat(value[:10])
                return dt2.strftime("%d/%m/%Y")
            except Exception:
                pass
        return str(value) if value else "-"
    local = dt.astimezone(MADRID_TZ)
    return local.strftime("%d/%m/%Y")


def format_datetime_es(value) -> str:
    """Format datetime to dd/mm/aaaa HH:MM in Europe/Madrid timezone"""
    dt = _coerce_datetime(value)
    if not dt:
        return str(value) if value else "-"
    local = dt.astimezone(MADRID_TZ)
    return local.strftime("%d/%m/%Y %H:%M")


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
    
    # Build vehicle description
    vehicle_desc = f"{user.get('vehicle_brand', '')} {user.get('vehicle_model', '')}".strip() or '-'
    vehicle_license = user.get('vehicle_license_number', '')
    
    titular_data = [
        ['Titular:', user.get('full_name', '-'), 'DNI/CIF:', user.get('dni_cif', '-')],
        ['Nº Licencia:', user.get('license_number', '-'), 'Concejo:', user.get('license_council', '-')],
        ['Teléfono:', user.get('phone', '-'), '', ''],
        ['Vehículo:', vehicle_desc, 'Matrícula:', user.get('vehicle_plate', '-')],
    ]
    
    # Add vehicle license number if present (useful for inspections)
    if vehicle_license:
        titular_data.append(['Lic. Vehículo:', vehicle_license, '', ''])
    
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
        ['Fecha precontratación:', format_datetime_es(sheet.get('prebooked_date'))],
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
    
    # Format datetime using helper
    pickup_dt = format_datetime_es(sheet.get('pickup_datetime'))
    
    service_data = [
        ['Tipo de recogida:', 'Aeropuerto' if sheet.get('pickup_type') == 'AIRPORT' else 'Otra dirección'],
        ['Lugar de recogida:', pickup_location],
        ['Fecha y hora:', pickup_dt],
        ['Destino:', sheet.get('destination', '-')],
        ['Pasajero(s):', sheet.get('passenger_info', '-')],
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
            annul_info.append(['Fecha de anulación:', format_datetime_es(sheet.get('annulled_at'))])
        
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
    """Generate PDF with multiple route sheets (one per page) - Same format as single sheet"""
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
    styles = getSampleStyleSheet()
    
    # Custom styles (same as single PDF)
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
    
    for i, sheet in enumerate(sheets):
        if i > 0:
            all_elements.append(PageBreak())
        
        driver_name = "Titular"
        if sheet.get("conductor_driver_id"):
            driver_name = drivers_map.get(sheet["conductor_driver_id"], "Titular")
        
        is_annulled = sheet.get('status') == 'ANNULLED'
        sheet_number = f"{sheet['seq_number']:03d}/{sheet['year']}"
        
        # ============== HEADER ==============
        logo = get_logo_image(max_width_mm=35, max_height_mm=25)
        
        header_left = []
        if logo:
            header_left.append(logo)
        else:
            header_left.append(Paragraph('<font color="#701111" size="24"><b>FAST</b></font>', styles['Normal']))
        
        header_right = []
        header_right.append(Paragraph(config.get('header_title', 'HOJA DE RUTA'), title_style))
        header_right.append(Paragraph(config.get('header_line1', ''), subtitle_style))
        header_right.append(Paragraph(config.get('header_line2', ''), subtitle_style))
        
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
        all_elements.append(header_table)
        
        # Horizontal line
        all_elements.append(Spacer(1, 3*mm))
        all_elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#701111')))
        all_elements.append(Spacer(1, 2*mm))
        
        # Sheet number prominent
        all_elements.append(Paragraph(f"Nº de Hoja: <b>{sheet_number}</b>", sheet_number_style))
        all_elements.append(Spacer(1, 4*mm))
        
        # ============== DATOS DEL TITULAR ==============
        all_elements.append(Paragraph('DATOS DEL TITULAR Y VEHÍCULO', section_header))
        
        vehicle_desc = f"{user.get('vehicle_brand', '')} {user.get('vehicle_model', '')}".strip() or '-'
        vehicle_license = user.get('vehicle_license_number', '')
        
        titular_data = [
            ['Titular:', user.get('full_name', '-'), 'DNI/CIF:', user.get('dni_cif', '-')],
            ['Nº Licencia:', user.get('license_number', '-'), 'Concejo:', user.get('license_council', '-')],
            ['Teléfono:', user.get('phone', '-'), '', ''],
            ['Vehículo:', vehicle_desc, 'Matrícula:', user.get('vehicle_plate', '-')],
        ]
        
        if vehicle_license:
            titular_data.append(['Lic. Vehículo:', vehicle_license, '', ''])
        
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
        all_elements.append(titular_table)
        
        # ============== DATOS DE CONTRATACIÓN ==============
        all_elements.append(Paragraph('DATOS DE CONTRATACIÓN', section_header))
        
        contractor_contact = []
        if sheet.get('contractor_phone'):
            contractor_contact.append(f"Tel: {sheet['contractor_phone']}")
        if sheet.get('contractor_email'):
            contractor_contact.append(f"Email: {sheet['contractor_email']}")
        contractor_str = ' | '.join(contractor_contact) if contractor_contact else '-'
        
        contract_data = [
            ['Contratante:', contractor_str],
            ['Fecha precontratación:', format_datetime_es(sheet.get('prebooked_date'))],
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
        all_elements.append(contract_table)
        
        # ============== DATOS DEL SERVICIO ==============
        all_elements.append(Paragraph('DATOS DEL SERVICIO', section_header))
        
        if sheet.get('pickup_type') == 'AIRPORT':
            pickup_location = f"Aeropuerto de Asturias - Vuelo: {sheet.get('flight_number', '-')}"
        else:
            pickup_location = sheet.get('pickup_address', '-')
        
        pickup_dt = format_datetime_es(sheet.get('pickup_datetime'))
        
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
        all_elements.append(service_table)
        
        # ============== ANNULLED INFO ==============
        if is_annulled:
            all_elements.append(Spacer(1, 4*mm))
            annul_info = [
                ['MOTIVO DE ANULACIÓN:', sheet.get('annul_reason', 'No especificado')],
            ]
            if sheet.get('annulled_at'):
                annul_info.append(['Fecha de anulación:', format_datetime_es(sheet.get('annulled_at'))])
            
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
            all_elements.append(annul_table)
        
        # ============== FOOTER ==============
        all_elements.append(Spacer(1, 10*mm))
        all_elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc')))
        all_elements.append(Spacer(1, 3*mm))
        
        legend_text = config.get('legend_text', 'Es obligatorio conservar los registros durante 12 meses desde la fecha de recogida del servicio.')
        all_elements.append(Paragraph(legend_text, footer_style))
        all_elements.append(Spacer(1, 2*mm))
        
        all_elements.append(Paragraph('RutasFast / Federación Asturiana Sindical del Taxi (FAST)', footer_style))
        all_elements.append(Spacer(1, 3*mm))
        
        final_number = ParagraphStyle('FinalNumber', fontSize=16, fontName='Helvetica-Bold',
                                       textColor=colors.HexColor('#701111'), alignment=TA_CENTER)
        all_elements.append(Paragraph(f"Hoja Nº {sheet_number}", final_number))
    
    doc.build(all_elements)
    buffer.seek(0)
    return buffer
