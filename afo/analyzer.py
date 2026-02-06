# Анализатор состояния пользователя

from datetime import datetime, time
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Callable

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
class ProcrastinationWarning:
    active: bool = False
    entertainment_minutes: int = 0
    message: str = ""


@dataclass
class AnalysisResult:
    mode: UserMode
    confidence: float
    time_of_day: TimeOfDay
    work_session_minutes: int
    should_take_break: bool
    recommendations: List[str]
    procrastination: ProcrastinationWarning = None
    
    def __post_init__(self):
        if self.procrastination is None:
            self.procrastination = ProcrastinationWarning()


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
        
        # трекинг прокрастинации
        self._entertainment_start: Optional[datetime] = None
        self._last_warning_time: Optional[datetime] = None
        self._warning_callback: Optional[Callable] = None
        
        # настройки прокрастинации (будут заданы через set_procrastination_settings)
        self._procrastination_enabled = True
        self._work_hours_start = time(9, 0)
        self._work_hours_end = time(18, 0)
        self._warning_threshold = 15
        self._warning_cooldown = 20
    
    def set_procrastination_settings(self, enabled: bool, work_start: str, work_end: str,
                                     threshold_minutes: int, cooldown_minutes: int):
        self._procrastination_enabled = enabled
        
        h, m = map(int, work_start.split(':'))
        self._work_hours_start = time(h, m)
        
        h, m = map(int, work_end.split(':'))
        self._work_hours_end = time(h, m)
        
        self._warning_threshold = threshold_minutes
        self._warning_cooldown = cooldown_minutes
    
    def set_warning_callback(self, callback: Callable):
        self._warning_callback = callback
    
    def _is_work_hours(self) -> bool:
        now = datetime.now().time()
        if self._work_hours_start < self._work_hours_end:
            return self._work_hours_start <= now <= self._work_hours_end
        # если конец < начала (ночная смена)
        return now >= self._work_hours_start or now <= self._work_hours_end
    
    def _check_procrastination(self, current_mode: UserMode) -> ProcrastinationWarning:
        if not self._procrastination_enabled:
            return ProcrastinationWarning()
        
        if not self._is_work_hours():
            self._entertainment_start = None
            return ProcrastinationWarning()
        
        now = datetime.now()
        
        if current_mode == UserMode.ENTERTAINMENT:
            if self._entertainment_start is None:
                self._entertainment_start = now
            
            minutes_in_entertainment = int((now - self._entertainment_start).total_seconds() / 60)
            
            if minutes_in_entertainment >= self._warning_threshold:
                # проверяем cooldown
                can_warn = True
                if self._last_warning_time:
                    since_last = (now - self._last_warning_time).total_seconds() / 60
                    if since_last < self._warning_cooldown:
                        can_warn = False
                
                if can_warn:
                    self._last_warning_time = now
                    
                    messages = [
                        f"Уже {minutes_in_entertainment} мин в развлечениях. Пора за работу?",
                        f"Так {minutes_in_entertainment} минут и пролетели... Может хватит?",
                        f"Рабочее время идёт, а ты уже {minutes_in_entertainment} мин отдыхаешь",
                        f"Эй, {minutes_in_entertainment} минут прокрастинации! Давай за дело",
                    ]
                    import random
                    msg = random.choice(messages)
                    
                    if self._warning_callback:
                        self._warning_callback(msg, minutes_in_entertainment)
                    
                    return ProcrastinationWarning(
                        active=True,
                        entertainment_minutes=minutes_in_entertainment,
                        message=msg
                    )
                
                return ProcrastinationWarning(
                    active=False,
                    entertainment_minutes=minutes_in_entertainment,
                    message=""
                )
            
            return ProcrastinationWarning(
                active=False,
                entertainment_minutes=minutes_in_entertainment,
                message=""
            )
        else:
            # вышли из развлечений - сбрасываем таймер
            self._entertainment_start = None
            return ProcrastinationWarning()
    
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
        
        # рекомендации по времени работы
        if work_minutes > 120:
            recs.append("Более 2 часов без перерыва. Обязательно отдохните!")
        elif work_minutes > 90:
            recs.append("Долгая работа без перерыва. Отдохните 15 минут.")
        elif work_minutes > 50:
            recs.append("Хорошее время для короткого перерыва.")
        elif work_minutes > 25:
            recs.append("Отличный темп! Помидорка почти готова 🍅")
        
        # рекомендации по времени суток
        if time_of_day == TimeOfDay.NIGHT:
            if mode in [UserMode.DEEP_WORK, UserMode.RESEARCH]:
                recs.append("Поздний час. Рекомендуется завершить работу.")
            recs.append("Ночной режим активен — берегите глаза.")
        
        if time_of_day == TimeOfDay.EVENING:
            if mode == UserMode.DEEP_WORK:
                recs.append("Включён ночной режим для комфорта глаз.")
            if work_minutes > 30:
                recs.append("Вечер — время замедлиться.")
        
        if time_of_day == TimeOfDay.MORNING:
            if mode == UserMode.ENTERTAINMENT:
                recs.append("Утро — продуктивное время для работы.")
            elif mode == UserMode.DEEP_WORK and work_minutes < 10:
                recs.append("Отличное начало дня! Утро — пик продуктивности.")
        
        if time_of_day == TimeOfDay.AFTERNOON:
            if work_minutes > 0 and work_minutes < 20:
                recs.append("После обеда бывает спад. Короткая прогулка поможет.")
        
        # рекомендации по режиму
        if mode == UserMode.DEEP_WORK:
            if work_minutes > 45:
                recs.append("Не забудьте размяться. Спина скажет спасибо.")
            if work_minutes > 20:
                recs.append("Фоновые звуки помогут сохранить концентрацию.")
        
        if mode == UserMode.COMMUNICATION:
            recs.append("Звук приглушён на время общения.")
        
        if mode == UserMode.RESEARCH:
            recs.append("Делайте заметки, пока информация свежая.")
        
        if mode == UserMode.CREATIVE:
            recs.append("Творческий режим — не отвлекайтесь!")
        
        if mode == UserMode.ENTERTAINMENT:
            if time_of_day in [TimeOfDay.MORNING, TimeOfDay.AFTERNOON]:
                if work_minutes == 0:
                    recs.append("Планировали поработать сегодня?")
        
        if mode == UserMode.IDLE:
            recs.append("Нет активности. Ушли на перерыв?")
        
        # не больше 3 рекомендаций
        return recs[:3]
    
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
        
        # прокрастинация
        procrastination = self._check_procrastination(mode)
        
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
            recommendations=recommendations,
            procrastination=procrastination
        )
