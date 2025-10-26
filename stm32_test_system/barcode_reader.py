"""
Barcode Okuyucu Modülü
USB Barcode Scanner entegrasyonu (HID Keyboard emulation)
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime
import json
from pathlib import Path


class BarcodeReaderDialog(QDialog):
    """Barcode okuma dialogu"""

    barcode_scanned = pyqtSignal(str)  # Barcode okunduğunda sinyal

    def __init__(self, title="Kimlik Kartı Okutun", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 300)

        self.scanned_barcode = None
        self.init_ui()

    def init_ui(self):
        """UI oluştur"""
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Başlık
        title_label = QLabel("🔖 KİMLİK KARTI OKUTUN")
        title_font = QFont("Arial", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            color: #2196F3;
            padding: 20px;
            background-color: #E3F2FD;
            border-radius: 10px;
        """)
        layout.addWidget(title_label)

        # Animasyonlu bekleme mesajı
        self.waiting_label = QLabel("Lütfen kimlik kartınızı okutun...")
        self.waiting_label.setFont(QFont("Arial", 14))
        self.waiting_label.setAlignment(Qt.AlignCenter)
        self.waiting_label.setStyleSheet("color: #555; padding: 10px;")
        layout.addWidget(self.waiting_label)

        # Barcode input (görünmez ama focus'ta)
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Barcode buraya okunacak...")
        self.barcode_input.setFont(QFont("Consolas", 16))
        self.barcode_input.setAlignment(Qt.AlignCenter)
        self.barcode_input.setStyleSheet("""
            QLineEdit {
                padding: 15px;
                border: 3px solid #2196F3;
                border-radius: 10px;
                background-color: #F5F5F5;
                font-size: 18px;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
                background-color: white;
            }
        """)
        self.barcode_input.returnPressed.connect(self.on_barcode_entered)
        layout.addWidget(self.barcode_input)

        # Durum göstergesi
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #777; padding: 5px;")
        layout.addWidget(self.status_label)

        # Butonlar
        button_layout = QHBoxLayout()

        # Manuel giriş butonu
        manual_btn = QPushButton("Manuel Giriş")
        manual_btn.setFixedHeight(50)
        manual_btn.setFont(QFont("Arial", 12))
        manual_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        manual_btn.clicked.connect(self.manual_login)
        button_layout.addWidget(manual_btn)

        # İptal butonu
        cancel_btn = QPushButton("İptal")
        cancel_btn.setFixedHeight(50)
        cancel_btn.setFont(QFont("Arial", 12))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # Yardım metni
        help_label = QLabel("💡 İpucu: Kimlik kartınızı okutun veya manuel giriş yapın")
        help_label.setFont(QFont("Arial", 10))
        help_label.setAlignment(Qt.AlignCenter)
        help_label.setStyleSheet("color: #999; padding: 10px;")
        layout.addWidget(help_label)

        self.setLayout(layout)

        # Timer ile animasyon
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_waiting)
        self.animation_timer.start(500)
        self.animation_state = 0

        # Focus'u input'a ver
        QTimer.singleShot(100, lambda: self.barcode_input.setFocus())

    def animate_waiting(self):
        """Bekleme animasyonu"""
        dots = "." * (self.animation_state % 4)
        self.waiting_label.setText(f"Lütfen kimlik kartınızı okutun{dots}")
        self.animation_state += 1

    def on_barcode_entered(self):
        """Barcode okunduğunda"""
        barcode = self.barcode_input.text().strip()

        if not barcode:
            self.status_label.setText("❌ Geçersiz barcode!")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.barcode_input.clear()
            return

        # Barcode validasyonu
        if len(barcode) < 3:
            self.status_label.setText("❌ Barcode çok kısa!")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.barcode_input.clear()
            return

        # Başarılı okuma
        self.animation_timer.stop()
        self.status_label.setText(f"✅ Kimlik okundu: {barcode}")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

        self.scanned_barcode = barcode
        self.barcode_scanned.emit(barcode)

        # Kısa bir bekleme sonra kapat
        QTimer.singleShot(500, self.accept)

    def manual_login(self):
        """Manuel giriş için eski dialog'u aç"""
        self.reject()

    def get_barcode(self):
        """Okutulan barcode'u döndür"""
        return self.scanned_barcode


class OperatorDatabase:
    """Operatör veritabanı yönetimi"""

    def __init__(self, db_path="./config/operators.json"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.operators = self.load_operators()

    def load_operators(self):
        """Operatörleri yükle"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_operators(self):
        """Operatörleri kaydet"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.operators, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Operatör kaydetme hatası: {e}")
            return False

    def get_operator(self, barcode):
        """Barcode ile operatör bilgisi al"""
        return self.operators.get(barcode)

    def add_operator(self, barcode, name, role="operator"):
        """Yeni operatör ekle"""
        self.operators[barcode] = {
            "name": name,
            "barcode": barcode,
            "role": role,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "login_count": 0
        }
        return self.save_operators()

    def update_login(self, barcode):
        """Login bilgilerini güncelle"""
        if barcode in self.operators:
            self.operators[barcode]["last_login"] = datetime.now().isoformat()
            self.operators[barcode]["login_count"] = self.operators[barcode].get("login_count", 0) + 1
            self.save_operators()

    def get_all_operators(self):
        """Tüm operatörleri listele"""
        return list(self.operators.values())


class ManualOperatorDialog(QDialog):
    """Manuel operatör girişi veya kayıt"""

    def __init__(self, operator_db, barcode=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Operatör Bilgileri")
        self.setModal(True)
        self.resize(400, 250)

        self.operator_db = operator_db
        self.barcode = barcode
        self.operator_info = None

        self.init_ui()

    def init_ui(self):
        """UI oluştur"""
        layout = QVBoxLayout()

        # Başlık
        if self.barcode:
            title = QLabel(f"Yeni Operatör Kaydı\nBarcode: {self.barcode}")
            title.setStyleSheet("color: #2196F3; font-size: 14px; font-weight: bold;")
        else:
            title = QLabel("Manuel Operatör Girişi")
            title.setStyleSheet("color: #2196F3; font-size: 14px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Barcode input (sadece manuel giriş için)
        if not self.barcode:
            self.barcode_input = QLineEdit()
            self.barcode_input.setPlaceholderText("Operatör Barcode/ID")
            self.barcode_input.setStyleSheet("""
                padding: 10px;
                border: 2px solid #2196F3;
                border-radius: 5px;
                font-size: 14px;
            """)
            layout.addWidget(QLabel("Barcode/ID:"))
            layout.addWidget(self.barcode_input)

        # İsim input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Operatör Adı Soyadı")
        self.name_input.setStyleSheet("""
            padding: 10px;
            border: 2px solid #2196F3;
            border-radius: 5px;
            font-size: 14px;
        """)
        layout.addWidget(QLabel("Ad Soyad:"))
        layout.addWidget(self.name_input)

        # Butonlar
        button_layout = QHBoxLayout()

        ok_btn = QPushButton("Tamam")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        ok_btn.clicked.connect(self.accept_input)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("İptal")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Focus
        if self.barcode:
            self.name_input.setFocus()
        else:
            QTimer.singleShot(100, lambda: self.barcode_input.setFocus()) if hasattr(self, 'barcode_input') else None

    def accept_input(self):
        """Girişi kabul et"""
        name = self.name_input.text().strip()

        if not self.barcode:
            barcode = self.barcode_input.text().strip()
        else:
            barcode = self.barcode

        if not name or not barcode:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Uyarı", "Lütfen tüm alanları doldurun!")
            return

        # Operatör var mı kontrol et
        existing = self.operator_db.get_operator(barcode)

        if existing:
            # Varolan operatör
            self.operator_info = existing
        else:
            # Yeni operatör ekle
            if self.operator_db.add_operator(barcode, name):
                self.operator_info = self.operator_db.get_operator(barcode)
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Hata", "Operatör kaydedilemedi!")
                return

        self.accept()

    def get_operator_info(self):
        """Operatör bilgisini döndür"""
        return self.operator_info


def read_barcode_card(parent=None, operator_db=None):
    """
    Barcode okuma işlemi (kolaylık fonksiyonu)

    Returns:
        dict: Operatör bilgisi veya None
    """
    if operator_db is None:
        operator_db = OperatorDatabase()

    # Barcode okuma dialogu
    dialog = BarcodeReaderDialog(parent=parent)

    if dialog.exec_() == QDialog.Accepted:
        barcode = dialog.get_barcode()

        if barcode:
            # Operatör var mı kontrol et
            operator = operator_db.get_operator(barcode)

            if operator:
                # Varolan operatör
                operator_db.update_login(barcode)
                return operator
            else:
                # Yeni operatör - kayıt dialogu aç
                from PyQt5.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    parent,
                    "Yeni Operatör",
                    f"Bu barcode ({barcode}) kayıtlı değil.\nYeni operatör olarak kaydetmek ister misiniz?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    # Kayıt dialogu
                    register_dialog = ManualOperatorDialog(operator_db, barcode, parent)
                    if register_dialog.exec_() == QDialog.Accepted:
                        operator = register_dialog.get_operator_info()
                        if operator:
                            operator_db.update_login(operator['barcode'])
                            return operator
    else:
        # Manuel giriş seçildi
        manual_dialog = ManualOperatorDialog(operator_db, parent=parent)
        if manual_dialog.exec_() == QDialog.Accepted:
            operator = manual_dialog.get_operator_info()
            if operator:
                operator_db.update_login(operator['barcode'])
                return operator

    return None
