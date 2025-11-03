"""
Gelişmiş Loglama Modülü
Hem dosyaya hem de konsola loglama yapabilir
Farklı log seviyeleri destekler
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class TestLogger:
    """Test sistemi için gelişmiş logger sınıfı"""

    def __init__(self, log_dir="./logs", max_bytes=10*1024*1024, backup_count=5):
        """
        Args:
            log_dir: Log dosyalarının kaydedileceği dizin
            max_bytes: Maksimum log dosya boyutu (byte)
            backup_count: Tutulacak yedek log dosyası sayısı
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Ana logger
        self.logger = logging.getLogger("STM32_TestSystem")
        self.logger.setLevel(logging.DEBUG)

        # Mevcut handler'ları temizle
        self.logger.handlers.clear()

        # Dosya handler - genel log
        log_file = self.log_dir / f"test_system_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Konsol handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Hata log dosyası - sadece ERROR ve CRITICAL
        error_log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        self.logger.addHandler(error_handler)

        # Test sonuçları log dosyası
        self.test_log_file = None

    def start_test_log(self, device_uuid):
        """Belirli bir cihaz için test log dosyası başlat"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.test_log_file = self.log_dir / f"test_{device_uuid}_{timestamp}.log"

        test_handler = logging.FileHandler(self.test_log_file, encoding='utf-8')
        test_handler.setLevel(logging.DEBUG)
        test_formatter = logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        test_handler.setFormatter(test_formatter)
        test_handler.set_name('test_handler')  # İsim ver ki sonra bulabilelim
        self.logger.addHandler(test_handler)

        self.info(f"=== Test başladı: {device_uuid} ===")

    def end_test_log(self):
        """Test log dosyasını kapat"""
        # Test handler'ını bul ve kaldır
        for handler in self.logger.handlers[:]:
            if handler.name == 'test_handler':
                handler.close()
                self.logger.removeHandler(handler)

        if self.test_log_file:
            self.info(f"Test log kaydedildi: {self.test_log_file}")
            self.test_log_file = None

    def debug(self, message):
        """Debug seviyesi log"""
        self.logger.debug(message)

    def info(self, message):
        """Info seviyesi log"""
        self.logger.info(message)

    def warning(self, message):
        """Warning seviyesi log"""
        self.logger.warning(message)

    def error(self, message, exc_info=False):
        """Error seviyesi log"""
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message, exc_info=False):
        """Critical seviyesi log"""
        self.logger.critical(message, exc_info=exc_info)

    def stage(self, stage_num, message):
        """Aşama log mesajı"""
        self.info(f"[AŞAMA {stage_num}] {message}")

    def success(self, message):
        """Başarı log mesajı"""
        self.info(f"✅ {message}")

    def failure(self, message):
        """Başarısızlık log mesajı"""
        self.error(f"❌ {message}")

    def measurement(self, data):
        """Ölçüm verisi log"""
        self.info(f"📊 Ölçüm: {data}")

    def get_log_stats(self):
        """Log istatistiklerini al"""
        stats = {
            "log_dir": str(self.log_dir),
            "log_files": [],
            "total_size": 0
        }

        if self.log_dir.exists():
            for log_file in self.log_dir.glob("*.log"):
                size = log_file.stat().st_size
                stats["log_files"].append({
                    "name": log_file.name,
                    "size": size,
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
                stats["total_size"] += size

        return stats

    def cleanup_old_logs(self, days=30):
        """Eski log dosyalarını temizle"""
        if not self.log_dir.exists():
            return 0

        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0

        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                    self.info(f"Eski log dosyası silindi: {log_file.name}")
                except Exception as e:
                    self.error(f"Log dosyası silinemedi: {log_file.name} - {e}")

        return deleted_count


# Global logger instance
_logger = None

def get_logger():
    """Global logger instance'ını al"""
    global _logger
    if _logger is None:
        _logger = TestLogger()
    return _logger
