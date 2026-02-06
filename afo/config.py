# Конфигурация приложения

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


def get_app_data_dir() -> Path:
    # Получить директорию данных приложения
    app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    path = Path(app_data) / 'AmbientFlowOrchestrator'
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class SoundSettings:
    enabled: bool = True
    volume: float = 0.3
    preferred_sounds: List[str] = None
    
    def __post_init__(self):
        if self.preferred_sounds is None:
            self.preferred_sounds = ['rain', 'cafe', 'forest']


@dataclass
class DisplaySettings:
    night_mode_enabled: bool = True
    night_mode_start: str = "20:00"
    night_mode_end: str = "07:00"
    color_temperature: int = 4500
    brightness_adjust: bool = True


@dataclass
class NotificationSettings:
    filter_enabled: bool = True
    allowed_apps: List[str] = None
    quiet_hours_start: str = "09:00"
    quiet_hours_end: str = "18:00"
    
    def __post_init__(self):
        if self.allowed_apps is None:
            self.allowed_apps = []


@dataclass
class BreakSettings:
    enabled: bool = True
    work_duration_minutes: int = 50
    break_duration_minutes: int = 10
    show_notification: bool = True
    play_sound: bool = True


@dataclass
class TrackingSettings:
    track_apps: bool = True
    track_input: bool = True
    track_audio: bool = True
    idle_threshold_seconds: int = 180


@dataclass
class ReminderItem:
    # одно напоминание - вода, разминка или кастомное
    id: str = ""
    name: str = ""
    enabled: bool = True
    interval_minutes: int = 30
    message: str = ""
    icon: str = "bell"  # bootstrap icon name


@dataclass
class ProcrastinationSettings:
    enabled: bool = True
    work_hours_start: str = "09:00"
    work_hours_end: str = "18:00"
    warning_threshold_minutes: int = 15
    cooldown_minutes: int = 20


@dataclass 
class ReminderSettings:
    # настройки напоминалок
    enabled: bool = True
    
    # предустановленные напоминания
    water: ReminderItem = None
    stretch: ReminderItem = None
    eyes: ReminderItem = None
    
    # кастомные напоминания юзера
    custom: List['ReminderItem'] = None
    
    # не показывать напоминания когда idle
    pause_when_idle: bool = True
    
    def __post_init__(self):
        if self.water is None:
            self.water = ReminderItem(
                id='water',
                name='Вода',
                enabled=True,
                interval_minutes=30,
                message='Выпей стакан воды 💧',
                icon='droplet'
            )
        if self.stretch is None:
            self.stretch = ReminderItem(
                id='stretch',
                name='Разминка',
                enabled=True,
                interval_minutes=45,
                message='Потянись и разомнись 🧘',
                icon='person-arms-up'
            )
        if self.eyes is None:
            self.eyes = ReminderItem(
                id='eyes',
                name='Глаза',
                enabled=False,
                interval_minutes=20,
                message='Посмотри вдаль 20 секунд 👀',
                icon='eye'
            )
        if self.custom is None:
            self.custom = []


@dataclass 
class Config:
    sound: SoundSettings = None
    display: DisplaySettings = None
    notifications: NotificationSettings = None
    breaks: BreakSettings = None
    tracking: TrackingSettings = None
    reminders: ReminderSettings = None
    procrastination: ProcrastinationSettings = None
    blocked_sites: List[str] = None
    work_apps: List[str] = None
    entertainment_apps: List[str] = None
    
    def __post_init__(self):
        if self.sound is None:
            self.sound = SoundSettings()
        if self.display is None:
            self.display = DisplaySettings()
        if self.notifications is None:
            self.notifications = NotificationSettings()
        if self.breaks is None:
            self.breaks = BreakSettings()
        if self.tracking is None:
            self.tracking = TrackingSettings()
        if self.reminders is None:
            self.reminders = ReminderSettings()
        if self.procrastination is None:
            self.procrastination = ProcrastinationSettings()
        if self.blocked_sites is None:
            self.blocked_sites = [
                'youtube.com', 'twitter.com', 'x.com', 'reddit.com', 'tiktok.com', 
                'instagram.com', 'facebook.com', 'twitch.tv', 'vk.com', 'ok.ru',
                'pinterest.com', 'tumblr.com', 'snapchat.com', '9gag.com', 'imgur.com',
                'buzzfeed.com', 'dailymotion.com', 'coub.com', 'pikabu.ru'
            ]
        if self.work_apps is None:
            self.work_apps = [
                # IDE и редакторы
                'code', 'devenv', 'pycharm', 'idea', 'webstorm', 'phpstorm', 'rider', 'clion',
                'goland', 'rubymine', 'datagrip', 'appcode', 'androidstudio',
                'notepad++', 'sublime_text', 'atom', 'vim', 'nvim', 'gvim', 'emacs',
                'brackets', 'textmate', 'bbedit', 'ultraedit', 'komodo',
                'eclipse', 'netbeans', 'codeblocks', 'qt creator', 'lazarus',
                # Office и документы
                'word', 'winword', 'excel', 'powerpoint', 'powerpnt', 'outlook', 'onenote', 'access', 'publisher',
                'libreoffice', 'soffice', 'openoffice', 'wps', 'onlyoffice',
                'acrord32', 'acrobat', 'foxitreader', 'sumatrapdf', 'calibre',
                'typora', 'marktext', 'zettlr', 'joplin',
                # Дизайн и графика
                'figma', 'figma-linux', 'photoshop', 'illustrator', 'aftereffects', 'premiere', 'indesign',
                'lightroom', 'xd', 'animate', 'audition', 'mediaencoder',
                'blender', 'gimp', 'inkscape', 'sketch', 'lunacy', 'gravit',
                'coreldraw', 'paintshoppro', 'affinity', 'afphoto', 'afdesigner',
                'cinema4d', 'maya', '3dsmax', 'zbrush', 'houdini', 'substance',
                'davinciresolve', 'resolve', 'vegas', 'camtasia', 'filmora',
                # Разработка и DevOps
                'terminal', 'iterm', 'cmd', 'powershell', 'pwsh', 'windowsterminal', 'wt', 'conemu', 'cmder',
                'git', 'github', 'gitkraken', 'sourcetree', 'tortoisegit', 'fork',
                'docker', 'podman', 'kubernetes', 'kubectl', 'lens',
                'postman', 'insomnia', 'httpie', 'soapui', 'paw',
                'datagrip', 'dbeaver', 'heidisql', 'mysql', 'pgadmin', 'mongodb', 'robo3t', 'studio3t',
                'filezilla', 'winscp', 'cyberduck', 'putty', 'mobaxterm', 'securecrt',
                'virtualbox', 'vmware', 'hyperv', 'vagrant', 'ansible',
                # Браузеры
                'firefox', 'chrome', 'msedge', 'edge', 'brave', 'opera', 'vivaldi', 'yandex',
                # Заметки и продуктивность
                'notion', 'obsidian', 'evernote', 'todoist', 'trello', 'asana',
                'clickup', 'monday', 'basecamp', 'wrike', 'airtable',
                'roamresearch', 'logseq', 'anytype', 'craft', 'bear', 'ulysses',
                'mindmanager', 'xmind', 'freemind', 'miro', 'lucidchart',
                # Коммуникации
                'slack', 'teams', 'zoom', 'skype', 'webex', 'gotomeeting',
                'meet', 'gather', 'around', 'loom', 'krisp',
                # Аналитика и данные
                'tableau', 'powerbi', 'looker', 'metabase', 'jupyter', 'rstudio', 'spss', 'stata',
                'python', 'ipython', 'anaconda', 'spyder', 'matlab', 'octave', 'mathematica'
            ]
        if self.entertainment_apps is None:
            self.entertainment_apps = [
                # Музыка и аудио
                'vlc', 'spotify', 'aimp', 'foobar2000', 'winamp', 'itunes', 'musicbee',
                'deezer', 'tidal', 'soundcloud', 'bandcamp', 'yandexmusic', 'applemusic',
                'audacity', 'reaper', 'flstudio', 'ableton', 'cubase', 'lmms',
                # Видео и стриминг
                'netflix', 'primevideo', 'kinopoisk', 'disney', 'hbomax', 'hulu',
                'ivi', 'okko', 'wink', 'megogo', 'more.tv',
                'potplayer', 'mpc-hc', 'kmplayer', 'gomplayer', 'kodi', 'plex', 'jellyfin',
                'mpv', 'smplayer', 'bsplayer', 'daum',
                # Игры и лаунчеры
                'steam', 'steamwebhelper', 'epicgameslauncher', 'gog', 'goggalaxy',
                'origin', 'ea app', 'uplay', 'ubisoft', 'battlenet',
                'riotclient', 'leagueclient', 'valorant',
                'minecraft', 'javaw', 'roblox',
                'xbox', 'playnite', 'launchbox', 'retroarch',
                # Соцсети и мессенджеры
                'discord', 'telegram', 'whatsapp', 'viber', 'messenger', 'signal',
                'wechat', 'line', 'kakaotalk', 'icq', 'element', 'matrix',
                'vk', 'vkmessenger', 'mailru',
                # Стриминг и создание контента
                'obs', 'obs64', 'streamlabs', 'xsplit', 'wirecast', 'vmix',
                'streamelements', 'twitchstudio',
                # Чтение и досуг
                'kindle', 'kobo', 'bookmate', 'litres', 'pocket', 'feedly', 'inoreader'
            ]


class ConfigManager:
    # Менеджер конфигурации
    
    def __init__(self):
        self.config_path = get_app_data_dir() / 'config.json'
        self.config = self._load()
    
    def _load(self) -> Config:
        # Загрузить конфигурацию
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return self._dict_to_config(data)
            except Exception:
                pass
        return Config()
    
    def _dict_to_config(self, data: dict) -> Config:
        # Преобразовать словарь в конфиг
        # для напоминаний нужна отдельная логика т.к. там вложенные dataclass'ы
        reminders_data = data.get('reminders', {})
        reminders = ReminderSettings(
            enabled=reminders_data.get('enabled', True),
            water=ReminderItem(**reminders_data.get('water', {})) if reminders_data.get('water') else None,
            stretch=ReminderItem(**reminders_data.get('stretch', {})) if reminders_data.get('stretch') else None,
            eyes=ReminderItem(**reminders_data.get('eyes', {})) if reminders_data.get('eyes') else None,
            custom=[ReminderItem(**r) for r in reminders_data.get('custom', [])],
            pause_when_idle=reminders_data.get('pause_when_idle', True)
        )
        
        return Config(
            sound=SoundSettings(**data.get('sound', {})),
            display=DisplaySettings(**data.get('display', {})),
            notifications=NotificationSettings(**data.get('notifications', {})),
            breaks=BreakSettings(**data.get('breaks', {})),
            tracking=TrackingSettings(**data.get('tracking', {})),
            reminders=reminders,
            procrastination=ProcrastinationSettings(**data.get('procrastination', {})),
            blocked_sites=data.get('blocked_sites'),
            work_apps=data.get('work_apps'),
            entertainment_apps=data.get('entertainment_apps')
        )
    
    def save(self):
        # Сохранить конфигурацию
        data = {
            'sound': asdict(self.config.sound),
            'display': asdict(self.config.display),
            'notifications': asdict(self.config.notifications),
            'breaks': asdict(self.config.breaks),
            'tracking': asdict(self.config.tracking),
            'reminders': asdict(self.config.reminders),
            'procrastination': asdict(self.config.procrastination),
            'blocked_sites': self.config.blocked_sites,
            'work_apps': self.config.work_apps,
            'entertainment_apps': self.config.entertainment_apps
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def update(self, section: str, **kwargs):
        # Обновить секцию конфига
        if hasattr(self.config, section):
            obj = getattr(self.config, section)
            if hasattr(obj, '__dataclass_fields__'):
                for key, value in kwargs.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
            else:
                setattr(self.config, section, kwargs.get('value', obj))
        self.save()
