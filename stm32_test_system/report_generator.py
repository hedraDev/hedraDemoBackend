"""
PDF Rapor Oluşturma Modülü
Test sonuçlarını PDF formatında raporlar
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class ReportGenerator:
    """Test raporlarını PDF olarak oluşturan sınıf"""

    def __init__(self, output_dir: str = "./reports"):
        """
        Args:
            output_dir: Raporların kaydedileceği dizin
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Özel stiller oluştur"""
        # Başlık stili
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1976D2'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Alt başlık stili
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2196F3'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))

        # Normal metin stili
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            fontName='Helvetica'
        ))

        # Başarı stili
        self.styles.add(ParagraphStyle(
            name='Success',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.green,
            fontName='Helvetica-Bold'
        ))

        # Hata stili
        self.styles.add(ParagraphStyle(
            name='Error',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.red,
            fontName='Helvetica-Bold'
        ))

    def generate_test_report(self, test_data: Dict, logo_path: str = None) -> str:
        """
        Tek bir test için rapor oluştur

        Args:
            test_data: Test verileri
            logo_path: Logo dosyası yolu (opsiyonel)

        Returns:
            Oluşturulan PDF dosyasının yolu
        """
        device_uuid = test_data.get('device_uuid', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_report_{device_uuid}_{timestamp}.pdf"
        filepath = self.output_dir / filename

        # PDF oluştur
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # İçerik listesi
        story = []

        # Logo ekle (varsa)
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=3*inch, height=1.5*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.5*inch))
            except:
                pass

        # Başlık
        title = Paragraph("STM32L011 CİHAZ TEST RAPORU", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.3*inch))

        # Genel Bilgiler
        story.append(Paragraph("Genel Bilgiler", self.styles['CustomHeading']))

        general_info = [
            ['Cihaz UUID:', device_uuid],
            ['Test Tarihi:', test_data.get('start_time', 'N/A')[:19]],
            ['Test Durumu:', test_data.get('status', 'N/A').upper()],
            ['Toplam Süre:', f"{test_data.get('total_duration', 0):.2f} saniye"]
        ]

        general_table = Table(general_info, colWidths=[4*cm, 12*cm])
        general_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(general_table)
        story.append(Spacer(1, 0.3*inch))

        # Aşama Süreleri
        if 'stage_durations' in test_data:
            story.append(Paragraph("Aşama Süreleri", self.styles['CustomHeading']))

            stage_data = [['Aşama', 'Süre (sn)']]
            for stage, duration in test_data['stage_durations'].items():
                stage_data.append([stage.replace('_', ' ').title(), f"{duration:.3f}"])

            stage_table = Table(stage_data, colWidths=[12*cm, 4*cm])
            stage_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(stage_table)
            story.append(Spacer(1, 0.3*inch))

        # Ölçüm Sonuçları
        if 'measurements' in test_data and test_data['measurements']:
            story.append(Paragraph("Ölçüm Sonuçları", self.styles['CustomHeading']))

            measurement_data = [['Zaman', 'Solution', 'Raw Değer', 'Sıcaklık (°C)']]
            for m in test_data['measurements']:
                timestamp_str = m.get('timestamp', '')[:19]
                solution = f"Solution {m.get('solution', 'N/A')}"
                raw = str(m.get('raw', 'N/A'))
                temp = f"{m.get('temperature', 'N/A')}"

                measurement_data.append([timestamp_str, solution, raw, temp])

            meas_table = Table(measurement_data, colWidths=[5*cm, 3*cm, 4*cm, 4*cm])
            meas_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(meas_table)
            story.append(Spacer(1, 0.3*inch))

        # Fotoğraf (varsa)
        if 'photo' in test_data:
            photo_path = Path('./photos') / test_data['photo']
            if photo_path.exists():
                story.append(Paragraph("Cihaz Fotoğrafı", self.styles['CustomHeading']))
                try:
                    photo = Image(str(photo_path), width=4*inch, height=3*inch)
                    photo.hAlign = 'CENTER'
                    story.append(photo)
                    story.append(Spacer(1, 0.3*inch))
                except:
                    pass

        # Sonuç
        status = test_data.get('status', 'unknown')
        if status == 'completed':
            result_text = "✓ TEST BAŞARILI"
            result_style = 'Success'
        else:
            result_text = "✗ TEST BAŞARISIZ"
            result_style = 'Error'

        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(result_text, self.styles[result_style]))

        # Footer
        story.append(Spacer(1, 0.5*inch))
        footer_text = f"Rapor Oluşturma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        story.append(Paragraph(footer_text, self.styles['CustomBody']))

        # PDF'i oluştur
        doc.build(story)

        return str(filepath)

    def generate_summary_report(self, test_list: List[Dict], statistics: Dict,
                               logo_path: str = None) -> str:
        """
        Özet rapor oluştur (birden fazla test)

        Args:
            test_list: Test verileri listesi
            statistics: İstatistik verileri
            logo_path: Logo dosyası yolu (opsiyonel)

        Returns:
            Oluşturulan PDF dosyasının yolu
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"summary_report_{timestamp}.pdf"
        filepath = self.output_dir / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        story = []

        # Logo
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=3*inch, height=1.5*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.5*inch))
            except:
                pass

        # Başlık
        title = Paragraph("TEST SİSTEMİ ÖZET RAPORU", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.3*inch))

        # İstatistikler
        story.append(Paragraph("Genel İstatistikler", self.styles['CustomHeading']))

        stats_data = [
            ['Toplam Test:', str(statistics.get('total_tests', 0))],
            ['Başarılı Test:', str(statistics.get('successful_tests', 0))],
            ['Başarısız Test:', str(statistics.get('failed_tests', 0))],
            ['Başarı Oranı:', f"{statistics.get('success_rate', 0):.1f}%"],
            ['Ortalama Süre:', f"{statistics.get('avg_duration', 0):.2f} sn"],
            ['Dönem:', f"{statistics.get('period_days', 0)} gün"]
        ]

        stats_table = Table(stats_data, colWidths=[6*cm, 10*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.4*inch))

        # Test Listesi
        if test_list:
            story.append(Paragraph("Test Listesi", self.styles['CustomHeading']))

            test_table_data = [['Tarih', 'UUID', 'Durum', 'Süre (sn)']]
            for test in test_list[:20]:  # İlk 20 test
                date = test.get('start_time', '')[:19]
                uuid = test.get('device_uuid', 'N/A')[:16] + '...'
                status = '✓' if test.get('status') == 'completed' else '✗'
                duration = f"{test.get('total_duration', 0):.2f}"

                test_table_data.append([date, uuid, status, duration])

            test_table = Table(test_table_data, colWidths=[5*cm, 5*cm, 3*cm, 3*cm])
            test_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(test_table)

        # Footer
        story.append(Spacer(1, 0.5*inch))
        footer_text = f"Rapor Oluşturma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        story.append(Paragraph(footer_text, self.styles['CustomBody']))

        doc.build(story)

        return str(filepath)
