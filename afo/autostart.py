# Управление автозагрузкой Windows

import os
import sys
import winreg
from pathlib import Path


REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "AmbientFlowOrchestrator"


def get_exe_path() -> str:
    # Получить путь к exe или скрипту
    if getattr(sys, 'frozen', False):
        # PyInstaller exe
        return sys.executable
    else:
        # Python скрипт — не добавляем в автозагрузку
        return ""


def is_autostart_enabled() -> bool:
    # Проверить включена ли автозагрузка
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def enable_autostart() -> bool:
    # Добавить в автозагрузку
    exe_path = get_exe_path()
    if not exe_path:
        return False
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def disable_autostart() -> bool:
    # Убрать из автозагрузки
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    # Установить состояние автозагрузки
    if enabled:
        return enable_autostart()
    else:
        return disable_autostart()
