# Модуль отслеживания активности пользователя

import ctypes
import time
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from ctypes import wintypes

import win32gui
import win32process
import psutil


@dataclass
class AppUsage:
    name: str
    total_seconds: int = 0
    last_active: datetime = None
    sessions: List[tuple] = field(default_factory=list)


@dataclass
class ActivityState:
    current_app: str = ""
    current_window: str = ""
    is_idle: bool = False
    idle_seconds: int = 0
    keyboard_active: bool = False
    mouse_active: bool = False
    activity_level: str = "normal"  # idle, low, normal, high


class InputTracker:
    # Отслеживание ввода (клавиатура/мышь)
    
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ('cbSize', wintypes.UINT),
            ('dwTime', wintypes.DWORD),
        ]
    
    def __init__(self):
        self._last_input = self.LASTINPUTINFO()
        self._last_input.cbSize = ctypes.sizeof(self._last_input)
    
    def get_idle_duration(self) -> int:
        # Получить время простоя в секундах
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(self._last_input))
        millis = ctypes.windll.kernel32.GetTickCount() - self._last_input.dwTime
        return millis // 1000


class WindowTracker:
    # Отслеживание активного окна
    
    @staticmethod
    def get_active_window() -> tuple:
        # Получить информацию об активном окне
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                window_title = win32gui.GetWindowText(hwnd)
                return process.name().lower().replace('.exe', ''), window_title
        except Exception:
            pass
        return "", ""


class ActivityTracker:
    # Основной трекер активности
    
    def __init__(self, idle_threshold: int = 180):
        self.idle_threshold = idle_threshold
        self.input_tracker = InputTracker()
        self.window_tracker = WindowTracker()
        
        self.state = ActivityState()
        self.app_usage: Dict[str, AppUsage] = defaultdict(lambda: AppUsage(name=""))
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._listeners: List[Callable] = []
        
        self._current_session_start: Optional[datetime] = None
        self._last_app: str = ""
    
    def add_listener(self, callback: Callable):
        # Добавить слушателя изменений состояния
        self._listeners.append(callback)
    
    def _notify_listeners(self):
        # Уведомить слушателей
        for listener in self._listeners:
            try:
                listener(self.state)
            except Exception:
                pass
    
    def _update_app_usage(self, app_name: str):
        # Обновить статистику использования приложения
        now = datetime.now()
        
        if app_name != self._last_app:
            # Завершить предыдущую сессию
            if self._last_app and self._current_session_start:
                duration = (now - self._current_session_start).total_seconds()
                usage = self.app_usage[self._last_app]
                usage.total_seconds += int(duration)
                usage.sessions.append((self._current_session_start, now))
            
            # Начать новую сессию
            self._current_session_start = now
            self._last_app = app_name
            
            if app_name:
                usage = self.app_usage[app_name]
                usage.name = app_name
                usage.last_active = now
    
    def _calculate_activity_level(self) -> str:
        # Рассчитать уровень активности
        idle = self.state.idle_seconds
        
        if idle > self.idle_threshold:
            return "idle"
        elif idle > 60:
            return "low"
        elif idle < 5:
            return "high"
        return "normal"
    
    def _track_loop(self):
        # Основной цикл отслеживания
        while self._running:
            try:
                # Получить idle время
                idle_seconds = self.input_tracker.get_idle_duration()
                self.state.idle_seconds = idle_seconds
                self.state.is_idle = idle_seconds > self.idle_threshold
                
                # Активность ввода
                self.state.keyboard_active = idle_seconds < 2
                self.state.mouse_active = idle_seconds < 5
                
                # Активное окно
                app_name, window_title = self.window_tracker.get_active_window()
                self.state.current_app = app_name
                self.state.current_window = window_title
                
                # Уровень активности
                self.state.activity_level = self._calculate_activity_level()
                
                # Обновить статистику
                if not self.state.is_idle:
                    self._update_app_usage(app_name)
                
                self._notify_listeners()
                
            except Exception:
                pass
            
            time.sleep(1)
    
    def start(self):
        # Запустить отслеживание
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._track_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        # Остановить отслеживание
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def get_today_stats(self) -> Dict[str, int]:
        # Получить статистику за сегодня
        today = datetime.now().date()
        stats = {}
        
        for app_name, usage in self.app_usage.items():
            total = 0
            for start, end in usage.sessions:
                if start.date() == today:
                    total += int((end - start).total_seconds())
            if total > 0:
                stats[app_name] = total
        
        return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
    
    def get_category_time(self, apps: List[str]) -> int:
        # Получить общее время для категории приложений
        total = 0
        for app in apps:
            if app in self.app_usage:
                total += self.app_usage[app].total_seconds
        return total
