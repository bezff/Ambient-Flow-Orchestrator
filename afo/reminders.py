# Напоминания о воде, разминке и прочем

import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional
from .config import ReminderSettings, ReminderItem


@dataclass
class ReminderState:
    id: str
    last_triggered: Optional[datetime] = None
    snooze_until: Optional[datetime] = None
    trigger_count: int = 0


class ReminderManager:
    
    def __init__(self, settings: ReminderSettings, is_idle_callback: Callable[[], bool] = None):
        self.settings = settings
        self._is_idle = is_idle_callback or (lambda: False)
        self._states: Dict[str, ReminderState] = {}
        self._listeners: List[Callable[[ReminderItem], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._init_states()
    
    def _init_states(self):
        for reminder in self._get_all_reminders():
            self._states[reminder.id] = ReminderState(id=reminder.id)
    
    def _get_all_reminders(self) -> List[ReminderItem]:
        reminders = []
        if self.settings.water:
            reminders.append(self.settings.water)
        if self.settings.stretch:
            reminders.append(self.settings.stretch)
        if self.settings.eyes:
            reminders.append(self.settings.eyes)
        if self.settings.custom:
            reminders.extend(self.settings.custom)
        return reminders
    
    def add_listener(self, callback: Callable[[ReminderItem], None]):
        self._listeners.append(callback)
    
    def _notify(self, reminder: ReminderItem):
        for listener in self._listeners:
            try:
                listener(reminder)
            except Exception as e:
                print(f"Reminder callback error: {e}")
    
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _loop(self):
        while self._running:
            try:
                self._check_reminders()
            except Exception as e:
                print(f"Reminder loop error: {e}")
            time.sleep(10)
    
    def _check_reminders(self):
        if not self.settings.enabled:
            return
        
        if self.settings.pause_when_idle and self._is_idle():
            return
        
        now = datetime.now()
        
        for reminder in self._get_all_reminders():
            if not reminder.enabled:
                continue
            
            state = self._states.get(reminder.id)
            if not state:
                state = ReminderState(id=reminder.id)
                self._states[reminder.id] = state
            
            if state.snooze_until and now < state.snooze_until:
                continue
            
            should_trigger = False
            
            if state.last_triggered is None:
                # ждём полный интервал от старта
                if not hasattr(state, '_start_time'):
                    state._start_time = now
                elif (now - state._start_time).total_seconds() >= reminder.interval_minutes * 60:
                    should_trigger = True
            else:
                elapsed = (now - state.last_triggered).total_seconds()
                if elapsed >= reminder.interval_minutes * 60:
                    should_trigger = True
            
            if should_trigger:
                self._trigger_reminder(reminder, state)
    
    def _trigger_reminder(self, reminder: ReminderItem, state: ReminderState):
        with self._lock:
            state.last_triggered = datetime.now()
            state.trigger_count += 1
        self._notify(reminder)
    
    def snooze(self, reminder_id: str, minutes: int = 10):
        # отложить на N минут
        with self._lock:
            if reminder_id in self._states:
                self._states[reminder_id].snooze_until = datetime.now() + timedelta(minutes=minutes)
    
    def dismiss(self, reminder_id: str):
        # сбросить таймер (выполнено)
        with self._lock:
            if reminder_id in self._states:
                self._states[reminder_id].last_triggered = datetime.now()
                self._states[reminder_id].snooze_until = None
    
    def get_status(self) -> Dict:
        now = datetime.now()
        result = {
            'enabled': self.settings.enabled,
            'reminders': []
        }
        
        for reminder in self._get_all_reminders():
            state = self._states.get(reminder.id, ReminderState(id=reminder.id))
            
            next_in_seconds = None
            if reminder.enabled:
                if state.snooze_until and now < state.snooze_until:
                    next_in_seconds = int((state.snooze_until - now).total_seconds())
                elif state.last_triggered:
                    elapsed = (now - state.last_triggered).total_seconds()
                    remaining = (reminder.interval_minutes * 60) - elapsed
                    next_in_seconds = max(0, int(remaining))
                else:
                    if hasattr(state, '_start_time'):
                        elapsed = (now - state._start_time).total_seconds()
                        remaining = (reminder.interval_minutes * 60) - elapsed
                        next_in_seconds = max(0, int(remaining))
                    else:
                        next_in_seconds = reminder.interval_minutes * 60
            
            result['reminders'].append({
                'id': reminder.id,
                'name': reminder.name,
                'enabled': reminder.enabled,
                'interval_minutes': reminder.interval_minutes,
                'message': reminder.message,
                'icon': reminder.icon,
                'next_in_seconds': next_in_seconds,
                'trigger_count': state.trigger_count,
                'snoozed': state.snooze_until is not None and now < state.snooze_until
            })
        
        return result
    
    def update_settings(self, settings: ReminderSettings):
        with self._lock:
            self.settings = settings
            self._init_states()
    
    def add_custom_reminder(self, name: str, interval_minutes: int, message: str, icon: str = 'bell') -> ReminderItem:
        custom_id = f"custom_{int(time.time())}_{len(self.settings.custom)}"
        
        reminder = ReminderItem(
            id=custom_id,
            name=name,
            enabled=True,
            interval_minutes=interval_minutes,
            message=message,
            icon=icon
        )
        
        with self._lock:
            self.settings.custom.append(reminder)
            self._states[custom_id] = ReminderState(id=custom_id)
        
        return reminder
    
    def remove_custom_reminder(self, reminder_id: str) -> bool:
        with self._lock:
            for i, r in enumerate(self.settings.custom):
                if r.id == reminder_id:
                    self.settings.custom.pop(i)
                    if reminder_id in self._states:
                        del self._states[reminder_id]
                    return True
        return False
