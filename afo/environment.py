# Модуль управления окружением

import ctypes
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum

from .analyzer import UserMode, TimeOfDay, AnalysisResult
from .config import Config


class AmbientSound(Enum):
    RAIN = "rain"
    FOREST = "forest"
    CAFE = "cafe"
    OCEAN = "ocean"
    FIRE = "fire"
    WHITE_NOISE = "white_noise"
    NONE = "none"


@dataclass
class EnvironmentState:
    sound: AmbientSound = AmbientSound.NONE
    sound_volume: float = 0.3
    night_mode_active: bool = False
    color_temperature: int = 6500
    notifications_filtered: bool = False
    focus_mode: bool = False


class DisplayController:
    # Управление дисплеем
    
    def __init__(self):
        self._gamma_ramp = None
        self._original_gamma = None
    
    def set_color_temperature(self, temperature: int):
        # Установить цветовую температуру (1000-10000 Кельвинов)
        temp = temperature / 100
        
        # Красный
        if temp <= 66:
            red = 255
        else:
            red = temp - 60
            red = 329.698727446 * (red ** -0.1332047592)
            red = max(0, min(255, red))
        
        # Зелёный
        if temp <= 66:
            green = temp
            green = 99.4708025861 * (green ** 0.5) - 161.1195681661 if temp > 0 else 0
        else:
            green = temp - 60
            green = 288.1221695283 * (green ** -0.0755148492)
        green = max(0, min(255, green))
        
        # Синий
        if temp >= 66:
            blue = 255
        elif temp <= 19:
            blue = 0
        else:
            blue = temp - 10
            blue = 138.5177312231 * (blue ** 0.5) - 305.0447927307
            blue = max(0, min(255, blue))
        
        self._apply_gamma(red / 255, green / 255, blue / 255)
    
    def _apply_gamma(self, r_factor: float, g_factor: float, b_factor: float):
        # Применить гамма-коррекцию
        try:
            # Создать гамма-рампу
            ramp = (ctypes.c_ushort * 256 * 3)()
            
            for i in range(256):
                ramp[0][i] = int(min(65535, i * 256 * r_factor))
                ramp[1][i] = int(min(65535, i * 256 * g_factor))
                ramp[2][i] = int(min(65535, i * 256 * b_factor))
            
            # Получить DC экрана
            hdc = ctypes.windll.user32.GetDC(0)
            ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
            ctypes.windll.user32.ReleaseDC(0, hdc)
            
        except Exception:
            pass
    
    def reset_gamma(self):
        # Сбросить гамму к стандартной
        self.set_color_temperature(6500)


class SoundController:
    # Управление фоновыми звуками
    
    def __init__(self, sounds_dir: Path = None):
        self.sounds_dir = sounds_dir or Path(__file__).parent / 'sounds'
        self._player = None
        self._current_sound: AmbientSound = AmbientSound.NONE
        self._volume: float = 0.3
        self._play_thread = None
        self._stop_flag = False
        
        # Пути к звуковым файлам
        self.sound_files: Dict[AmbientSound, str] = {
            AmbientSound.RAIN: "rain.mp3",
            AmbientSound.FOREST: "forest.mp3",
            AmbientSound.CAFE: "cafe.mp3",
            AmbientSound.OCEAN: "ocean.mp3",
            AmbientSound.FIRE: "fire.mp3",
            AmbientSound.WHITE_NOISE: "white_noise.mp3"
        }
    
    def play(self, sound: AmbientSound, volume: float = None):
        # Воспроизвести фоновый звук
        if volume is not None:
            self._volume = volume
        
        if sound == AmbientSound.NONE:
            self.stop()
            return
        
        if sound == self._current_sound and self._player:
            return
        
        self.stop()
        
        sound_file = self.sounds_dir / self.sound_files.get(sound, "")
        if not sound_file.exists():
            print(f"Звуковой файл не найден: {sound_file}")
            return
        
        self._current_sound = sound
        self._stop_flag = False
        
        # Запустить воспроизведение в отдельном потоке
        self._play_thread = threading.Thread(
            target=self._play_loop, 
            args=(str(sound_file),),
            daemon=True
        )
        self._play_thread.start()
    
    def _play_loop(self, file_path: str):
        # Цикл воспроизведения через Windows Media Player COM
        try:
            import pythoncom
            pythoncom.CoInitialize()
            
            from win32com.client import Dispatch
            self._player = Dispatch("WMPlayer.OCX")
            self._player.settings.autoStart = True
            self._player.settings.setMode("loop", True)
            self._player.settings.volume = int(self._volume * 100)
            self._player.URL = file_path
            
            # Держим поток живым пока играет
            while not self._stop_flag and self._player:
                time.sleep(0.5)
                
        except ImportError:
            # Fallback на PowerShell
            self._play_powershell(file_path)
        except Exception as e:
            print(f"Ошибка воспроизведения: {e}")
        finally:
            try:
                pythoncom.CoUninitialize()
            except:
                pass
    
    def _play_powershell(self, file_path: str):
        # Fallback через PowerShell MediaPlayer
        try:
            ps_script = f'''
            Add-Type -AssemblyName PresentationCore
            $player = New-Object System.Windows.Media.MediaPlayer
            $player.Open([Uri]"{file_path}")
            $player.Volume = {self._volume}
            $player.Play()
            while ($true) {{ Start-Sleep -Seconds 1 }}
            '''
            self._player = subprocess.Popen(
                ["powershell", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self._player.wait()
        except Exception as e:
            print(f"PowerShell fallback error: {e}")
    
    def stop(self):
        # Остановить воспроизведение
        self._stop_flag = True
        
        if self._player:
            try:
                if hasattr(self._player, 'controls'):
                    self._player.controls.stop()
                    self._player.close()
                elif hasattr(self._player, 'terminate'):
                    self._player.terminate()
            except Exception:
                pass
            self._player = None
        
        self._current_sound = AmbientSound.NONE
    
    def set_volume(self, volume: float):
        # Установить громкость (0.0 - 1.0)
        self._volume = max(0.0, min(1.0, volume))
        if self._player and hasattr(self._player, 'settings'):
            try:
                self._player.settings.volume = int(self._volume * 100)
            except:
                pass


class NotificationController:
    # Управление уведомлениями
    
    def __init__(self):
        self._focus_assist_enabled = False
    
    def enable_focus_assist(self):
        # Включить режим фокуса Windows
        if self._focus_assist_enabled:
            return
        
        try:
            # Установить Focus Assist через реестр
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default$windows.data.notifications.quiethourssettings\windows.data.notifications.quiethourssettings"
            # В реальной реализации здесь будет код для включения Focus Assist
            self._focus_assist_enabled = True
        except Exception:
            pass
    
    def disable_focus_assist(self):
        # Выключить режим фокуса
        self._focus_assist_enabled = False
    
    def is_focus_assist_enabled(self) -> bool:
        return self._focus_assist_enabled


class EnvironmentController:
    # Главный контроллер окружения
    
    def __init__(self, config: Config):
        self.config = config
        self.state = EnvironmentState()
        
        self.display = DisplayController()
        self.sound = SoundController()
        self.notifications = NotificationController()
        
        self._auto_adjust = True
        self._transition_lock = threading.Lock()
    
    def apply_for_mode(self, analysis: AnalysisResult):
        # Применить настройки для режима
        if not self._auto_adjust:
            return
        
        with self._transition_lock:
            mode = analysis.mode
            time_of_day = analysis.time_of_day
            
            # Настройки в зависимости от режима
            if mode == UserMode.DEEP_WORK:
                self._apply_deep_work_settings(time_of_day)
            elif mode == UserMode.RESEARCH:
                self._apply_research_settings(time_of_day)
            elif mode == UserMode.CREATIVE:
                self._apply_creative_settings(time_of_day)
            elif mode == UserMode.ENTERTAINMENT:
                self._apply_entertainment_settings(time_of_day)
            elif mode == UserMode.BREAK:
                self._apply_break_settings()
            elif mode == UserMode.IDLE:
                self._apply_idle_settings()
            
            # Ночной режим
            if time_of_day in [TimeOfDay.EVENING, TimeOfDay.NIGHT]:
                if self.config.display.night_mode_enabled:
                    self._enable_night_mode()
            else:
                self._disable_night_mode()
    
    def _apply_deep_work_settings(self, time_of_day: TimeOfDay):
        # Настройки для глубокой работы
        # Фоновый звук
        if self.config.sound.enabled:
            sounds = self.config.sound.preferred_sounds
            if sounds and 'rain' in sounds:
                self.sound.play(AmbientSound.RAIN, self.config.sound.volume)
            elif sounds and 'cafe' in sounds:
                self.sound.play(AmbientSound.CAFE, self.config.sound.volume)
            else:
                self.sound.play(AmbientSound.WHITE_NOISE, self.config.sound.volume)
        
        # Фильтрация уведомлений
        if self.config.notifications.filter_enabled:
            self.notifications.enable_focus_assist()
            self.state.notifications_filtered = True
        
        self.state.focus_mode = True
    
    def _apply_research_settings(self, time_of_day: TimeOfDay):
        # Настройки для исследования
        if self.config.sound.enabled:
            self.sound.play(AmbientSound.CAFE, self.config.sound.volume * 0.7)
        
        self.state.focus_mode = False
        self.state.notifications_filtered = False
        self.notifications.disable_focus_assist()
    
    def _apply_creative_settings(self, time_of_day: TimeOfDay):
        # Настройки для творческой работы
        if self.config.sound.enabled:
            self.sound.play(AmbientSound.FOREST, self.config.sound.volume)
        
        if self.config.notifications.filter_enabled:
            self.notifications.enable_focus_assist()
            self.state.notifications_filtered = True
        
        self.state.focus_mode = True
    
    def _apply_entertainment_settings(self, time_of_day: TimeOfDay):
        # Настройки для развлечений
        self.sound.stop()
        self.notifications.disable_focus_assist()
        
        self.state.sound = AmbientSound.NONE
        self.state.focus_mode = False
        self.state.notifications_filtered = False
    
    def _apply_break_settings(self):
        # Настройки для перерыва
        if self.config.sound.enabled:
            self.sound.play(AmbientSound.FOREST, self.config.sound.volume * 0.5)
        
        self.notifications.disable_focus_assist()
        self.state.focus_mode = False
    
    def _apply_idle_settings(self):
        # Настройки для простоя
        self.sound.stop()
        self.state.sound = AmbientSound.NONE
    
    def _enable_night_mode(self):
        # Включить ночной режим
        if self.state.night_mode_active:
            return
        
        self.display.set_color_temperature(self.config.display.color_temperature)
        self.state.night_mode_active = True
        self.state.color_temperature = self.config.display.color_temperature
    
    def _disable_night_mode(self):
        # Выключить ночной режим
        if not self.state.night_mode_active:
            return
        
        self.display.reset_gamma()
        self.state.night_mode_active = False
        self.state.color_temperature = 6500
    
    def set_auto_adjust(self, enabled: bool):
        # Включить/выключить автоподстройку
        self._auto_adjust = enabled
    
    def reset(self):
        # Сбросить все настройки
        self.sound.stop()
        self.display.reset_gamma()
        self.notifications.disable_focus_assist()
        
        self.state = EnvironmentState()
