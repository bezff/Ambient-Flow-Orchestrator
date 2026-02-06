# Pomodoro таймер

import threading
import time
from datetime import datetime, date
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional
from enum import Enum

from .config import PomodoroSettings


class PomodoroPhase(Enum):
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    IDLE = "idle"


@dataclass
class PomodoroStats:
    date: str = ""
    completed_pomodoros: int = 0
    total_work_minutes: int = 0
    total_break_minutes: int = 0


@dataclass
class PomodoroState:
    phase: PomodoroPhase = PomodoroPhase.IDLE
    running: bool = False
    seconds_left: int = 0
    current_pomodoro: int = 0
    completed_today: int = 0


class PomodoroTimer:
    
    def __init__(self, settings: PomodoroSettings):
        self.settings = settings
        self.state = PomodoroState()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # колбэки для событий
        self._on_tick: Optional[Callable] = None
        self._on_phase_complete: Optional[Callable] = None
        self._on_pomodoro_complete: Optional[Callable] = None
        
        # статистика по дням
        self._stats: Dict[str, PomodoroStats] = {}
        self._load_today_stats()
    
    def _load_today_stats(self):
        today = date.today().isoformat()
        if today not in self._stats:
            self._stats[today] = PomodoroStats(date=today)
        self.state.completed_today = self._stats[today].completed_pomodoros
    
    def _get_today_stats(self) -> PomodoroStats:
        today = date.today().isoformat()
        if today not in self._stats:
            self._stats[today] = PomodoroStats(date=today)
        return self._stats[today]
    
    def set_callbacks(self, on_tick: Callable = None, on_phase_complete: Callable = None,
                     on_pomodoro_complete: Callable = None):
        self._on_tick = on_tick
        self._on_phase_complete = on_phase_complete
        self._on_pomodoro_complete = on_pomodoro_complete
    
    def update_settings(self, settings: PomodoroSettings):
        with self._lock:
            self.settings = settings
    
    def start(self, phase: PomodoroPhase = None):
        if self.state.running:
            return
        
        with self._lock:
            if phase:
                self.state.phase = phase
            elif self.state.phase == PomodoroPhase.IDLE:
                self.state.phase = PomodoroPhase.WORK
            
            # установить время в зависимости от фазы
            if self.state.phase == PomodoroPhase.WORK:
                self.state.seconds_left = self.settings.work_minutes * 60
            elif self.state.phase == PomodoroPhase.SHORT_BREAK:
                self.state.seconds_left = self.settings.short_break_minutes * 60
            elif self.state.phase == PomodoroPhase.LONG_BREAK:
                self.state.seconds_left = self.settings.long_break_minutes * 60
            
            self.state.running = True
            self._stop_event.clear()
        
        self._thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._thread.start()
    
    def pause(self):
        with self._lock:
            self.state.running = False
            self._stop_event.set()
    
    def resume(self):
        if self.state.running or self.state.seconds_left <= 0:
            return
        
        with self._lock:
            self.state.running = True
            self._stop_event.clear()
        
        self._thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        with self._lock:
            self.state.running = False
            self.state.phase = PomodoroPhase.IDLE
            self.state.seconds_left = 0
            self._stop_event.set()
    
    def skip(self):
        # пропустить текущую фазу
        was_running = self.state.running
        self.pause()
        self._complete_phase()
        
        if was_running and self.state.phase != PomodoroPhase.IDLE:
            if self.state.phase == PomodoroPhase.WORK or self.settings.auto_start_breaks:
                self.start()
    
    def _timer_loop(self):
        while not self._stop_event.is_set():
            time.sleep(1)
            
            with self._lock:
                if not self.state.running:
                    break
                
                self.state.seconds_left -= 1
                
                if self._on_tick:
                    try:
                        self._on_tick(self.state)
                    except Exception:
                        pass
                
                if self.state.seconds_left <= 0:
                    self.state.running = False
                    break
        
        if self.state.seconds_left <= 0:
            self._complete_phase()
    
    def _complete_phase(self):
        stats = self._get_today_stats()
        prev_phase = self.state.phase
        
        with self._lock:
            if prev_phase == PomodoroPhase.WORK:
                self.state.current_pomodoro += 1
                self.state.completed_today += 1
                stats.completed_pomodoros += 1
                stats.total_work_minutes += self.settings.work_minutes
                
                if self._on_pomodoro_complete:
                    try:
                        self._on_pomodoro_complete(self.state.completed_today)
                    except Exception:
                        pass
                
                # следующая фаза - перерыв
                if self.state.current_pomodoro >= self.settings.pomodoros_until_long_break:
                    self.state.phase = PomodoroPhase.LONG_BREAK
                    self.state.current_pomodoro = 0
                else:
                    self.state.phase = PomodoroPhase.SHORT_BREAK
                
                if self.settings.auto_start_breaks:
                    self.start()
            
            elif prev_phase in [PomodoroPhase.SHORT_BREAK, PomodoroPhase.LONG_BREAK]:
                duration = self.settings.short_break_minutes if prev_phase == PomodoroPhase.SHORT_BREAK else self.settings.long_break_minutes
                stats.total_break_minutes += duration
                
                self.state.phase = PomodoroPhase.WORK
                
                if self.settings.auto_start_work:
                    self.start()
            else:
                self.state.phase = PomodoroPhase.IDLE
        
        if self._on_phase_complete:
            try:
                self._on_phase_complete(prev_phase, self.state.phase)
            except Exception:
                pass
    
    def get_status(self) -> Dict:
        stats = self._get_today_stats()
        
        return {
            'phase': self.state.phase.value,
            'running': self.state.running,
            'seconds_left': self.state.seconds_left,
            'current_pomodoro': self.state.current_pomodoro,
            'completed_today': self.state.completed_today,
            'total_work_minutes': stats.total_work_minutes,
            'total_break_minutes': stats.total_break_minutes,
            'settings': {
                'work_minutes': self.settings.work_minutes,
                'short_break_minutes': self.settings.short_break_minutes,
                'long_break_minutes': self.settings.long_break_minutes,
                'pomodoros_until_long_break': self.settings.pomodoros_until_long_break,
                'auto_start_breaks': self.settings.auto_start_breaks,
                'auto_start_work': self.settings.auto_start_work,
            }
        }
    
    def get_history(self, days: int = 7) -> List[Dict]:
        result = []
        for date_str, stats in sorted(self._stats.items(), reverse=True)[:days]:
            result.append({
                'date': date_str,
                'pomodoros': stats.completed_pomodoros,
                'work_minutes': stats.total_work_minutes,
                'break_minutes': stats.total_break_minutes,
            })
        return result
