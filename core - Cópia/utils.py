from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from django.core.files.base import ContentFile
from io import BytesIO
from datetime import datetime
import os

def gerar_recibo_pagamento(pagamento):
    """Gera um recibo PDF para um pagamento aprovado"""
    from .models import ConfiguracaoEscola
    from django.conf import settings
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    config = ConfiguracaoEscola.objects.first()
    
    logo_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'core', 'images', 'siga-logo.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=4*cm, height=1.5*cm)
        elements.append(img)
        elements.append(Spacer(1, 0.5*cm))
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    elements.append(Paragraph(f"RECIBO DE PAGAMENTO", title_style))
    elements.append(Paragraph(f"Nº {pagamento.id:06d}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    data = [
        ['Escola:', pagamento.subscricao.nome_escola],
        ['Plano:', pagamento.get_plano_escolhido_display()],
        ['Valor Pago:', f"{pagamento.valor:,.2f} Kz"],
        ['Data do Pagamento:', pagamento.data_pagamento.strftime('%d/%m/%Y')],
        ['Referência:', pagamento.numero_referencia or 'N/A'],
        ['Aprovado Por:', pagamento.aprovado_por.get_full_name() or pagamento.aprovado_por.username],
        ['Data de Aprovação:', pagamento.data_aprovacao.strftime('%d/%m/%Y %H:%M')],
        ['Nova Data de Expiração:', pagamento.subscricao.data_expiracao.strftime('%d/%m/%Y')],
    ]
    
    table = Table(data, colWidths=[6*cm, 12*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e5e7eb')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 1*cm))
    
    elements.append(Paragraph("Este recibo confirma o pagamento e renovação da subscrição do SIGA.", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("SIGA v1.0.0 - Sistema Integral de Gestão Académica", footer_style))
    elements.append(Paragraph("Desenvolvido por Eng. Osvaldo Queta", footer_style))
    
    doc.build(elements)
    
    pdf_content = ContentFile(buffer.getvalue())
    filename = f'recibo_pagamento_{pagamento.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    pagamento.recibo_pdf.save(filename, pdf_content, save=False)
    
    return filename
