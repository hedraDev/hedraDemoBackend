"""
Yapılandırma Yönetim Modülü
JSON tabanlı yapılandırma dosyası yönetimi
"""

import json
import os
from pathlib import Path
from typing import Any, Dict


class ConfigManager:
    """Sistem yapılandırmasını yöneten sınıf"""

    DEFAULT_CONFIG = {
        "system": {
            "version": "2.0.0",
            "company_name": "HEDRA",
            "test_system_name": "STM32L011 Test Sistemi"
        },
        "hardware": {
            "firmware_path": "./firmware/stm32l011_firmware.hex",
            "stm32_target": "stm32l011f4",
            "ppk2_voltage": 3000,
            "pyocd_frequency": 1000000
        },
        "ble": {
            "uart_service_uuid": "6E400001-B5A3-F393-E0A9-E50E24DCCA9E",
            "tx_char_uuid": "6E400002-B5A3-F393-E0A9-E50E24DCCA9E",
            "rx_char_uuid": "6E400003-B5A3-F393-E0A9-E50E24DCCA9E",
            "scan_timeout": 10.0,
            "connection_timeout": 30.0,
            "measurement_timeout": 15.0
        },
        "camera": {
            "width": 640,
            "height": 480,
            "fps": 30,
            "preview_refresh_ms": 30
        },
        "database": {
            "mongodb_uri": "mongodb://localhost:27017/",
            "db_name": "stm32_test_db",
            "collection_name": "test_results",
            "backup_enabled": True
        },
        "paths": {
            "logs": "./logs",
            "photos": "./photos",
            "backup": "./backup",
            "firmware": "./firmware",
            "reports": "./reports",
            "sounds": "./sounds"
        },
        "ui": {
            "theme": "modern_blue",
            "enable_animations": True,
            "enable_sounds": True,
            "window_width": 1600,
            "window_height": 1000
        },
        "timeouts": {
            "stage_timeout": 300,
            "retry_attempts": 3,
            "retry_delay": 2
        },
        "logging": {
            "level": "INFO",
            "max_file_size_mb": 10,
            "backup_count": 5,
            "console_output": True
        }
    }

    def __init__(self, config_path="./config/config.json"):
        """
        Args:
            config_path: Yapılandırma dosyasının yolu
        """
        self.config_path = Path(config_path)
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Yapılandırma dosyasını yükle veya varsayılanı oluştur"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Eksik anahtarları varsayılanlarla doldur
                    return self._merge_with_defaults(config)
            except Exception as e:
                print(f"Config yükleme hatası: {e}. Varsayılan config kullanılıyor.")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Dosya yoksa oluştur
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()

    def _merge_with_defaults(self, config: Dict) -> Dict:
        """Mevcut config'i varsayılanlarla birleştir"""
        result = self.DEFAULT_CONFIG.copy()

        def deep_update(base, update):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_update(base[key], value)
                else:
                    base[key] = value

        deep_update(result, config)
        return result

    def save_config(self, config: Dict = None):
        """Yapılandırmayı dosyaya kaydet"""
        if config is None:
            config = self.config

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Config kaydetme hatası: {e}")
            return False

    def get(self, *keys, default=None):
        """
        İç içe geçmiş yapılandırma değerini al
        Örnek: get('database', 'mongodb_uri')
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, *keys, value):
        """
        İç içe geçmiş yapılandırma değerini ayarla
        Örnek: set('database', 'mongodb_uri', value='mongodb://...')
        """
        if len(keys) < 1:
            return False

        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value
        return self.save_config()

    def get_all(self) -> Dict:
        """Tüm yapılandırmayı al"""
        return self.config.copy()

    def reset_to_defaults(self):
        """Yapılandırmayı varsayılanlara döndür"""
        self.config = self.DEFAULT_CONFIG.copy()
        return self.save_config()

    def create_directories(self):
        """Yapılandırmada tanımlı dizinleri oluştur"""
        paths = self.get('paths', default={})
        created = []

        for path_key, path_value in paths.items():
            path = Path(path_value)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    created.append(str(path))
                except Exception as e:
                    print(f"Dizin oluşturma hatası ({path}): {e}")

        return created

    def validate(self) -> tuple[bool, list]:
        """Yapılandırmayı doğrula"""
        errors = []

        # Firmware dosyası kontrolü
        firmware_path = self.get('hardware', 'firmware_path')
        if firmware_path and not os.path.exists(firmware_path):
            errors.append(f"Firmware dosyası bulunamadı: {firmware_path}")

        # MongoDB URI kontrolü
        mongodb_uri = self.get('database', 'mongodb_uri')
        if not mongodb_uri:
            errors.append("MongoDB URI tanımlanmamış")

        # BLE UUID kontrolü
        ble_uuids = ['uart_service_uuid', 'tx_char_uuid', 'rx_char_uuid']
        for uuid_key in ble_uuids:
            uuid_value = self.get('ble', uuid_key)
            if not uuid_value or len(uuid_value) != 36:
                errors.append(f"Geçersiz BLE UUID: {uuid_key}")

        return len(errors) == 0, errors


# Global config instance
_config = None

def get_config():
    """Global config instance'ını al"""
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config
