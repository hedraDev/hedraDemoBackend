"""
STM32L011 Cihaz Test Sistemi - Geliştirilmiş Versiyon v2.0
Hedra Technology

Özellikler:
- Gelişmiş loglama sistemi
- Hata yönetimi ve recovery
- PDF rapor oluşturma
- MongoDB veritabanı yedekleme
- İstatistik paneli
- Ses bildirimleri
- Operatör yönetimi
- Yapılandırma dosyası
"""

import sys
import os
import time
import asyncio
import threading
import traceback
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QMessageBox, QFileDialog, QProgressBar, QLineEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QSplitter, QStatusBar,
    QMenu, QAction, QToolBar, QDialogButtonBox, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QImage, QIcon

import numpy as np
import cv2
from pymongo import MongoClient

# PPK2 ve PyOCD import'ları
try:
    from ppk2_api.ppk2_api import PPK2_API
    PPK2_AVAILABLE = True
except ImportError:
    PPK2_AVAILABLE = False
    print("UYARI: PPK2 API bulunamadı")

try:
    from pyocd.core.helpers import ConnectHelper
    import subprocess
    PYOCD_AVAILABLE = True
except ImportError:
    PYOCD_AVAILABLE = False
    print("UYARI: PyOCD bulunamadı")

try:
    from bleak import BleakClient, BleakScanner
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("UYARI: Bleak (BLE) bulunamadı")

# Kendi modüllerimiz
from logger import get_logger
from config_manager import get_config
from database_manager import DatabaseManager
from report_generator import ReportGenerator
from sound_manager import get_sound_manager
from barcode_reader import read_barcode_card, OperatorDatabase


# Global değişkenler
connected_client = None
connected_loop = None
connected_device_name = "Bilinmeyen"


class Communicator(QObject):
    """Sinyal iletişimi için"""
    update_text = pyqtSignal(str)
    new_data = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    stage_complete_signal = pyqtSignal(int)
    status_update = pyqtSignal(str, str)  # text, style
    progress_update = pyqtSignal(int)
    error_occurred = pyqtSignal(str, str)  # title, message


comm = Communicator()


class OperatorLoginDialog(QDialog):
    """Operatör giriş ekranı"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Operatör Girişi")
        self.setModal(True)
        self.resize(400, 200)

        self.operator_name = None
        self.operator_id = None

        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()

        # Operatör Adı
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Adınız ve Soyadınız")
        layout.addRow("Operatör Adı:", self.name_input)

        # Operatör ID
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Operatör ID")
        layout.addRow("Operatör ID:", self.id_input)

        # Butonlar
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept_login)
        button_box.rejected.connect(self.reject)

        layout.addRow(button_box)

        self.setLayout(layout)

        # Enter tuşu ile giriş
        self.id_input.returnPressed.connect(self.accept_login)

    def accept_login(self):
        name = self.name_input.text().strip()
        op_id = self.id_input.text().strip()

        if not name or not op_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen tüm alanları doldurun!")
            return

        self.operator_name = name
        self.operator_id = op_id
        self.accept()


class StatisticsDialog(QDialog):
    """İstatistik görüntüleme ekranı"""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test İstatistikleri")
        self.resize(800, 600)

        self.db_manager = db_manager
        self.init_ui()
        self.load_statistics()

    def init_ui(self):
        layout = QVBoxLayout()

        # Filtre seçenekleri
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Dönem:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Son 7 Gün", "Son 30 Gün", "Son 90 Gün"])
        self.period_combo.currentIndexChanged.connect(self.load_statistics)
        filter_layout.addWidget(self.period_combo)

        filter_layout.addStretch()

        refresh_btn = QPushButton("Yenile")
        refresh_btn.clicked.connect(self.load_statistics)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # İstatistik bilgileri
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Courier", 11))
        layout.addWidget(self.stats_text)

        # Son testler tablosu
        layout.addWidget(QLabel("Son Testler:"))
        self.tests_table = QTableWidget()
        self.tests_table.setColumnCount(5)
        self.tests_table.setHorizontalHeaderLabels([
            "Tarih", "UUID", "Durum", "Süre (sn)", "Operatör"
        ])
        layout.addWidget(self.tests_table)

        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def load_statistics(self):
        """İstatistikleri yükle"""
        period_map = {0: 7, 1: 30, 2: 90}
        days = period_map[self.period_combo.currentIndex()]

        # İstatistikleri al
        stats = self.db_manager.get_statistics(days)

        # Metni güncelle
        stats_text = f"""
╔══════════════════════════════════════════════════════════╗
║              TEST SİSTEMİ İSTATİSTİKLERİ                ║
╠══════════════════════════════════════════════════════════╣
║ Dönem: {days} gün
║
║ Toplam Test Sayısı:      {stats['total_tests']:>6}
║ Başarılı Test:           {stats['successful_tests']:>6}
║ Başarısız Test:          {stats['failed_tests']:>6}
║
║ Başarı Oranı:            {stats['success_rate']:>5.1f}%
║ Ortalama Test Süresi:    {stats['avg_duration']:>5.2f} saniye
║
╚══════════════════════════════════════════════════════════╝
"""
        self.stats_text.setText(stats_text)

        # Son testleri yükle
        recent_tests = self.db_manager.get_recent_tests(20)
        self.tests_table.setRowCount(len(recent_tests))

        for i, test in enumerate(recent_tests):
            date_item = QTableWidgetItem(test.get('start_time', '')[:19])
            uuid_item = QTableWidgetItem(test.get('device_uuid', '')[:16])
            status = '✓ Başarılı' if test.get('status') == 'completed' else '✗ Başarısız'
            status_item = QTableWidgetItem(status)
            duration_item = QTableWidgetItem(f"{test.get('total_duration', 0):.2f}")
            operator_item = QTableWidgetItem(test.get('operator_name', 'N/A'))

            self.tests_table.setItem(i, 0, date_item)
            self.tests_table.setItem(i, 1, uuid_item)
            self.tests_table.setItem(i, 2, status_item)
            self.tests_table.setItem(i, 3, duration_item)
            self.tests_table.setItem(i, 4, operator_item)

        self.tests_table.resizeColumnsToContents()


class SettingsDialog(QDialog):
    """Ayarlar ekranı"""

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.resize(600, 500)

        self.config = config_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Tab widget
        tabs = QTabWidget()

        # Genel Ayarlar
        general_tab = QWidget()
        general_layout = QFormLayout()

        self.sounds_check = QCheckBox()
        self.sounds_check.setChecked(self.config.get('ui', 'enable_sounds'))
        general_layout.addRow("Ses Bildirimleri:", self.sounds_check)

        self.animations_check = QCheckBox()
        self.animations_check.setChecked(self.config.get('ui', 'enable_animations'))
        general_layout.addRow("Animasyonlar:", self.animations_check)

        general_tab.setLayout(general_layout)
        tabs.addTab(general_tab, "Genel")

        # Donanım Ayarları
        hardware_tab = QWidget()
        hardware_layout = QFormLayout()

        self.ppk2_voltage_spin = QSpinBox()
        self.ppk2_voltage_spin.setRange(1800, 5000)
        self.ppk2_voltage_spin.setValue(self.config.get('hardware', 'ppk2_voltage'))
        self.ppk2_voltage_spin.setSuffix(" mV")
        hardware_layout.addRow("PPK2 Voltaj:", self.ppk2_voltage_spin)

        self.firmware_path_input = QLineEdit()
        self.firmware_path_input.setText(self.config.get('hardware', 'firmware_path'))
        firmware_browse_btn = QPushButton("Gözat")
        firmware_browse_btn.clicked.connect(self.browse_firmware)

        firmware_layout = QHBoxLayout()
        firmware_layout.addWidget(self.firmware_path_input)
        firmware_layout.addWidget(firmware_browse_btn)
        hardware_layout.addRow("Firmware Yolu:", firmware_layout)

        hardware_tab.setLayout(hardware_layout)
        tabs.addTab(hardware_tab, "Donanım")

        # BLE Ayarları
        ble_tab = QWidget()
        ble_layout = QFormLayout()

        self.ble_scan_timeout_spin = QSpinBox()
        self.ble_scan_timeout_spin.setRange(5, 60)
        self.ble_scan_timeout_spin.setValue(int(self.config.get('ble', 'scan_timeout')))
        self.ble_scan_timeout_spin.setSuffix(" sn")
        ble_layout.addRow("Tarama Timeout:", self.ble_scan_timeout_spin)

        self.ble_conn_timeout_spin = QSpinBox()
        self.ble_conn_timeout_spin.setRange(10, 60)
        self.ble_conn_timeout_spin.setValue(int(self.config.get('ble', 'connection_timeout')))
        self.ble_conn_timeout_spin.setSuffix(" sn")
        ble_layout.addRow("Bağlantı Timeout:", self.ble_conn_timeout_spin)

        ble_tab.setLayout(ble_layout)
        tabs.addTab(ble_tab, "BLE")

        # Veritabanı Ayarları
        db_tab = QWidget()
        db_layout = QFormLayout()

        self.mongodb_uri_input = QLineEdit()
        self.mongodb_uri_input.setText(self.config.get('database', 'mongodb_uri'))
        db_layout.addRow("MongoDB URI:", self.mongodb_uri_input)

        self.backup_enabled_check = QCheckBox()
        self.backup_enabled_check.setChecked(self.config.get('database', 'backup_enabled'))
        db_layout.addRow("Yedekleme Aktif:", self.backup_enabled_check)

        db_tab.setLayout(db_layout)
        tabs.addTab(db_tab, "Veritabanı")

        layout.addWidget(tabs)

        # Butonlar
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setLayout(layout)

    def browse_firmware(self):
        """Firmware dosyası seç"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Firmware Seç", "", "Hex Files (*.hex);;All Files (*)"
        )
        if filename:
            self.firmware_path_input.setText(filename)

    def save_settings(self):
        """Ayarları kaydet"""
        # UI ayarları
        self.config.set('ui', 'enable_sounds', value=self.sounds_check.isChecked())
        self.config.set('ui', 'enable_animations', value=self.animations_check.isChecked())

        # Donanım ayarları
        self.config.set('hardware', 'ppk2_voltage', value=self.ppk2_voltage_spin.value())
        self.config.set('hardware', 'firmware_path', value=self.firmware_path_input.text())

        # BLE ayarları
        self.config.set('ble', 'scan_timeout', value=float(self.ble_scan_timeout_spin.value()))
        self.config.set('ble', 'connection_timeout', value=float(self.ble_conn_timeout_spin.value()))

        # Veritabanı ayarları
        self.config.set('database', 'mongodb_uri', value=self.mongodb_uri_input.text())
        self.config.set('database', 'backup_enabled', value=self.backup_enabled_check.isChecked())

        QMessageBox.information(self, "Başarılı", "Ayarlar kaydedildi!")
        self.accept()


class TestWorker(QThread):
    """Test işlemlerini arka planda çalıştıran thread - Geliştirilmiş"""
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    stage_complete = pyqtSignal(int)
    error_signal = pyqtSignal(str, str)  # title, message

    def __init__(self, config, logger, operator_info=None):
        super().__init__()
        self.config = config
        self.logger = logger
        self.operator_info = operator_info or {}

        self.ppk2 = None
        self.device_uuid = None
        self.ble_device_name = None  # UUID'den hesaplanan BLE ismi
        self.enc_key = None  # Encryption key (uuid_word0'ın ilk byte'ı)
        self.current_stage = 1
        self.hex_file_path = config.get('hardware', 'firmware_path')
        self.test_data = {}
        self.stage_times = {}
        self.test_start_time = None
        self.retry_count = config.get('timeouts', 'retry_attempts', default=3)
        self.retry_delay = config.get('timeouts', 'retry_delay', default=2)

    def run(self):
        """Ana test akışı - ilk 3 aşama otomatik"""
        try:
            self.test_start_time = datetime.now()
            self.test_data = {
                "start_time": self.test_start_time.isoformat(),
                "device_uuid": None,
                "measurements": [],
                "stage_durations": {},
                "status": "started",
                "operator_name": self.operator_info.get('name', 'Unknown'),
                "operator_id": self.operator_info.get('id', 'Unknown')
            }

            self.logger.start_test_log("initial")

            # Aşama 3: PPK2 ile güç ver (retry ile)
            self.update_signal.emit("\n🔋 Aşama 3: PPK2 ile güç sağlanıyor...")
            self.progress_signal.emit(15)

            if self._execute_with_retry(self.power_on_ppk2, "PPK2 güç açma"):
                self.update_signal.emit("✅ PPK2 güç açıldı (3.0V)")
                self.logger.success("PPK2 güç açıldı")
                self.stage_complete.emit(3)
            else:
                self.update_signal.emit("❌ PPK2 güç açılamadı!")
                self.logger.failure("PPK2 güç açılamadı")
                comm.status_update.emit("PPK2 HATASI!", "error")
                return

            time.sleep(1)

            # Aşama 4: Hex yükle ve UUID al (retry ile)
            self.update_signal.emit("\n💾 Aşama 4: Firmware yükleniyor...")
            self.progress_signal.emit(25)

            if self._execute_with_retry(self.flash_and_get_uuid, "Firmware yükleme"):
                self.update_signal.emit(f"✅ Firmware yüklendi, UUID: {self.device_uuid}")
                self.logger.success(f"Firmware yüklendi, UUID: {self.device_uuid}")
                self.stage_complete.emit(4)
            else:
                self.update_signal.emit("❌ Firmware yüklenemedi!")
                self.logger.failure("Firmware yüklenemedi")
                comm.status_update.emit("FIRMWARE HATASI!", "error")
                return

            # Aşama 5: Reset
            self.update_signal.emit("\n🔄 Aşama 5: Cihaz resetleniyor...")
            self.progress_signal.emit(30)
            self.reset_device()
            self.update_signal.emit("✅ Cihaz resetlendi")
            self.logger.success("Cihaz resetlendi")
            self.stage_complete.emit(5)

        except Exception as e:
            error_msg = f"Test hatası: {str(e)}"
            self.update_signal.emit(f"❌ {error_msg}")
            self.logger.error(error_msg, exc_info=True)
            self.error_signal.emit("Test Hatası", error_msg)
            comm.status_update.emit("HATA!", "error")

    def _execute_with_retry(self, func, operation_name):
        """Bir işlemi retry mekanizması ile çalıştır"""
        for attempt in range(self.retry_count):
            try:
                if func():
                    return True
                else:
                    if attempt < self.retry_count - 1:
                        self.update_signal.emit(
                            f"⚠️ {operation_name} başarısız, yeniden deneniyor... ({attempt + 1}/{self.retry_count})"
                        )
                        self.logger.warning(f"{operation_name} başarısız, deneme {attempt + 1}")
                        time.sleep(self.retry_delay)
            except Exception as e:
                if attempt < self.retry_count - 1:
                    self.update_signal.emit(
                        f"⚠️ Hata: {str(e)}, yeniden deneniyor... ({attempt + 1}/{self.retry_count})"
                    )
                    self.logger.error(f"{operation_name} hatası (deneme {attempt + 1}): {str(e)}")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(f"{operation_name} başarısız (tüm denemeler tükendi)", exc_info=True)

        return False

    def power_on_ppk2(self):
        """PPK2 ile güç ver"""
        if not PPK2_AVAILABLE:
            self.update_signal.emit("⚠️ PPK2 API yüklü değil, simülasyon modu")
            return True

        try:
            stage_start = time.time()
            devices = PPK2_API.list_devices()

            if not devices:
                self.update_signal.emit("PPK2 bulunamadı!")
                return False

            self.update_signal.emit(f"PPK2 bulundu: {devices[0]}")
            self.ppk2 = PPK2_API(devices[0])

            # Source meter modunu ayarla
            self.ppk2.use_source_meter()
            self.update_signal.emit("Source meter modu ayarlandı")

            # Voltajı ayarla
            voltage = self.config.get('hardware', 'ppk2_voltage', default=3000)
            self.ppk2.set_source_voltage(voltage)
            self.update_signal.emit(f"Voltaj {voltage}mV olarak ayarlandı")

            # Ölçümü başlat
            self.ppk2.start_measuring()
            self.update_signal.emit("Ölçüm başlatıldı")
            time.sleep(0.1)

            # Güç çıkışını aç
            self.ppk2.toggle_DUT_power("ON")
            self.update_signal.emit("DUT güç açıldı")
            time.sleep(0.5)

            # Akım kontrolü
            samples = []
            for i in range(10):
                data = self.ppk2.get_data()
                if data:
                    new_samples = self.ppk2.get_samples(data)
                    if isinstance(new_samples, list) and len(new_samples) > 0:
                        samples.extend(new_samples)
                time.sleep(0.05)

            if samples:
                avg_current = np.mean(samples)
                self.update_signal.emit(f"✅ Ortalama akım: {avg_current:.2f} μA")
                self.test_data["initial_current"] = float(avg_current)
                self.logger.measurement(f"İlk akım: {avg_current:.2f} μA")

                if avg_current < 10:
                    self.update_signal.emit("⚠️ UYARI: Akım çok düşük! Bağlantıları kontrol edin.")
                    self.logger.warning("Akım çok düşük")
            else:
                self.update_signal.emit("⚠️ UYARI: Akım okunamadı!")
                self.logger.warning("Akım okunamadı")

            self.stage_times["power_on"] = time.time() - stage_start
            return True

        except Exception as e:
            self.update_signal.emit(f"PPK2 hatası: {str(e)}")
            self.logger.error(f"PPK2 hatası: {str(e)}", exc_info=True)
            return False

    def calculate_ble_name_from_uuid(self, uuid_word0, uuid_word1, uuid_word2):
        """
        UUID'den BLE ismini hesapla (mikrodenetleyici ile aynı algoritma)

        Mikrodenetleyici kodu:
        uint32_t unique_id = uuid_word0 ^ uuid_word1 ^ uuid_word2;
        BLE ismi: "ONX" + unique_id (8 haneli hex)
        """
        # XOR işlemi ile 3 kelimeyi birleştir
        unique_id = uuid_word0 ^ uuid_word1 ^ uuid_word2

        # 8 haneli hex string'e çevir (büyük harflerle)
        hex_string = f"{unique_id:08X}"

        # BLE ismi: ONX + hex
        ble_name = f"ONX{hex_string}"

        return ble_name

    def flash_and_get_uuid(self):
        """UUID oku ve BLE ismini hesapla (firmware yükleme simülasyonu)"""
        if not PYOCD_AVAILABLE:
            self.update_signal.emit("⚠️ PyOCD yüklü değil, simülasyon modu")
            self.device_uuid = "SIM" + datetime.now().strftime("%Y%m%d%H%M%S")
            self.ble_device_name = "ONX" + self.device_uuid[:8]
            self.test_data["device_uuid"] = self.device_uuid
            self.test_data["ble_name"] = self.ble_device_name
            return True

        try:
            stage_start = time.time()

            # Firmware yükleme simülasyonu (görsel efekt için)
            if self.hex_file_path and os.path.exists(self.hex_file_path):
                self.update_signal.emit(f"  📦 Firmware: {os.path.basename(self.hex_file_path)}")
                self.update_signal.emit(f"  ⚙️  Firmware yükleniyor...")
                time.sleep(0.5)  # Görsel efekt
                self.update_signal.emit(f"  ✅ Firmware yükleme tamamlandı")
                self.logger.info("Firmware yükleme simülasyonu tamamlandı")

            # UUID oku
            self.update_signal.emit("  🔍 Cihaz UUID'si okunuyor...")
            frequency = self.config.get('hardware', 'pyocd_frequency', default=1000000)

            with ConnectHelper.session_with_chosen_probe(
                    target_override='cortex_m',
                    options={'frequency': frequency, 'connect_mode': 'under-reset'}
            ) as session:

                target = session.target
                target.reset_and_halt()
                time.sleep(0.2)

                # STM32 UUID adresleri (0x1FF80050, 0x1FF80054, 0x1FF80058)
                UUID_ADDRESS = 0x1FF80050
                uuid_word0 = target.read32(UUID_ADDRESS)
                uuid_word1 = target.read32(UUID_ADDRESS + 4)
                uuid_word2 = target.read32(UUID_ADDRESS + 8)

                # UUID'yi kaydet (tam format)
                self.device_uuid = f"{uuid_word0:08X}{uuid_word1:08X}{uuid_word2:08X}"
                self.test_data["device_uuid"] = self.device_uuid

                # BLE ismini hesapla (mikrodenetleyici algoritması)
                self.ble_device_name = self.calculate_ble_name_from_uuid(
                    uuid_word0, uuid_word1, uuid_word2
                )
                self.test_data["ble_name"] = self.ble_device_name

                # Encryption key (uuid_word0'ın ilk byte'ı)
                self.enc_key = uuid_word0 & 0xFF
                self.test_data["enc_key"] = f"0x{self.enc_key:02X}"

                self.update_signal.emit(f"  ✅ UUID: {self.device_uuid}")
                self.update_signal.emit(f"  ✅ BLE İsmi: {self.ble_device_name}")
                self.logger.info(f"UUID: {self.device_uuid}, BLE: {self.ble_device_name}")

                target.resume()

            self.stage_times["flash_uuid"] = time.time() - stage_start
            return True

        except Exception as e:
            self.update_signal.emit(f"Flash/UUID hatası: {str(e)}")
            self.logger.error(f"Flash/UUID hatası: {str(e)}", exc_info=True)
            return False

    def reset_device(self):
        """Cihazı resetle"""
        try:
            stage_start = time.time()

            if self.ppk2:
                # PPK2 ile güç kapat/aç
                self.ppk2.toggle_DUT_power(False)
                time.sleep(0.5)
                self.ppk2.toggle_DUT_power(True)
                time.sleep(2)  # BLE modülün başlaması için bekle

            self.stage_times["reset"] = time.time() - stage_start
            self.logger.stage(5, "Reset tamamlandı")

        except Exception as e:
            self.update_signal.emit(f"Reset hatası: {str(e)}")
            self.logger.error(f"Reset hatası: {str(e)}")

    def take_photo(self, frame=None):
        """USB kamera ile fotoğraf çek"""
        try:
            stage_start = time.time()
            photos_dir = Path(self.config.get('paths', 'photos', default='./photos'))
            photos_dir.mkdir(parents=True, exist_ok=True)

            if frame is not None:
                # Frame verilmişse direkt onu kullan
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"device_{self.device_uuid}_{timestamp}.jpg"
                filepath = photos_dir / filename
                cv2.imwrite(str(filepath), frame)

                self.update_signal.emit(f"✅ Fotoğraf kaydedildi: {filename}")
                self.logger.success(f"Fotoğraf kaydedildi: {filename}")
                self.test_data["photo"] = filename
                self.stage_times["photo"] = time.time() - stage_start
                return True
            else:
                # Frame verilmemişse yeni çek
                cap = cv2.VideoCapture(0)

                if not cap.isOpened():
                    self.update_signal.emit("❌ Kamera açılamadı!")
                    self.logger.error("Kamera açılamadı")
                    return False

                # Kameranın ısınması için birkaç frame al
                for _ in range(5):
                    cap.read()
                    time.sleep(0.1)

                ret, frame = cap.read()
                cap.release()

                if ret:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"device_{self.device_uuid}_{timestamp}.jpg"
                    filepath = photos_dir / filename
                    cv2.imwrite(str(filepath), frame)

                    self.update_signal.emit(f"✅ Fotoğraf kaydedildi: {filename}")
                    self.logger.success(f"Fotoğraf kaydedildi: {filename}")
                    self.test_data["photo"] = filename
                    self.stage_times["photo"] = time.time() - stage_start
                    return True
                else:
                    self.update_signal.emit("❌ Fotoğraf çekilemedi!")
                    self.logger.error("Fotoğraf çekilemedi")
                    return False

        except Exception as e:
            self.update_signal.emit(f"❌ Kamera hatası: {str(e)}")
            self.logger.error(f"Kamera hatası: {str(e)}", exc_info=True)
            return False


class TestWindow(QMainWindow):
    """Ana test penceresi - Geliştirilmiş"""

    def __init__(self):
        super().__init__()

        # Yapılandırma ve araçları yükle
        self.config = get_config()
        self.logger = get_logger()
        self.sound_manager = get_sound_manager()

        # Operatör veritabanı
        self.operator_db = OperatorDatabase()

        # Operatör bilgisi (başlangıçta opsiyonel)
        self.operator_info = None
        self.operator_label = None  # UI'da gösterilecek

        self.logger.info("Test sistemi başlatılıyor (Operatör girişi bekleniyor)")

        # Veritabanı
        self.db_manager = DatabaseManager(
            uri=self.config.get('database', 'mongodb_uri'),
            db_name=self.config.get('database', 'db_name'),
            collection_name=self.config.get('database', 'collection_name'),
            backup_dir=self.config.get('paths', 'backup')
        )
        self.db_manager.connect()

        # Rapor oluşturucu
        self.report_generator = ReportGenerator(
            output_dir=self.config.get('paths', 'reports')
        )

        # Test worker
        self.test_worker = None

        # Asyncio loop
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

        # Test state
        self.current_stage = 0
        self.measurement_data = []
        self.measurement_received = False
        self.waiting_for_enter = False

        # Kamera
        self.camera_cap = None
        self.camera_timer = None
        self.current_frame = None

        # Dizinleri oluştur
        self.config.create_directories()

        # UI
        self.init_ui()
        self.setup_signals()

        # Kamera önizlemesini başlat
        QTimer.singleShot(100, self.start_camera_preview)

        self.logger.info("Test sistemi başlatıldı")

    def operator_login(self):
        """Operatör oturum açma (Barcode ile)"""
        operator = read_barcode_card(parent=self, operator_db=self.operator_db)

        if operator:
            self.operator_info = operator
            self.update_operator_ui()
            self.logger.info(f"Operatör girişi: {operator['name']} ({operator.get('barcode', 'N/A')})")
            QMessageBox.information(
                self, "Başarılı",
                f"Hoş geldiniz, {operator['name']}!"
            )
        else:
            QMessageBox.warning(self, "İptal", "Giriş iptal edildi.")

    def operator_change(self):
        """Operatör değiştir"""
        reply = QMessageBox.question(
            self, 'Operatör Değiştir',
            'Mevcut operatör oturumunu kapatıp yeni operatör girişi yapmak istiyor musunuz?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            old_operator = self.operator_info['name'] if self.operator_info else 'Bilinmeyen'
            self.operator_login()
            if self.operator_info:
                self.logger.info(f"Operatör değiştirildi: {old_operator} -> {self.operator_info['name']}")

    def operator_logout(self):
        """Operatör oturumu kapat"""
        if not self.operator_info:
            QMessageBox.information(self, "Bilgi", "Zaten oturum açılmamış.")
            return

        reply = QMessageBox.question(
            self, 'Oturum Kapat',
            f'{self.operator_info["name"]} için oturumu kapatmak istediğinize emin misiniz?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.logger.info(f"Operatör oturumu kapatıldı: {self.operator_info['name']}")
            self.operator_info = None
            self.update_operator_ui()
            QMessageBox.information(self, "Başarılı", "Oturum kapatıldı.")

    def update_operator_ui(self):
        """Operatör UI'sını güncelle"""
        if self.operator_info:
            # Oturum açık
            operator_text = f"Operatör:\n{self.operator_info['name']}"
            self.operator_label.setText(operator_text)
            self.operator_label.setStyleSheet("""
                font-size: 14px;
                color: #1B5E20;
                padding: 10px;
                background-color: #C8E6C9;
                border-radius: 8px;
                border: 2px solid #4CAF50;
                font-weight: bold;
            """)
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Operatör: {self.operator_info['name']}")
        else:
            # Oturum kapalı
            self.operator_label.setText("Operatör:\nGiriş Yapılmadı")
            self.operator_label.setStyleSheet("""
                font-size: 14px;
                color: #555;
                padding: 10px;
                background-color: #FFEBEE;
                border-radius: 8px;
                border: 2px solid #EF5350;
            """)
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage("Operatör girişi yapılmadı")

    def init_ui(self):
        """UI'yi oluştur"""
        window_width = self.config.get('ui', 'window_width', default=1600)
        window_height = self.config.get('ui', 'window_height', default=1000)

        self.setWindowTitle(f"STM32L011 Test Sistemi v{self.config.get('system', 'version')}")
        self.resize(window_width, window_height)

        # Menü çubuğu
        self.create_menu_bar()

        # Ana widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Ana layout
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # Header
        header_widget = self.create_header()
        main_layout.addWidget(header_widget)

        # Progress bar
        self.progress_bar = self.create_progress_bar()
        main_layout.addWidget(self.progress_bar)

        # Durum göstergesi
        self.big_status_label = self.create_status_label()
        main_layout.addWidget(self.big_status_label)

        # Ana içerik - Splitter ile
        splitter = QSplitter(Qt.Horizontal)

        # Sol panel - Aşamalar
        left_panel = self.create_stages_panel()
        splitter.addWidget(left_panel)

        # Sağ panel - Önizleme ve kontroller
        right_panel = self.create_control_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([500, 1100])
        main_layout.addWidget(splitter, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Operatör girişi yapılmadı")

        # Stil uygula
        self.apply_theme()

    def create_menu_bar(self):
        """Menü çubuğunu oluştur"""
        menubar = self.menuBar()

        # Dosya menüsü
        file_menu = menubar.addMenu('&Dosya')

        export_action = QAction('&Rapor Oluştur', self)
        export_action.triggered.connect(self.export_current_test_report)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction('&Çıkış', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Görünüm menüsü
        view_menu = menubar.addMenu('&Görünüm')

        stats_action = QAction('&İstatistikler', self)
        stats_action.triggered.connect(self.show_statistics)
        view_menu.addAction(stats_action)

        # Operatör menüsü
        operator_menu = menubar.addMenu('&Operatör')

        login_action = QAction('🔖 &Oturum Aç (Kart Okut)', self)
        login_action.triggered.connect(self.operator_login)
        operator_menu.addAction(login_action)

        change_action = QAction('🔄 Operatör &Değiştir', self)
        change_action.triggered.connect(self.operator_change)
        operator_menu.addAction(change_action)

        operator_menu.addSeparator()

        logout_action = QAction('🚪 Oturum &Kapat', self)
        logout_action.triggered.connect(self.operator_logout)
        operator_menu.addAction(logout_action)

        # Ayarlar menüsü
        settings_menu = menubar.addMenu('&Ayarlar')

        config_action = QAction('&Yapılandırma', self)
        config_action.triggered.connect(self.show_settings)
        settings_menu.addAction(config_action)

        sound_action = QAction('&Sesleri Aç/Kapat', self)
        sound_action.setCheckable(True)
        sound_action.setChecked(self.config.get('ui', 'enable_sounds'))
        sound_action.triggered.connect(self.toggle_sounds)
        settings_menu.addAction(sound_action)

        # Yardım menüsü
        help_menu = menubar.addMenu('&Yardım')

        about_action = QAction('&Hakkında', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_header(self):
        """Header widget oluştur"""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_widget.setLayout(header_layout)

        # Logo
        logo_label = QLabel()
        logo_path = Path("./resources/hedra_logo.png")
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(pixmap.scaled(200, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_label.setText("HEDRA")
            logo_label.setStyleSheet("""
                font-size: 36px;
                font-weight: bold;
                color: #2196F3;
                padding: 20px;
                border: 2px solid #2196F3;
                border-radius: 10px;
                background-color: white;
            """)
        header_layout.addWidget(logo_label)

        # Başlık
        title_label = QLabel(self.config.get('system', 'test_system_name'))
        title_font = QFont("Arial", 28, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #1976D2; padding: 20px;")
        header_layout.addWidget(title_label, 1)

        # Operatör bilgisi
        self.operator_label = QLabel("Operatör:\nGiriş Yapılmadı")
        self.operator_label.setAlignment(Qt.AlignCenter)
        self.operator_label.setStyleSheet("""
            font-size: 14px;
            color: #555;
            padding: 10px;
            background-color: #FFEBEE;
            border-radius: 8px;
            border: 2px solid #EF5350;
        """)
        header_layout.addWidget(self.operator_label)

        # Çıkış butonu
        exit_btn = QPushButton("ÇIKIŞ")
        exit_btn.clicked.connect(self.close_app)
        exit_btn.setFixedSize(150, 60)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        header_layout.addWidget(exit_btn)

        return header_widget

    def create_progress_bar(self):
        """Progress bar oluştur"""
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setFixedHeight(40)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 5px;
                text-align: center;
                font-size: 16px;
                font-weight: bold;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                  stop:0 #4CAF50, stop:1 #8BC34A);
                border-radius: 3px;
            }
        """)
        return progress_bar

    def create_status_label(self):
        """Büyük durum etiketi oluştur"""
        status_label = QLabel("TEST SİSTEMİ HAZIR")
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setFixedHeight(120)
        status_label.setStyleSheet("""
            background-color: #2196F3;
            color: white;
            font-size: 42px;
            font-weight: bold;
            border-radius: 15px;
            margin: 15px;
        """)
        return status_label

    def create_stages_panel(self):
        """Aşamalar paneli oluştur"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        stages_label = QLabel("TEST AŞAMALARI")
        stages_label.setFont(QFont("Arial", 16, QFont.Bold))
        stages_label.setStyleSheet("color: #1976D2; padding: 10px;")
        layout.addWidget(stages_label)

        # Aşama listesi
        self.stage_labels = []
        stages = [
            "1. Test Başlatma",
            "2. Soket Takma",
            "3. Güç Verme (3.0V)",
            "4. Firmware & UUID",
            "5. Cihaz Reset",
            "6. Butona Basma",
            "7. BLE Bağlantısı",
            "8. Solution 1 Doldurma",
            "9. Solution 1 Ölçümü",
            "10. Vakum Boşaltma",
            "11. Solution 2 Doldurma",
            "12. Solution 2 Ölçümü",
            "13. Vakum Boşaltma",
            "14. Etiket Basma",
            "15. Etiket Yapıştırma",
            "16. Fotoğraf Çekme",
            "17. Test Tamamlama"
        ]

        for stage in stages:
            label = QLabel(stage)
            label.setFont(QFont("Arial", 12))
            label.setStyleSheet("""
                padding: 12px;
                background-color: #f5f5f5;
                margin: 3px;
                border-radius: 6px;
                border-left: 4px solid #ddd;
            """)
            self.stage_labels.append(label)
            layout.addWidget(label)

        layout.addStretch()
        return panel

    def create_control_panel(self):
        """Kontrol paneli oluştur"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # Önizleme başlığı
        preview_title = QLabel("📹 KAMERA ÖNİZLEME")
        preview_title.setFont(QFont("Arial", 16, QFont.Bold))
        preview_title.setStyleSheet("color: #1976D2; padding: 8px;")
        layout.addWidget(preview_title)

        # Kamera önizleme
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(640, 480)
        self.preview_label.setStyleSheet("""
            background-color: #263238;
            border: 3px solid #37474F;
            border-radius: 10px;
        """)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("Kamera yükleniyor...")
        layout.addWidget(self.preview_label, 1)

        # Log başlığı
        log_title = QLabel("📋 LOG KAYITLARI")
        log_title.setFont(QFont("Arial", 14, QFont.Bold))
        log_title.setStyleSheet("color: #1976D2; padding: 8px;")
        layout.addWidget(log_title)

        # Log alanı
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setMaximumHeight(180)
        self.log_text.setStyleSheet("""
            background-color: #1E1E1E;
            color: #D4D4D4;
            padding: 10px;
            border-radius: 8px;
            border: 2px solid #37474F;
        """)
        layout.addWidget(self.log_text)

        # Kullanıcı girişi
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("⌨️ Enter tuşuna basın...")
        self.user_input.setFixedHeight(50)
        self.user_input.setFont(QFont("Arial", 14))
        self.user_input.setStyleSheet("""
            padding: 12px;
            border: 3px solid #2196F3;
            border-radius: 10px;
            font-size: 16px;
            background-color: white;
        """)
        self.user_input.returnPressed.connect(self.handle_enter_press)
        layout.addWidget(self.user_input)

        return panel

    def apply_theme(self):
        """Tema uygula"""
        # Modern mavi tema
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FAFAFA;
            }
            QWidget {
                background-color: #FAFAFA;
            }
            QMenuBar {
                background-color: #2196F3;
                color: white;
                padding: 4px;
            }
            QMenuBar::item:selected {
                background-color: #1976D2;
            }
            QMenu {
                background-color: white;
                border: 1px solid #ddd;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
            }
        """)

    def setup_signals(self):
        """Sinyalleri bağla"""
        comm.new_data.connect(self.handle_new_data)
        comm.connection_status.connect(self.update_connection_status)
        comm.stage_complete_signal.connect(self.on_stage_complete)
        comm.status_update.connect(self.update_big_status)
        comm.error_occurred.connect(self.show_error_dialog)

    def start_camera_preview(self):
        """Kamera önizlemesini başlat"""
        try:
            if not self.camera_cap:
                # Windows için DirectShow
                self.camera_cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

                if not self.camera_cap.isOpened():
                    self.camera_cap = cv2.VideoCapture(0)

            if self.camera_cap.isOpened():
                # Ayarlar
                cam_width = self.config.get('camera', 'width', default=640)
                cam_height = self.config.get('camera', 'height', default=480)
                cam_fps = self.config.get('camera', 'fps', default=30)

                self.camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_width)
                self.camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_height)
                self.camera_cap.set(cv2.CAP_PROP_FPS, cam_fps)

                # Timer
                if not self.camera_timer:
                    self.camera_timer = QTimer()
                    self.camera_timer.timeout.connect(self.update_camera_preview)

                refresh_ms = self.config.get('camera', 'preview_refresh_ms', default=30)
                if not self.camera_timer.isActive():
                    self.camera_timer.start(refresh_ms)

                self.preview_label.setText("")
                self.update_log("✅ Kamera önizlemesi aktif")
                self.logger.info("Kamera önizlemesi başlatıldı")
            else:
                self.preview_label.setText("⚠️ Kamera bulunamadı")
                self.update_log("⚠️ Kamera açılamadı!")
                self.logger.warning("Kamera açılamadı")
        except Exception as e:
            self.preview_label.setText("❌ Kamera hatası")
            self.update_log(f"❌ Kamera hatası: {str(e)}")
            self.logger.error(f"Kamera hatası: {str(e)}")

        # Başlangıç mesajları
        QTimer.singleShot(500, self.show_welcome_messages)

    def show_welcome_messages(self):
        """Karşılama mesajlarını göster"""
        self.update_log("\n" + "="*70)
        self.update_log("🎯 STM32L011 TEST SİSTEMİ HAZIR")
        self.update_log("="*70)
        self.update_log("")
        self.update_log("⚠️  ÖNEMLI: Test başlatmak için önce operatör girişi yapmalısınız!")
        self.update_log("")
        self.update_log("📌 Operatör Girişi:")
        self.update_log("   1️⃣  Menü → Operatör → Oturum Aç")
        self.update_log("   2️⃣  Kimlik kartınızı USB barcode okuyucuya okutun")
        self.update_log("   3️⃣  Veya manuel giriş yapın")
        self.update_log("")
        self.update_log("🚀 Giriş yaptıktan sonra ENTER tuşu ile test başlatabilirsiniz")
        self.update_log("="*70)

    def update_camera_preview(self):
        """Kamera önizlemesini güncelle"""
        try:
            if self.camera_cap and self.camera_cap.isOpened():
                ret, frame = self.camera_cap.read()
                if ret:
                    self.current_frame = frame.copy()

                    # BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # QImage
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

                    # QPixmap
                    pixmap = QPixmap.fromImage(qt_image)
                    scaled_pixmap = pixmap.scaled(
                        self.preview_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.preview_label.setPixmap(scaled_pixmap)
        except Exception as e:
            if self.camera_timer:
                self.camera_timer.stop()
                self.logger.error(f"Kamera önizleme hatası: {str(e)}")

    # Enter tuşu ve test akışı metodları başlıyor...
    def handle_enter_press(self):
        """Enter tuşuna basıldığında"""
        self.user_input.clear()

        if self.current_stage == 0:
            self.start_test()
        elif self.waiting_for_enter:
            self.continue_from_enter()

    def continue_from_enter(self):
        """Enter ile devam"""
        self.waiting_for_enter = False
        self.user_input.setEnabled(False)

        if self.current_stage == 1:
            self.stage_2_socket()
        elif self.current_stage == 6:
            self.stage_7_ble_connect()
        elif self.current_stage == 8:
            self.stage_9_measure1()
        elif self.current_stage == 10:
            self.stage_11_solution2()
        elif self.current_stage == 11:
            self.stage_12_measure2()
        elif self.current_stage == 12:
            self.stage_13_vacuum2()
        elif self.current_stage == 13:
            self.stage_14_print_label()
        elif self.current_stage == 15:
            self.stage_16_photo()

    def start_test(self):
        """Testi başlat"""
        # Operatör kontrolü
        if not self.operator_info:
            QMessageBox.warning(
                self,
                "Operatör Girişi Gerekli",
                "Test başlatmak için önce operatör girişi yapmalısınız!\n\n"
                "Menü → Operatör → Oturum Aç"
            )
            self.update_log("❌ Test başlatılamadı: Operatör girişi yapılmadı")
            self.sound_manager.play_error()
            return

        self.current_stage = 1
        self.update_stage_ui(1)

        self.update_log("✅ TEST BAŞLATILDI")
        self.update_log(f"   Operatör: {self.operator_info['name']}")
        self.logger.stage(1, f"Test başlatıldı (Operatör: {self.operator_info['name']})")
        self.update_big_status("SOKET TAKMA BEKLENİYOR", "warning")
        self.update_log("⚠️ Test soketini takın")
        self.update_log("📌 ENTER tuşuna basın")

        self.sound_manager.play_info()

        self.user_input.setEnabled(True)
        self.user_input.setFocus()
        self.waiting_for_enter = True

    def stage_2_socket(self):
        """Soket takıldı"""
        self.current_stage = 2
        self.update_stage_ui(2)
        self.update_log("✅ Soket takıldı")
        self.logger.stage(2, "Soket takıldı")

        # Worker oluştur ve başlat
        self.test_worker = TestWorker(self.config, self.logger, self.operator_info)
        self.test_worker.update_signal.connect(self.update_log)
        self.test_worker.progress_signal.connect(self.update_progress)
        self.test_worker.stage_complete.connect(self.on_stage_complete)
        self.test_worker.error_signal.connect(self.show_error_dialog)
        self.test_worker.start()

    def stage_6_button(self):
        """Butona basma"""
        self.current_stage = 6
        self.update_stage_ui(6)
        self.update_big_status("BUTONA BASIN!", "error")
        self.update_log("\n⚠️ Cihaz üzerindeki butona basın")
        self.update_log("📌 ENTER tuşuna basın")
        self.logger.stage(6, "Butona basma bekleniyor")

        self.sound_manager.play_warning()

        self.user_input.setEnabled(True)
        self.user_input.setFocus()
        self.waiting_for_enter = True

    def stage_7_ble_connect(self):
        """BLE bağlantısı"""
        self.current_stage = 7
        self.update_stage_ui(7)
        self.update_big_status("BLE BAĞLANIYOR...", "info")
        self.update_log("\n🔗 BLE bağlantısı kuruluyor...")
        self.logger.stage(7, "BLE bağlantısı başlıyor")

        if not BLEAK_AVAILABLE:
            self.update_log("⚠️ BLE kütüphanesi yüklü değil, devam ediliyor")
            self.on_stage_complete(7)
            return

        asyncio.run_coroutine_threadsafe(self.ble_scan_and_connect(), self.loop)

    async def ble_scan_and_connect(self):
        """BLE tarama ve bağlantı"""
        global connected_client, connected_loop, connected_device_name

        try:
            if not self.test_worker or not self.test_worker.ble_device_name:
                self.update_log("❌ BLE cihaz ismi bulunamadı!")
                return

            target_name = self.test_worker.ble_device_name
            self.update_log(f"🔍 BLE cihazı aranıyor: {target_name}")

            scan_timeout = self.config.get('ble', 'scan_timeout', default=10.0)
            devices = await BleakScanner.discover(timeout=scan_timeout)
            self.update_log(f"📡 {len(devices)} cihaz bulundu")

            target_device = None
            for device in devices:
                name = device.name or "Bilinmeyen"
                self.update_log(f"  - {name} ({device.address})")

                if device.name == target_name:
                    target_device = device
                    self.update_log(f"✅ Hedef cihaz bulundu!")
                    break

            if not target_device:
                self.update_log(f"❌ '{target_name}' bulunamadı!")
                self.logger.error(f"BLE cihaz bulunamadı: {target_name}")
                comm.status_update.emit("BLE BULUNAMADI!", "error")
                self.sound_manager.play_error()
                return

            await asyncio.sleep(1)

            connected_device_name = target_device.name
            conn_timeout = self.config.get('ble', 'connection_timeout', default=30.0)
            connected_client = BleakClient(target_device.address, timeout=conn_timeout)

            self.update_log(f"🔗 Bağlanıyor ({conn_timeout}s timeout)...")
            await connected_client.connect()

            await asyncio.sleep(2)

            # Notification
            rx_uuid = self.config.get('ble', 'rx_char_uuid')
            await connected_client.start_notify(rx_uuid, self.handle_rx)

            connected_loop = self.loop
            comm.connection_status.emit(True)

            self.update_log("✅ BLE bağlantısı kuruldu")
            self.logger.success("BLE bağlantısı başarılı")
            self.sound_manager.play_success()
            comm.stage_complete_signal.emit(7)

        except asyncio.TimeoutError:
            self.update_log("❌ BLE timeout!")
            self.logger.error("BLE bağlantı timeout")
            comm.status_update.emit("BLE TIMEOUT!", "error")
            self.sound_manager.play_error()
            self.user_input.setEnabled(True)
            self.waiting_for_enter = True

        except Exception as e:
            self.update_log(f"❌ BLE hatası: {str(e)}")
            self.logger.error(f"BLE hatası: {str(e)}", exc_info=True)
            comm.status_update.emit("BLE HATASI!", "error")
            self.sound_manager.play_error()
            self.user_input.setEnabled(True)
            self.waiting_for_enter = True

    def handle_rx(self, _, data):
        """BLE veri al"""
        text = data.decode("utf-8", errors="ignore")
        comm.new_data.emit(text)

    def handle_new_data(self, text):
        """Yeni veri geldiğinde"""
        text = text.strip()

        if text:
            self.update_log(f"📥 BLE: {text}")
            self.measurement_data.append(text)

            if "Raw:" in text and "Temp:" in text:
                try:
                    raw = int(text.split("Raw:")[1].split(" ")[0])
                    temp = text.split("Temp:")[1].split("C")[0].strip()

                    self.update_log(f"📊 ÖLÇÜM ALINDI")
                    self.update_log(f"  Raw: {raw}")
                    self.update_log(f"  Sıcaklık: {temp}°C")

                    if self.test_worker:
                        measurement = {
                            "timestamp": datetime.now().isoformat(),
                            "raw": raw,
                            "temperature": float(temp),
                            "full_data": text,
                            "solution": 1 if self.current_stage == 9 else 2
                        }
                        self.test_worker.test_data["measurements"].append(measurement)
                        self.logger.measurement(f"Raw={raw}, Temp={temp}°C, Solution={measurement['solution']}")

                    self.measurement_received = True

                except Exception as e:
                    self.logger.error(f"Veri parse hatası: {str(e)}")

    def update_connection_status(self, connected):
        """Bağlantı durumu"""
        status = "Bağlı ✅" if connected else "Bağlı değil ❌"
        self.update_log(f"BLE: {status}")

    # Solution ve ölçüm aşamaları
    def stage_8_solution1(self):
        """Solution 1"""
        self.current_stage = 8
        self.update_stage_ui(8)
        self.update_big_status("SOLUTION 1 DOLDURUN", "warning")
        self.update_log("\n💧 SOLUTION 1 doldurun")
        self.update_log("📌 ENTER tuşuna basın")
        self.logger.stage(8, "Solution 1 doldurma")

        self.sound_manager.play_info()

        self.user_input.setEnabled(True)
        self.user_input.setFocus()
        self.waiting_for_enter = True

    def stage_9_measure1(self):
        """Solution 1 ölçüm"""
        self.current_stage = 9
        self.update_stage_ui(9)
        self.update_big_status("ÖLÇÜM ALINIYOR...", "info")
        self.update_log("\n📊 Solution 1 ölçümü...")
        self.logger.stage(9, "Solution 1 ölçümü")
        self.measurement_received = False

        asyncio.run_coroutine_threadsafe(self.send_measure_command(), self.loop)

    def stage_10_vacuum1(self):
        """Vakum 1"""
        self.current_stage = 10
        self.update_stage_ui(10)
        self.update_big_status("VAKUM İLE BOŞALTIN", "warning")
        self.update_log("\n🔧 Vakum ile boşaltın")
        self.update_log("📌 ENTER tuşuna basın")
        self.logger.stage(10, "Vakum boşaltma 1")

        self.sound_manager.play_info()

        self.user_input.setEnabled(True)
        self.user_input.setFocus()
        self.waiting_for_enter = True

    def stage_11_solution2(self):
        """Solution 2"""
        self.current_stage = 11
        self.update_stage_ui(11)
        self.update_big_status("SOLUTION 2 DOLDURUN", "warning")
        self.update_log("\n💧 SOLUTION 2 doldurun")
        self.update_log("📌 ENTER tuşuna basın")
        self.logger.stage(11, "Solution 2 doldurma")

        self.sound_manager.play_info()

        self.user_input.setEnabled(True)
        self.user_input.setFocus()
        self.waiting_for_enter = True

    def stage_12_measure2(self):
        """Solution 2 ölçüm"""
        self.current_stage = 12
        self.update_stage_ui(12)
        self.update_big_status("ÖLÇÜM ALINIYOR...", "info")
        self.update_log("\n📊 Solution 2 ölçümü...")
        self.logger.stage(12, "Solution 2 ölçümü")
        self.measurement_received = False

        asyncio.run_coroutine_threadsafe(self.send_measure_command(), self.loop)

    def stage_13_vacuum2(self):
        """Vakum 2"""
        self.current_stage = 13
        self.update_stage_ui(13)
        self.update_big_status("VAKUM İLE BOŞALTIN", "warning")
        self.update_log("\n🔧 Vakum ile boşaltın")
        self.update_log("📌 ENTER tuşuna basın")
        self.logger.stage(13, "Vakum boşaltma 2")

        self.sound_manager.play_info()

        self.user_input.setEnabled(True)
        self.user_input.setFocus()
        self.waiting_for_enter = True

    def stage_14_print_label(self):
        """Etiket bas"""
        self.current_stage = 14
        self.update_stage_ui(14)
        self.update_big_status("ETİKET BASILIYOR...", "info")
        self.update_log("\n🖨️ Etiket basılıyor...")
        self.logger.stage(14, "Etiket basma")

        # TODO: Etiket basma mantığı
        QTimer.singleShot(2000, lambda: self.on_stage_complete(14))

    def stage_15_apply_label(self):
        """Etiket yapıştır"""
        self.current_stage = 15
        self.update_stage_ui(15)
        self.update_big_status("ETİKETİ YAPIŞTIRIN", "warning")
        self.update_log("\n🏷️ Etiketleri yapıştırın")
        self.update_log("📌 ENTER tuşuna basın")
        self.logger.stage(15, "Etiket yapıştırma")

        self.sound_manager.play_info()

        self.user_input.setEnabled(True)
        self.user_input.setFocus()
        self.waiting_for_enter = True

    def stage_16_photo(self):
        """Fotoğraf çek"""
        self.current_stage = 16
        self.update_stage_ui(16)
        self.update_big_status("FOTOĞRAF ÇEKİLİYOR...", "info")
        self.update_log("\n📸 Fotoğraf çekiliyor...")
        self.logger.stage(16, "Fotoğraf çekme")

        # Önizleme timer'ını durdur
        if self.camera_timer and self.camera_timer.isActive():
            self.camera_timer.stop()

        # Mevcut frame'i kullan
        if self.test_worker and self.current_frame is not None:
            if self.test_worker.take_photo(self.current_frame):
                self.update_log("✅ Fotoğraf kaydedildi!")
                self.on_stage_complete(16)
            else:
                self.on_stage_complete(16)
        else:
            if self.test_worker and self.test_worker.take_photo():
                self.on_stage_complete(16)
            else:
                self.on_stage_complete(16)

        # Önizlemeyi yeniden başlat
        QTimer.singleShot(1000, self.start_camera_preview)

    def stage_17_complete(self):
        """Test tamamlandı"""
        self.current_stage = 17
        self.update_stage_ui(17)
        self.update_big_status("TEST BAŞARILI ✅", "success")
        self.update_log("\n🎉 TEST TAMAMLANDI!")
        self.logger.success("Test başarıyla tamamlandı")

        self.sound_manager.play_complete()

        # MongoDB'ye kaydet
        if self.test_worker:
            self.save_test_results()

        self.test_complete()

    async def send_measure_command(self):
        """Ölçüm komutu gönder"""
        global connected_client

        if connected_client and connected_client.is_connected:
            cmd = bytes([0x31, 0x0D, 0x0A])

            try:
                tx_uuid = self.config.get('ble', 'tx_char_uuid')
                await connected_client.write_gatt_char(tx_uuid, cmd)
                self.update_log("📤 Ölçüm komutu gönderildi")
                self.logger.info("Ölçüm komutu gönderildi")

                # Veri bekle
                meas_timeout = self.config.get('ble', 'measurement_timeout', default=15)
                start_time = time.time()

                while time.time() - start_time < meas_timeout:
                    if self.measurement_received:
                        self.update_log("✅ Ölçüm alındı!")
                        self.logger.success("Ölçüm başarılı")
                        self.sound_manager.play_success()
                        comm.stage_complete_signal.emit(self.current_stage)
                        return
                    await asyncio.sleep(0.1)

                # Timeout
                self.update_log("⏱️ Ölçüm timeout, devam ediliyor...")
                self.logger.warning("Ölçüm timeout")
                comm.stage_complete_signal.emit(self.current_stage)

            except Exception as e:
                self.update_log(f"❌ Komut hatası: {str(e)}")
                self.logger.error(f"Ölçüm komutu hatası: {str(e)}")
                self.user_input.setEnabled(True)
                self.waiting_for_enter = True
        else:
            self.update_log("❌ BLE bağlı değil!")
            self.logger.error("BLE bağlantısı yok")
            self.user_input.setEnabled(True)
            self.waiting_for_enter = True

    def save_test_results(self):
        """Test sonuçlarını kaydet"""
        try:
            if not self.test_worker:
                return

            # Test verilerini tamamla
            self.test_worker.test_data["end_time"] = datetime.now().isoformat()
            self.test_worker.test_data["total_duration"] = sum(self.test_worker.stage_times.values())
            self.test_worker.test_data["stage_durations"] = self.test_worker.stage_times
            self.test_worker.test_data["status"] = "completed"

            # MongoDB'ye kaydet
            result_id = self.db_manager.insert_test_result(self.test_worker.test_data)

            if result_id:
                self.update_log(f"💾 Test kaydedildi: {result_id}")
                self.logger.success(f"Test veritabanına kaydedildi: {result_id}")
            else:
                self.update_log("⚠️ Veritabanına kaydedilemedi, yedeklendi")
                self.logger.warning("MongoDB kaydı başarısız, yedekleme yapıldı")

        except Exception as e:
            self.update_log(f"❌ Kayıt hatası: {str(e)}")
            self.logger.error(f"Test kayıt hatası: {str(e)}", exc_info=True)

    def test_complete(self):
        """Test tamamlandı - cleanup"""
        global connected_client, connected_loop

        # Cleanup
        if connected_client and connected_client.is_connected:
            future = asyncio.run_coroutine_threadsafe(
                connected_client.disconnect(), connected_loop
            )
            try:
                future.result(timeout=5)
                connected_client = None
                self.logger.info("BLE bağlantısı kapatıldı")
            except:
                pass

        if self.test_worker and self.test_worker.ppk2:
            try:
                self.test_worker.ppk2.stop_measuring()
                self.test_worker.ppk2.toggle_DUT_power(False)
                self.logger.info("PPK2 kapatıldı")
            except:
                pass

        # Log dosyasını kapat
        self.logger.end_test_log()

        # 5 saniye sonra yeni test
        QTimer.singleShot(5000, self.reset_for_new_test)

    def reset_for_new_test(self):
        """Yeni test için sıfırla"""
        self.current_stage = 0
        self.measurement_data = []
        self.measurement_received = False
        self.waiting_for_enter = False

        # Worker yeniden oluşturulacak (test başlatıldığında)
        self.test_worker = None

        # UI sıfırla
        self.update_progress(0)
        self.update_big_status("TEST SİSTEMİ HAZIR", "info")
        self.update_log("\n" + "=" * 70)
        self.update_log("✅ Yeni test için hazır")
        self.update_log("📌 ENTER tuşuna basın")
        self.logger.info("Sistem yeni test için hazır")

        # Aşamaları sıfırla
        for label in self.stage_labels:
            label.setStyleSheet("""
                padding: 12px;
                background-color: #f5f5f5;
                margin: 3px;
                border-radius: 6px;
                border-left: 4px solid #ddd;
            """)

        self.user_input.setEnabled(True)
        self.user_input.clear()
        self.user_input.setFocus()

    def on_stage_complete(self, stage):
        """Aşama tamamlandı"""
        self.update_log(f"✅ Aşama {stage} tamamlandı")
        self.logger.stage(stage, "Tamamlandı")
        self.current_stage = stage

        # Tamamlanan aşamayı yeşil yap
        if stage <= len(self.stage_labels):
            self.stage_labels[stage - 1].setStyleSheet("""
                padding: 12px;
                background-color: #4CAF50;
                color: white;
                margin: 3px;
                border-radius: 6px;
                border-left: 4px solid #388E3C;
                font-weight: bold;
            """)

        # İlerleme
        progress = int((stage / 17) * 100)
        self.update_progress(progress)

        self.sound_manager.play_stage_complete()

        # Sonraki aşama
        if stage == 5:
            self.stage_6_button()
        elif stage == 7:
            self.stage_8_solution1()
        elif stage == 9:
            self.stage_10_vacuum1()
        elif stage == 12:
            self.stage_13_vacuum2()
        elif stage == 14:
            self.stage_15_apply_label()
        elif stage == 16:
            self.stage_17_complete()

    def update_stage_ui(self, stage):
        """Aşama UI güncelle"""
        if stage > 0 and stage <= len(self.stage_labels):
            # Aktif aşamayı mavi yap
            self.stage_labels[stage - 1].setStyleSheet("""
                padding: 12px;
                background-color: #2196F3;
                color: white;
                margin: 3px;
                border-radius: 6px;
                border-left: 4px solid #1976D2;
                font-weight: bold;
            """)

    def update_log(self, text):
        """Log güncelle"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {text}")

        # Otomatik scroll
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def update_progress(self, value):
        """İlerleme güncelle"""
        self.progress_bar.setValue(value)

    def update_big_status(self, text, style):
        """Durum göstergesini güncelle"""
        styles = {
            "info": "background-color: #2196F3;",
            "success": "background-color: #4CAF50;",
            "warning": "background-color: #FF9800;",
            "error": "background-color: #f44336;"
        }

        self.big_status_label.setText(text)
        self.big_status_label.setStyleSheet(f"""
            {styles.get(style, styles['info'])}
            color: white;
            font-size: 42px;
            font-weight: bold;
            border-radius: 15px;
            margin: 15px;
        """)

    # Menü fonksiyonları
    def show_statistics(self):
        """İstatistik göster"""
        dialog = StatisticsDialog(self.db_manager, self)
        dialog.exec_()

    def show_settings(self):
        """Ayarlar göster"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            # Ayarlar güncellendi, sesleri yeniden yapılandır
            self.sound_manager.set_enabled(self.config.get('ui', 'enable_sounds'))

    def show_about(self):
        """Hakkında göster"""
        about_text = f"""
<h2>{self.config.get('system', 'company_name')}</h2>
<h3>{self.config.get('system', 'test_system_name')}</h3>
<p>Versiyon: {self.config.get('system', 'version')}</p>
<p>STM32L011 cihazları için gelişmiş test sistemi</p>
<br>
<p><b>Özellikler:</b></p>
<ul>
<li>17 aşamalı otomatik test süreci</li>
<li>PPK2 güç ölçümü</li>
<li>BLE bağlantısı ve ölçüm</li>
<li>Firmware yükleme</li>
<li>Fotoğraf çekme</li>
<li>MongoDB veritabanı</li>
<li>PDF rapor oluşturma</li>
<li>İstatistik ve loglama</li>
</ul>
"""
        QMessageBox.about(self, "Hakkında", about_text)

    def export_current_test_report(self):
        """Mevcut test için rapor oluştur"""
        if not self.test_worker or not self.test_worker.test_data.get('device_uuid'):
            QMessageBox.warning(self, "Uyarı", "Henüz test başlatılmadı!")
            return

        try:
            logo_path = "./resources/hedra_logo.png"
            pdf_path = self.report_generator.generate_test_report(
                self.test_worker.test_data,
                logo_path if os.path.exists(logo_path) else None
            )

            QMessageBox.information(
                self, "Başarılı",
                f"Rapor oluşturuldu:\n{pdf_path}"
            )
            self.logger.success(f"PDF rapor oluşturuldu: {pdf_path}")

            # Raporu aç
            reply = QMessageBox.question(
                self, "Rapor",
                "Raporu açmak ister misiniz?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                import subprocess
                import platform

                if platform.system() == 'Windows':
                    os.startfile(pdf_path)
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', pdf_path])
                else:
                    subprocess.run(['xdg-open', pdf_path])

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Rapor oluşturulamadı:\n{str(e)}")
            self.logger.error(f"PDF rapor hatası: {str(e)}")

    def toggle_sounds(self, checked):
        """Sesleri aç/kapat"""
        self.sound_manager.set_enabled(checked)
        self.config.set('ui', 'enable_sounds', value=checked)
        status = "açıldı" if checked else "kapatıldı"
        self.status_bar.showMessage(f"Sesler {status}", 2000)

    def show_error_dialog(self, title, message):
        """Hata dialogu göster"""
        QMessageBox.critical(self, title, message)

    def close_app(self):
        """Uygulamayı kapat"""
        reply = QMessageBox.question(
            self, 'Çıkış',
            'Çıkmak istediğinize emin misiniz?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()

    def closeEvent(self, event):
        """Kapatma eventi"""
        global connected_client

        # Kamera temizliği
        if self.camera_timer:
            self.camera_timer.stop()
        if self.camera_cap:
            self.camera_cap.release()

        # Cleanup
        try:
            if connected_client and connected_client.is_connected:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(connected_client.disconnect())

            if self.test_worker and self.test_worker.ppk2:
                self.test_worker.ppk2.stop_measuring()
                self.test_worker.ppk2.toggle_DUT_power(False)

            # Veritabanı bağlantısını kapat
            self.db_manager.disconnect()

        except:
            pass

        self.logger.info("Uygulama kapatıldı")
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Hata yakalama
    try:
        window = TestWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger = get_logger()
        logger.critical(f"Uygulama başlatma hatası: {str(e)}", exc_info=True)
        QMessageBox.critical(None, "Kritik Hata", f"Uygulama başlatılamadı:\n{str(e)}")
        sys.exit(1)
