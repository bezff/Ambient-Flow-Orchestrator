# Веб-сервер и API

import json
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, Callable

from .tracker import ActivityTracker, ActivityState
from .analyzer import StateAnalyzer, AnalysisResult
from .environment import EnvironmentController, AmbientSound
from .config import ConfigManager
from .reminders import ReminderManager
from . import autostart


class APIHandler(SimpleHTTPRequestHandler):
    # Обработчик HTTP запросов
    
    orchestrator: 'Orchestrator' = None
    static_dir: Path = None
    
    def __init__(self, *args, **kwargs):
        self.routes = {
            '/api/status': self.handle_status,
            '/api/stats': self.handle_stats,
            '/api/config': self.handle_config,
            '/api/sound': self.handle_sound,
            '/api/mode': self.handle_mode,
            '/api/break': self.handle_break,
            '/api/autostart': self.handle_autostart,
            '/api/reminders': self.handle_reminders,
            '/api/reminders/snooze': self.handle_reminder_snooze,
            '/api/reminders/dismiss': self.handle_reminder_dismiss,
            '/api/procrastination': self.handle_procrastination,
        }
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        # Отключить логирование запросов
        pass
    
    def send_json(self, data: Dict, status: int = 200):
        # Отправить JSON ответ
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        # Обработка CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        # Обработка GET запросов
        parsed = urlparse(self.path)
        path = parsed.path
        
        # API роуты
        if path.startswith('/api/'):
            handler = self.routes.get(path.split('?')[0])
            if handler:
                params = parse_qs(parsed.query)
                handler('GET', params)
            else:
                self.send_json({'error': 'Not found'}, 404)
            return
        
        # Статические файлы
        if path == '/':
            path = '/index.html'
        
        # Иконка из корня проекта
        if path == '/icon.png':
            # static_dir = afo/web, parent = afo, parent.parent = корень проекта
            icon_path = self.static_dir.parent.parent / 'icon.png'
            if not icon_path.exists():
                # Fallback - ищем рядом с afo/
                icon_path = Path(__file__).parent.parent / 'icon.png'
            if icon_path.exists():
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Cache-Control', 'max-age=3600')
                self.end_headers()
                self.wfile.write(icon_path.read_bytes())
                return
        
        # Звуковые файлы из папки sounds
        if path.startswith('/sounds/'):
            sound_file = path.split('/')[-1]
            sound_path = Path(__file__).parent / 'sounds' / sound_file
            if sound_path.exists() and sound_path.suffix == '.mp3':
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Cache-Control', 'max-age=86400')
                self.end_headers()
                self.wfile.write(sound_path.read_bytes())
                return
        
        file_path = self.static_dir / path.lstrip('/')
        
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            
            content_types = {
                '.html': 'text/html',
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.json': 'application/json',
                '.png': 'image/png',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon',
            }
            content_type = content_types.get(file_path.suffix, 'application/octet-stream')
            self.send_header('Content-Type', f'{content_type}; charset=utf-8')
            self.end_headers()
            
            self.wfile.write(file_path.read_bytes())
        else:
            self.send_json({'error': 'Not found'}, 404)
    
    def do_POST(self):
        # Обработка POST запросов
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith('/api/'):
            handler = self.routes.get(path)
            if handler:
                content_length = int(self.headers.get('Content-Length', 0))
                body = {}
                if content_length > 0:
                    raw_body = self.rfile.read(content_length)
                    try:
                        body = json.loads(raw_body.decode('utf-8'))
                    except Exception:
                        pass
                handler('POST', body)
            else:
                self.send_json({'error': 'Not found'}, 404)
        else:
            self.send_json({'error': 'Not found'}, 404)
    
    def handle_status(self, method: str, params: Dict):
        # Получить текущий статус
        orch = self.orchestrator
        
        status = {
            'running': orch.running,
            'activity': {
                'current_app': orch.tracker.state.current_app,
                'current_window': orch.tracker.state.current_window,
                'is_idle': orch.tracker.state.is_idle,
                'idle_seconds': orch.tracker.state.idle_seconds,
                'activity_level': orch.tracker.state.activity_level,
            },
            'analysis': None,
            'environment': {
                'sound': orch.environment.state.sound.value,
                'sound_volume': orch.environment.state.sound_volume,
                'night_mode': orch.environment.state.night_mode_active,
                'focus_mode': orch.environment.state.focus_mode,
                'notifications_filtered': orch.environment.state.notifications_filtered,
            },
            # напоминания которые надо показать юзеру
            'pending_reminders': orch._pending_reminders.copy()
        }
        
        # очищаем после отправки (юзер их увидел)
        orch._pending_reminders.clear()
        
        if orch._last_analysis:
            status['analysis'] = {
                'mode': orch._last_analysis.mode.value,
                'confidence': orch._last_analysis.confidence,
                'time_of_day': orch._last_analysis.time_of_day.value,
                'work_minutes': orch._last_analysis.work_session_minutes,
                'should_break': orch._last_analysis.should_take_break,
                'recommendations': orch._last_analysis.recommendations,
                'procrastination': {
                    'active': orch._last_analysis.procrastination.active,
                    'entertainment_minutes': orch._last_analysis.procrastination.entertainment_minutes,
                    'message': orch._last_analysis.procrastination.message,
                }
            }
        
        self.send_json(status)
    
    def handle_stats(self, method: str, params: Dict):
        # Получить статистику
        orch = self.orchestrator
        today_stats = orch.tracker.get_today_stats()
        
        # Форматировать статистику
        formatted = []
        for app, seconds in today_stats.items():
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            formatted.append({
                'app': app,
                'seconds': seconds,
                'formatted': f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
            })
        
        work_time = orch.tracker.get_category_time(orch.config.config.work_apps)
        entertainment_time = orch.tracker.get_category_time(orch.config.config.entertainment_apps)
        
        self.send_json({
            'apps': formatted[:10],
            'work_seconds': work_time,
            'entertainment_seconds': entertainment_time,
        })
    
    def handle_config(self, method: str, params: Dict):
        # Работа с конфигурацией
        orch = self.orchestrator
        
        if method == 'GET':
            config = orch.config.config
            self.send_json({
                'sound': {
                    'enabled': config.sound.enabled,
                    'volume': config.sound.volume,
                    'preferred_sounds': config.sound.preferred_sounds,
                },
                'display': {
                    'night_mode_enabled': config.display.night_mode_enabled,
                    'night_mode_start': config.display.night_mode_start,
                    'night_mode_end': config.display.night_mode_end,
                    'color_temperature': config.display.color_temperature,
                },
                'notifications': {
                    'filter_enabled': config.notifications.filter_enabled,
                },
                'breaks': {
                    'enabled': config.breaks.enabled,
                    'work_duration': config.breaks.work_duration_minutes,
                    'break_duration': config.breaks.break_duration_minutes,
                },
                'blocked_sites': config.blocked_sites,
            })
        elif method == 'POST':
            # Обновить конфигурацию
            for section, values in params.items():
                if isinstance(values, dict):
                    orch.config.update(section, **values)
                else:
                    orch.config.update(section, value=values)
            self.send_json({'success': True})
    
    def handle_sound(self, method: str, params: Dict):
        # Управление звуком
        orch = self.orchestrator
        
        if method == 'POST':
            sound_name = params.get('sound', 'none')
            volume = params.get('volume')
            
            try:
                sound = AmbientSound(sound_name)
                if volume is not None:
                    orch.environment.sound.play(sound, float(volume))
                else:
                    orch.environment.sound.play(sound)
                self.send_json({'success': True, 'sound': sound.value})
            except Exception as e:
                self.send_json({'error': str(e)}, 400)
        else:
            self.send_json({
                'current': orch.environment.state.sound.value,
                'volume': orch.environment.state.sound_volume,
                'available': [s.value for s in AmbientSound if s != AmbientSound.NONE]
            })
    
    def handle_mode(self, method: str, params: Dict):
        # Управление режимом
        orch = self.orchestrator
        
        if method == 'POST':
            auto = params.get('auto')
            if auto is not None:
                orch.environment.set_auto_adjust(auto)
            self.send_json({'success': True})
        else:
            self.send_json({
                'auto_adjust': orch.environment._auto_adjust
            })
    
    def handle_break(self, method: str, params: Dict):
        # Запустить перерыв
        orch = self.orchestrator
        
        if method == 'POST':
            orch.start_break()
            self.send_json({'success': True})
        else:
            self.send_json({
                'break_active': False,
                'break_remaining': 0
            })
    
    def handle_autostart(self, method: str, params: Dict):
        # Управление автозагрузкой
        if method == 'POST':
            enabled = params.get('enabled', False)
            success = autostart.set_autostart(enabled)
            self.send_json({
                'success': success,
                'enabled': autostart.is_autostart_enabled()
            })
        else:
            self.send_json({
                'enabled': autostart.is_autostart_enabled(),
                'available': bool(autostart.get_exe_path())
            })
    
    def handle_reminders(self, method: str, params: Dict):
        # получить/обновить настройки напоминаний
        orch = self.orchestrator
        
        if method == 'GET':
            # возвращаем статус + настройки
            status = orch.reminders.get_status()
            config = orch.config.config.reminders
            
            self.send_json({
                **status,
                'pause_when_idle': config.pause_when_idle
            })
        else:
            # POST - обновляем настройки
            # можно передать enabled (общий флаг) или настройки конкретного напоминания
            
            if 'enabled' in params:
                orch.config.config.reminders.enabled = params['enabled']
            
            if 'pause_when_idle' in params:
                orch.config.config.reminders.pause_when_idle = params['pause_when_idle']
            
            # обновление конкретного напоминания по id
            if 'reminder_id' in params:
                rid = params['reminder_id']
                settings = orch.config.config.reminders
                
                # ищем напоминание
                target = None
                if settings.water and settings.water.id == rid:
                    target = settings.water
                elif settings.stretch and settings.stretch.id == rid:
                    target = settings.stretch
                elif settings.eyes and settings.eyes.id == rid:
                    target = settings.eyes
                else:
                    for r in settings.custom:
                        if r.id == rid:
                            target = r
                            break
                
                if target:
                    if 'reminder_enabled' in params:
                        target.enabled = params['reminder_enabled']
                    if 'interval_minutes' in params:
                        target.interval_minutes = params['interval_minutes']
                    if 'message' in params:
                        target.message = params['message']
            
            # добавление кастомного напоминания
            if 'add_custom' in params:
                custom = params['add_custom']
                orch.reminders.add_custom_reminder(
                    name=custom.get('name', 'Напоминание'),
                    interval_minutes=custom.get('interval_minutes', 30),
                    message=custom.get('message', ''),
                    icon=custom.get('icon', 'bell')
                )
            
            # удаление кастомного
            if 'remove_custom' in params:
                orch.reminders.remove_custom_reminder(params['remove_custom'])
            
            # сохраняем и обновляем менеджер
            orch.config.save()
            orch.reminders.update_settings(orch.config.config.reminders)
            
            self.send_json({'success': True})
    
    def handle_reminder_snooze(self, method: str, params: Dict):
        # отложить напоминание
        if method == 'POST':
            reminder_id = params.get('id')
            minutes = params.get('minutes', 10)
            
            if reminder_id:
                self.orchestrator.reminders.snooze(reminder_id, minutes)
                self.send_json({'success': True})
            else:
                self.send_json({'error': 'id required'}, 400)
        else:
            self.send_json({'error': 'POST only'}, 405)
    
    def handle_reminder_dismiss(self, method: str, params: Dict):
        # сбросить напоминание (типа выполнил)
        if method == 'POST':
            reminder_id = params.get('id')
            
            if reminder_id:
                self.orchestrator.reminders.dismiss(reminder_id)
                self.send_json({'success': True})
            else:
                self.send_json({'error': 'id required'}, 400)
        else:
            self.send_json({'error': 'POST only'}, 405)
    
    def handle_procrastination(self, method: str, params: Dict):
        orch = self.orchestrator
        
        if method == 'GET':
            p = orch.config.config.procrastination
            self.send_json({
                'enabled': p.enabled,
                'work_hours_start': p.work_hours_start,
                'work_hours_end': p.work_hours_end,
                'warning_threshold_minutes': p.warning_threshold_minutes,
                'cooldown_minutes': p.cooldown_minutes
            })
        else:
            p = orch.config.config.procrastination
            
            if 'enabled' in params:
                p.enabled = params['enabled']
            if 'work_hours_start' in params:
                p.work_hours_start = params['work_hours_start']
            if 'work_hours_end' in params:
                p.work_hours_end = params['work_hours_end']
            if 'warning_threshold_minutes' in params:
                p.warning_threshold_minutes = params['warning_threshold_minutes']
            if 'cooldown_minutes' in params:
                p.cooldown_minutes = params['cooldown_minutes']
            
            orch.config.save()
            
            orch.analyzer.set_procrastination_settings(
                enabled=p.enabled,
                work_start=p.work_hours_start,
                work_end=p.work_hours_end,
                threshold_minutes=p.warning_threshold_minutes,
                cooldown_minutes=p.cooldown_minutes
            )
            
            self.send_json({'success': True})


class WebServer:
    # Веб-сервер
    
    def __init__(self, orchestrator: 'Orchestrator', port: int = 8420):
        self.orchestrator = orchestrator
        self.port = port
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        # Запустить сервер
        APIHandler.orchestrator = self.orchestrator
        APIHandler.static_dir = Path(__file__).parent / 'web'
        
        self.server = HTTPServer(('127.0.0.1', self.port), APIHandler)
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
    
    def stop(self):
        # Остановить сервер
        if self.server:
            self.server.shutdown()
    
    def open_browser(self):
        # Открыть браузер
        webbrowser.open(f'http://localhost:{self.port}')


class Orchestrator:
    # Главный оркестратор
    
    def __init__(self):
        self.config = ConfigManager()
        self.tracker = ActivityTracker(
            idle_threshold=self.config.config.tracking.idle_threshold_seconds
        )
        self.analyzer = StateAnalyzer(
            work_apps=self.config.config.work_apps,
            entertainment_apps=self.config.config.entertainment_apps
        )
        self.environment = EnvironmentController(self.config.config)
        self.server = WebServer(self)
        
        # напоминалки - проверяем idle через трекер
        self.reminders = ReminderManager(
            settings=self.config.config.reminders,
            is_idle_callback=lambda: self.tracker.state.is_idle
        )
        
        # очередь напоминаний для UI (SSE можно будет потом прикрутить)
        self._pending_reminders = []
        self.reminders.add_listener(self._on_reminder)
        
        # настройки прокрастинации
        p = self.config.config.procrastination
        self.analyzer.set_procrastination_settings(
            enabled=p.enabled,
            work_start=p.work_hours_start,
            work_end=p.work_hours_end,
            threshold_minutes=p.warning_threshold_minutes,
            cooldown_minutes=p.cooldown_minutes
        )
        self.analyzer.set_warning_callback(self._on_procrastination_warning)
        
        self.running = False
        self._last_analysis: Optional[AnalysisResult] = None
        self._analysis_thread: Optional[threading.Thread] = None
    
    def _on_procrastination_warning(self, message: str, minutes: int):
        self._pending_reminders.append({
            'id': 'procrastination',
            'name': 'Прокрастинация',
            'message': message,
            'icon': 'exclamation-triangle',
            'timestamp': __import__('time').time(),
            'type': 'procrastination',
            'entertainment_minutes': minutes
        })
        if len(self._pending_reminders) > 5:
            self._pending_reminders.pop(0)
        
        self.running = False
        self._last_analysis: Optional[AnalysisResult] = None
        self._analysis_thread: Optional[threading.Thread] = None
    
    def _on_reminder(self, reminder):
        # колбэк когда пора показать напоминание
        # пока просто складываем в очередь, UI будет поллить
        self._pending_reminders.append({
            'id': reminder.id,
            'name': reminder.name,
            'message': reminder.message,
            'icon': reminder.icon,
            'timestamp': __import__('time').time()
        })
        # держим макс 5 штук в очереди
        if len(self._pending_reminders) > 5:
            self._pending_reminders.pop(0)
    
    def _analysis_loop(self):
        # Цикл анализа
        while self.running:
            try:
                analysis = self.analyzer.analyze(
                    self.tracker.state,
                    self.config.config.breaks.work_duration_minutes
                )
                self._last_analysis = analysis
                
                # Применить настройки окружения
                self.environment.apply_for_mode(analysis)
                
            except Exception:
                pass
            
            threading.Event().wait(5)  # Анализ каждые 5 секунд
    
    def start(self):
        """Запустить оркестратор"""
        if self.running:
            return
        
        self.running = True
        
        # Запустить компоненты
        self.tracker.start()
        self.server.start()
        self.reminders.start()
        
        # Запустить цикл анализа
        self._analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self._analysis_thread.start()
    
    def stop(self):
        # Остановить оркестратор
        self.running = False
        
        self.tracker.stop()
        self.server.stop()
        self.reminders.stop()
        self.environment.reset()
        
        if self._analysis_thread:
            self._analysis_thread.join(timeout=2)
    
    def start_break(self):
        # Начать перерыв
        from .analyzer import UserMode
        
        # Имитировать режим перерыва
        class FakeAnalysis:
            mode = UserMode.BREAK
            time_of_day = self.analyzer.get_time_of_day()
        
        self.environment.apply_for_mode(FakeAnalysis())
