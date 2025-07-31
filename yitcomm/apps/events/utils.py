# utils.py - Utility functions for ticket generation and other helpers
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import inch
from io import BytesIO
import qrcode
from PIL import Image as PILImage
from django.conf import settings
import os


def generate_ticket_pdf(ticket):
    """Generate PDF ticket for an event registration"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#1f2937'),
        alignment=1  # Center alignment
    )

    story = []

    # Title
    title = Paragraph("EVENT TICKET", title_style)
    story.append(title)
    story.append(Spacer(1, 20))

    # Event information table
    event = ticket.registration.event
    user = ticket.registration.user

    event_data = [
        ['Event:', event.title],
        ['Date:', event.start_time.strftime('%B %d, %Y')],
        ['Time:', f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}"],
        ['Location:', event.location if not event.is_online else 'Online Event'],
        ['Ticket Number:', ticket.ticket_number],
        ['Attendee:', user.get_full_name()],
        ['Email:', user.email],
    ]

    if event.event_type == 'paid':
        event_data.append(['Amount Paid:', f"TZS {ticket.registration.amount_paid:,.2f}"])

    if event.is_online and event.meeting_url:
        event_data.append(['Meeting URL:', event.meeting_url])

    # Create table
    event_table = Table(event_data, colWidths=[2 * inch, 4 * inch])
    event_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
    ]))

    story.append(event_table)
    story.append(Spacer(1, 30))

    # QR Code
    if ticket.qr_code_data:
        qr_title = Paragraph("<b>QR Code for Check-in:</b>", styles['Heading3'])
        story.append(qr_title)
        story.append(Spacer(1, 10))

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(ticket.qr_code_data)
        qr.make(fit=True)

        qr_image = qr.make_image(fill_color="black", back_color="white")

        # Save QR code to temporary buffer
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        # Add QR code to PDF
        qr_img = Image(qr_buffer, 2 * inch, 2 * inch)
        qr_img.hAlign = 'CENTER'
        story.append(qr_img)
        story.append(Spacer(1, 20))

    # Important notes
    notes_title = Paragraph("<b>Important Notes:</b>", styles['Heading3'])
    story.append(notes_title)
    story.append(Spacer(1, 10))

    notes_text = """
    • Please bring this ticket (digital or printed) to the event<br/>
    • Arrive 15 minutes early for check-in<br/>
    • This ticket is non-transferable<br/>
    • For support, contact the event organizer<br/>
    • Keep your ticket safe - lost tickets cannot be replaced
    """

    notes = Paragraph(notes_text, styles['Normal'])
    story.append(notes)
    story.append(Spacer(1, 30))

    # Footer
    footer_text = f"""
    <i>Generated on {ticket.issued_date.strftime('%B %d, %Y at %I:%M %p')}<br/>
    Event ID: {event.id} | Ticket ID: {ticket.id}</i>
    """
    footer = Paragraph(footer_text, styles['Normal'])
    story.append(footer)

    # Build PDF
    doc.build(story)
    buffer.seek(0)

    return buffer


def format_tanzanian_phone(phone):
    """Format phone number for Tanzania"""
    if not phone:
        return ''

    # Remove any non-digit characters
    phone = ''.join(filter(str.isdigit, str(phone)))

    # Handle different formats
    if phone.startswith('255'):
        # Convert from 255XXXXXXXXX to 07XXXXXXXX
        phone = '0' + phone[3:]
    elif phone.startswith('7') and len(phone) == 9:
        # Convert from 7XXXXXXXX to 07XXXXXXXX
        phone = '0' + phone
    elif not phone.startswith('0'):
        # Add leading zero if missing
        phone = '0' + phone

    return phone if len(phone) == 10 and phone.startswith('07') else phone


def generate_ticket_number(event_id, registration_id):
    """Generate a unique ticket number"""
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    reg_short = str(registration_id).replace('-', '')[:8].upper()
    return f"TKT-{event_id}-{date_str}-{reg_short}"


def send_email_notification(user_email, subject, message, html_message=None):
    """Send email notification to user"""
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send email to {user_email}: {str(e)}")
        return False

