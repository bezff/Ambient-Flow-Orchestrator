# Глобальные горячие клавиши

import threading
from typing import Dict, Callable, Optional

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class HotkeyManager:
    
    # дефолтные комбинации
    DEFAULT_HOTKEYS = {
        'toggle_sound': 'ctrl+alt+m',
        'start_break': 'ctrl+alt+b',
        'toggle_pomodoro': 'ctrl+alt+p',
        'skip_pomodoro': 'ctrl+alt+s',
    }
    
    def __init__(self):
        self._hotkeys: Dict[str, str] = self.DEFAULT_HOTKEYS.copy()
        self._callbacks: Dict[str, Callable] = {}
        self._registered: Dict[str, bool] = {}
        self._enabled = True
        self._lock = threading.Lock()
    
    def set_callback(self, action: str, callback: Callable):
        self._callbacks[action] = callback
    
    def set_hotkey(self, action: str, hotkey: str):
        with self._lock:
            # убрать старую если была
            if action in self._registered and self._registered[action]:
                try:
                    old_hotkey = self._hotkeys.get(action)
                    if old_hotkey and KEYBOARD_AVAILABLE:
                        keyboard.remove_hotkey(old_hotkey)
                except Exception:
                    pass
            
            self._hotkeys[action] = hotkey
            self._registered[action] = False
            
            # зарегать новую
            if self._enabled:
                self._register_hotkey(action)
    
    def _register_hotkey(self, action: str):
        if not KEYBOARD_AVAILABLE:
            return
        
        hotkey = self._hotkeys.get(action)
        callback = self._callbacks.get(action)
        
        if hotkey and callback:
            try:
                keyboard.add_hotkey(hotkey, callback, suppress=False)
                self._registered[action] = True
            except Exception as e:
                print(f"Hotkey registration failed for {action}: {e}")
    
    def start(self):
        if not KEYBOARD_AVAILABLE:
            print("Keyboard module not available, hotkeys disabled")
            return
        
        with self._lock:
            self._enabled = True
            for action in self._hotkeys:
                if action in self._callbacks:
                    self._register_hotkey(action)
    
    def stop(self):
        if not KEYBOARD_AVAILABLE:
            return
        
        with self._lock:
            self._enabled = False
            for action, hotkey in self._hotkeys.items():
                if self._registered.get(action):
                    try:
                        keyboard.remove_hotkey(hotkey)
                    except Exception:
                        pass
                    self._registered[action] = False
    
    def get_hotkeys(self) -> Dict[str, str]:
        return self._hotkeys.copy()
    
    def is_available(self) -> bool:
        return KEYBOARD_AVAILABLE
