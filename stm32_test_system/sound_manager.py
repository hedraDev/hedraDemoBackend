"""
Ses Bildirimleri Modülü
Test aşamalarında ses bildirimleri çalar
"""

import os
import platform
import subprocess
from pathlib import Path
from PyQt5.QtMultimedia import QSound


class SoundManager:
    """Ses bildirimlerini yöneten sınıf"""

    def __init__(self, sounds_dir: str = "./sounds", enabled: bool = True):
        """
        Args:
            sounds_dir: Ses dosyalarının bulunduğu dizin
            enabled: Seslerin aktif olup olmadığı
        """
        self.sounds_dir = Path(sounds_dir)
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = enabled

        # Ses dosyaları
        self.sounds = {
            'success': self.sounds_dir / 'success.wav',
            'error': self.sounds_dir / 'error.wav',
            'warning': self.sounds_dir / 'warning.wav',
            'info': self.sounds_dir / 'info.wav',
            'complete': self.sounds_dir / 'complete.wav',
            'stage_complete': self.sounds_dir / 'stage_complete.wav'
        }

        # QSound nesneleri
        self.qsounds = {}
        self._init_sounds()

    def _init_sounds(self):
        """Ses dosyalarını yükle"""
        for sound_name, sound_path in self.sounds.items():
            if sound_path.exists():
                try:
                    self.qsounds[sound_name] = QSound(str(sound_path))
                except Exception as e:
                    print(f"Ses yükleme hatası ({sound_name}): {e}")

    def play(self, sound_name: str):
        """
        Ses çal

        Args:
            sound_name: Çalınacak sesin adı (success, error, warning, info, complete, stage_complete)
        """
        if not self.enabled:
            return

        if sound_name in self.qsounds:
            try:
                self.qsounds[sound_name].play()
            except Exception as e:
                print(f"Ses çalma hatası ({sound_name}): {e}")
                # QSound başarısız olursa sistem ses fonksiyonunu dene
                self._play_system_sound(sound_name)
        else:
            # Ses dosyası yoksa sistem sesi çal
            self._play_system_sound(sound_name)

    def _play_system_sound(self, sound_type: str):
        """Platform bağımsız sistem sesi çal"""
        system = platform.system()

        try:
            if system == 'Windows':
                # Windows için winsound kullan
                import winsound
                if sound_type in ['error', 'warning']:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                elif sound_type == 'success':
                    winsound.MessageBeep(winsound.MB_OK)
                else:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)

            elif system == 'Darwin':  # macOS
                # macOS için afplay veya system beep
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'],
                             capture_output=True, timeout=2)

            elif system == 'Linux':
                # Linux için paplay veya beep
                subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'],
                             capture_output=True, timeout=2)

        except Exception as e:
            # Hiçbir yöntem çalışmazsa sessiz başarısız ol
            pass

    def play_success(self):
        """Başarı sesi çal"""
        self.play('success')

    def play_error(self):
        """Hata sesi çal"""
        self.play('error')

    def play_warning(self):
        """Uyarı sesi çal"""
        self.play('warning')

    def play_info(self):
        """Bilgi sesi çal"""
        self.play('info')

    def play_complete(self):
        """Tamamlanma sesi çal"""
        self.play('complete')

    def play_stage_complete(self):
        """Aşama tamamlanma sesi çal"""
        self.play('stage_complete')

    def set_enabled(self, enabled: bool):
        """Sesleri aç/kapat"""
        self.enabled = enabled

    def is_enabled(self) -> bool:
        """Seslerin aktif olup olmadığını kontrol et"""
        return self.enabled

    def create_default_sounds(self):
        """
        Varsayılan ses dosyaları oluştur (basit bip sesleri)
        Not: Gerçek projede WAV dosyaları kullanılmalı
        """
        # Bu fonksiyon opsiyonel - gerçek ses dosyaları eklenebilir
        print("Ses dosyaları için lütfen WAV dosyalarını şu dizine ekleyin:")
        print(f"  {self.sounds_dir}")
        print("Gerekli dosyalar:")
        for sound_name in self.sounds.keys():
            print(f"  - {sound_name}.wav")


# Global sound manager instance
_sound_manager = None

def get_sound_manager():
    """Global sound manager instance'ını al"""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager
