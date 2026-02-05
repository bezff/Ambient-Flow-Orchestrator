# Анализатор состояния пользователя

from datetime import datetime, time
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

from .tracker import ActivityState


class UserMode(Enum):
    DEEP_WORK = "deep_work"
    RESEARCH = "research"
    CREATIVE = "creative"
    COMMUNICATION = "communication"
    ENTERTAINMENT = "entertainment"
    BREAK = "break"
    IDLE = "idle"


class TimeOfDay(Enum):
    MORNING = "morning"      # 6-12
    AFTERNOON = "afternoon"  # 12-17
    EVENING = "evening"      # 17-21
    NIGHT = "night"          # 21-6


@dataclass
class AnalysisResult:
    mode: UserMode
    confidence: float
    time_of_day: TimeOfDay
    work_session_minutes: int
    should_take_break: bool
    recommendations: List[str]


class StateAnalyzer:
    # Анализатор состояния пользователя
    
    # Паттерны приложений по категориям
    DEEP_WORK_APPS = [
        'code', 'devenv', 'pycharm', 'idea', 'webstorm', 'rider',
        'sublime_text', 'notepad++', 'vim', 'nvim', 'emacs',
        'word', 'excel', 'powerpoint', 'photoshop', 'illustrator',
        'figma', 'sketch', 'blender', 'unity', 'unreal'
    ]
    
    RESEARCH_APPS = [
        'chrome', 'firefox', 'edge', 'brave', 'opera',
        'acrobat', 'foxitreader', 'kindle', 'notion', 'obsidian',
        'onenote', 'evernote'
    ]
    
    COMMUNICATION_APPS = [
        'teams', 'slack', 'discord', 'zoom', 'skype', 'telegram',
        'whatsapp', 'outlook', 'thunderbird', 'mail'
    ]
    
    ENTERTAINMENT_APPS = [
        'vlc', 'spotify', 'netflix', 'steam', 'epicgameslauncher',
        'origin', 'battle.net', 'twitch', 'youtube'
    ]
    
    CREATIVE_KEYWORDS = [
        'design', 'draw', 'paint', 'music', 'video', 'edit',
        'premiere', 'aftereffects', 'audacity', 'fl studio'
    ]
    
    def __init__(self, work_apps: List[str] = None, entertainment_apps: List[str] = None):
        self.work_apps = work_apps or self.DEEP_WORK_APPS
        self.entertainment_apps = entertainment_apps or self.ENTERTAINMENT_APPS
        
        self._work_session_start: Optional[datetime] = None
        self._last_mode: UserMode = UserMode.IDLE
        self._mode_history: List[tuple] = []  # (timestamp, mode)
    
    @staticmethod
    def get_time_of_day() -> TimeOfDay:
        # Определить время суток
        hour = datetime.now().hour
        
        if 6 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 21:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT
    
    def _detect_mode(self, state: ActivityState) -> tuple:
        # Определить режим работы
        app = state.current_app.lower()
        window = state.current_window.lower()
        
        if state.is_idle:
            return UserMode.IDLE, 1.0
        
        # Проверка глубокой работы
        for work_app in self.DEEP_WORK_APPS:
            if work_app in app:
                if state.activity_level == 'high':
                    return UserMode.DEEP_WORK, 0.9
                return UserMode.DEEP_WORK, 0.7
        
        # Проверка коммуникации
        for comm_app in self.COMMUNICATION_APPS:
            if comm_app in app:
                return UserMode.COMMUNICATION, 0.85
        
        # Проверка развлечений
        for ent_app in self.ENTERTAINMENT_APPS:
            if ent_app in app:
                return UserMode.ENTERTAINMENT, 0.9
        
        # Проверка креатива по ключевым словам
        for keyword in self.CREATIVE_KEYWORDS:
            if keyword in app or keyword in window:
                return UserMode.CREATIVE, 0.75
        
        # Браузер - может быть работа или исследование
        for browser in self.RESEARCH_APPS:
            if browser in app:
                # Попробуем определить по заголовку
                work_keywords = ['github', 'stackoverflow', 'docs', 'documentation', 
                               'google docs', 'sheets', 'drive', 'jira', 'confluence']
                for kw in work_keywords:
                    if kw in window:
                        return UserMode.RESEARCH, 0.7
                
                entertainment_keywords = ['youtube', 'netflix', 'twitch', 'reddit', 
                                         'twitter', 'facebook', 'instagram']
                for kw in entertainment_keywords:
                    if kw in window:
                        return UserMode.ENTERTAINMENT, 0.8
                
                return UserMode.RESEARCH, 0.5
        
        return UserMode.IDLE, 0.3
    
    def _get_work_session_minutes(self) -> int:
        # Получить длительность текущей рабочей сессии
        if self._work_session_start is None:
            return 0
        return int((datetime.now() - self._work_session_start).total_seconds() / 60)
    
    def _should_take_break(self, work_minutes: int, break_after: int = 50) -> bool:
        # Проверить, нужен ли перерыв
        return work_minutes >= break_after
    
    def _get_recommendations(self, mode: UserMode, time_of_day: TimeOfDay, 
                            work_minutes: int) -> List[str]:
        # Сформировать рекомендации
        recs = []
        
        if work_minutes > 90:
            recs.append("Долгая работа без перерыва. Отдохните 15 минут.")
        elif work_minutes > 50:
            recs.append("Хорошее время для короткого перерыва.")
        
        if time_of_day == TimeOfDay.NIGHT and mode in [UserMode.DEEP_WORK, UserMode.RESEARCH]:
            recs.append("Поздний час. Рекомендуется завершить работу.")
        
        if time_of_day == TimeOfDay.EVENING and mode == UserMode.DEEP_WORK:
            recs.append("Включён ночной режим для комфорта глаз.")
        
        if mode == UserMode.ENTERTAINMENT and time_of_day == TimeOfDay.MORNING:
            recs.append("Утро — продуктивное время для работы.")
        
        return recs
    
    def analyze(self, state: ActivityState, break_after_minutes: int = 50) -> AnalysisResult:
        # Провести анализ состояния
        mode, confidence = self._detect_mode(state)
        time_of_day = self.get_time_of_day()
        
        # Управление рабочей сессией
        is_work_mode = mode in [UserMode.DEEP_WORK, UserMode.RESEARCH, UserMode.CREATIVE]
        
        if is_work_mode and self._work_session_start is None:
            self._work_session_start = datetime.now()
        elif not is_work_mode and mode != UserMode.COMMUNICATION:
            # Сбросить сессию если перешли к отдыху или простою
            if mode in [UserMode.ENTERTAINMENT, UserMode.BREAK, UserMode.IDLE]:
                if self._last_mode in [UserMode.DEEP_WORK, UserMode.RESEARCH, UserMode.CREATIVE]:
                    self._work_session_start = None
        
        work_minutes = self._get_work_session_minutes()
        should_break = self._should_take_break(work_minutes, break_after_minutes)
        recommendations = self._get_recommendations(mode, time_of_day, work_minutes)
        
        # Сохранить историю
        self._mode_history.append((datetime.now(), mode))
        if len(self._mode_history) > 1000:
            self._mode_history = self._mode_history[-500:]
        
        self._last_mode = mode
        
        return AnalysisResult(
            mode=mode,
            confidence=confidence,
            time_of_day=time_of_day,
            work_session_minutes=work_minutes,
            should_take_break=should_break,
            recommendations=recommendations
        )
