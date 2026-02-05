# Установка AFO

## Сборка

1. Убедись что установлен Python 3.10+
2. Открой папку проекта
3. Запусти `build.bat`

Готовый exe будет в `dist/AFO.exe`

## Автозапуск

Откройте AFO → Настройки → включите "Автозапуск"

Приложение само добавится в автозагрузку Windows.

## Проблемы

**pywin32 не устанавливается**
```
pip install --upgrade pip
pip install pywin32
```

**PyInstaller не находится**
```
pip install pyinstaller
```
