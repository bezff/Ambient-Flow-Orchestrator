/**
 * AFO - Ambient Flow Orchestrator
 * Frontend Application
 */

(function() {
    'use strict';

    const API_BASE = '';
    const UPDATE_INTERVAL = 2000;

    // Audio player для фоновых звуков
    let audioPlayer = null;

    // State
    const state = {
        connected: false,
        status: null,
        stats: null,
        config: null,
        currentSound: 'none',
        breakActive: false,
        breakTimer: null,
        breakSeconds: 0
    };

    // DOM Elements
    const elements = {};

    // Mode display config
    const modeConfig = {
        deep_work: {
            name: 'Глубокая работа',
            desc: 'Максимальная концентрация',
            icon: '<i class="bi bi-layers"></i>'
        },
        research: {
            name: 'Исследование',
            desc: 'Поиск и изучение',
            icon: '<i class="bi bi-search"></i>'
        },
        creative: {
            name: 'Творчество',
            desc: 'Креативный процесс',
            icon: '<i class="bi bi-brush"></i>'
        },
        communication: {
            name: 'Общение',
            desc: 'Коммуникация с коллегами',
            icon: '<i class="bi bi-chat-dots"></i>'
        },
        entertainment: {
            name: 'Отдых',
            desc: 'Развлечения и релаксация',
            icon: '<i class="bi bi-play-circle"></i>'
        },
        break: {
            name: 'Перерыв',
            desc: 'Время отдохнуть',
            icon: '<i class="bi bi-cup-hot"></i>'
        },
        idle: {
            name: 'Ожидание',
            desc: 'Нет активности',
            icon: '<i class="bi bi-clock"></i>'
        }
    };

    // Initialize
    function init() {
        cacheElements();
        bindEvents();
        startPolling();
        loadConfig();
    }

    function cacheElements() {
        elements.connectionStatus = document.getElementById('connectionStatus');
        elements.modeIcon = document.getElementById('modeIcon');
        elements.modeName = document.getElementById('modeName');
        elements.modeDesc = document.getElementById('modeDesc');
        elements.autoMode = document.getElementById('autoMode');
        elements.currentApp = document.getElementById('currentApp');
        elements.activityLevel = document.getElementById('activityLevel');
        elements.sessionTime = document.getElementById('sessionTime');
        elements.sessionProgress = document.getElementById('sessionProgress');
        elements.recommendationsList = document.getElementById('recommendationsList');
        elements.envSound = document.getElementById('envSound');
        elements.envNight = document.getElementById('envNight');
        elements.envFocus = document.getElementById('envFocus');
        elements.envNotif = document.getElementById('envNotif');
        elements.btnBreak = document.getElementById('btnBreak');
        elements.volumeSlider = document.getElementById('volumeSlider');
        elements.volumeValue = document.getElementById('volumeValue');
        elements.appsList = document.getElementById('appsList');
        elements.workTimeTotal = document.getElementById('workTimeTotal');
        elements.entertainmentTime = document.getElementById('entertainmentTime');
        elements.breakOverlay = document.getElementById('breakOverlay');
        elements.breakTimer = document.getElementById('breakTimer');
        elements.breakProgress = document.getElementById('breakProgress');
    }

    function bindEvents() {
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.dataset.page;
                navigateTo(page);
            });
        });

        // Auto mode toggle
        elements.autoMode?.addEventListener('change', (e) => {
            setAutoMode(e.target.checked);
        });

        // Break button
        elements.btnBreak?.addEventListener('click', startBreakMode);

        // Keyboard shortcuts for break
        document.addEventListener('keydown', (e) => {
            if (state.breakActive && (e.key === 'Escape' || e.key === ' ')) {
                e.preventDefault();
                stopBreakMode();
            }
        });

        // Sound cards
        document.querySelectorAll('.sound-card').forEach(card => {
            card.addEventListener('click', () => {
                const sound = card.dataset.sound;
                playSound(sound);
            });
        });

        // Volume slider
        elements.volumeSlider?.addEventListener('input', (e) => {
            const volume = e.target.value;
            elements.volumeValue.textContent = volume + '%';
            setVolume(volume / 100);
        });

        // Settings toggles
        bindSettingsEvents();
    }

    function bindSettingsEvents() {
        const settingHandlers = {
            'settingSoundEnabled': (v) => updateConfig('sound', { enabled: v }),
            'settingNightMode': (v) => updateConfig('display', { night_mode_enabled: v }),
            'settingBreaksEnabled': (v) => updateConfig('breaks', { enabled: v }),
            'settingNotifFilter': (v) => updateConfig('notifications', { filter_enabled: v }),
            'settingAutostart': (v) => setAutostart(v)
        };

        Object.keys(settingHandlers).forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', (e) => settingHandlers[id](e.target.checked));
            }
        });

        const workDuration = document.getElementById('settingWorkDuration');
        if (workDuration) {
            workDuration.addEventListener('change', (e) => {
                updateConfig('breaks', { work_duration: parseInt(e.target.value) });
            });
        }

        const colorTemp = document.getElementById('settingColorTemp');
        if (colorTemp) {
            colorTemp.addEventListener('input', (e) => {
                updateConfig('display', { color_temperature: parseInt(e.target.value) });
            });
        }
        
        // Загрузить статус автозагрузки
        loadAutostartStatus();
    }

    function navigateTo(page) {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === page);
        });

        document.querySelectorAll('.page').forEach(p => {
            p.classList.toggle('active', p.id === 'page-' + page);
        });

        if (page === 'stats') {
            loadStats();
        }
    }

    // API calls
    async function fetchAPI(endpoint, options = {}) {
        try {
            const response = await fetch(API_BASE + endpoint, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            setConnected(false);
            return null;
        }
    }

    async function fetchStatus() {
        const data = await fetchAPI('/api/status');
        if (data) {
            setConnected(true);
            state.status = data;
            updateUI();
        }
    }

    async function loadStats() {
        const data = await fetchAPI('/api/stats');
        if (data) {
            state.stats = data;
            updateStatsUI();
        }
    }

    async function loadConfig() {
        const data = await fetchAPI('/api/config');
        if (data) {
            state.config = data;
            updateSettingsUI();
        }
    }

    async function updateConfig(section, values) {
        await fetchAPI('/api/config', {
            method: 'POST',
            body: JSON.stringify({ [section]: values })
        });
    }

    async function setAutoMode(enabled) {
        await fetchAPI('/api/mode', {
            method: 'POST',
            body: JSON.stringify({ auto: enabled })
        });
    }

    function playSound(sound) {
        const volume = (elements.volumeSlider?.value || 30) / 100;
        
        // Остановить текущий звук
        if (audioPlayer) {
            audioPlayer.pause();
            audioPlayer = null;
        }
        
        if (sound === 'none') {
            state.currentSound = 'none';
            updateSoundCards();
            return;
        }
        
        // Создать новый аудио плеер
        audioPlayer = new Audio(`/sounds/${sound}.mp3`);
        audioPlayer.loop = true;
        audioPlayer.volume = volume;
        
        audioPlayer.play().then(() => {
            state.currentSound = sound;
            updateSoundCards();
        }).catch(err => {
            console.error('Ошибка воспроизведения:', err);
            state.currentSound = 'none';
            updateSoundCards();
        });
    }

    function setVolume(volume) {
        if (audioPlayer) {
            audioPlayer.volume = volume;
        }
    }

    function stopSound() {
        if (audioPlayer) {
            audioPlayer.pause();
            audioPlayer = null;
        }
        state.currentSound = 'none';
        updateSoundCards();
    }

    async function startBreak() {
        await fetchAPI('/api/break', { method: 'POST' });
    }

    function startBreakMode() {
        const breakDuration = state.config?.breaks?.break_duration || 10;
        state.breakSeconds = breakDuration * 60;
        state.breakActive = true;
        
        elements.breakOverlay?.classList.add('active');
        
        // Полноэкранный режим
        const overlay = elements.breakOverlay;
        if (overlay) {
            if (overlay.requestFullscreen) {
                overlay.requestFullscreen();
            } else if (overlay.webkitRequestFullscreen) {
                overlay.webkitRequestFullscreen();
            } else if (overlay.msRequestFullscreen) {
                overlay.msRequestFullscreen();
            }
        }
        
        updateBreakTimer();
        
        // Отправить на сервер
        startBreak();
        
        // Запустить таймер
        state.breakTimer = setInterval(() => {
            state.breakSeconds--;
            updateBreakTimer();
            
            if (state.breakSeconds <= 0) {
                stopBreakMode();
            }
        }, 1000);
    }

    function stopBreakMode() {
        state.breakActive = false;
        
        if (state.breakTimer) {
            clearInterval(state.breakTimer);
            state.breakTimer = null;
        }
        
        // Выйти из полноэкранного режима
        if (document.fullscreenElement || document.webkitFullscreenElement) {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            }
        }
        
        elements.breakOverlay?.classList.remove('active');
    }

    function updateBreakTimer() {
        const mins = Math.floor(state.breakSeconds / 60);
        const secs = state.breakSeconds % 60;
        
        if (elements.breakTimer) {
            elements.breakTimer.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
        }
        
        // Обновить прогресс
        const breakDuration = (state.config?.breaks?.break_duration || 10) * 60;
        const progress = ((breakDuration - state.breakSeconds) / breakDuration) * 100;
        
        if (elements.breakProgress) {
            elements.breakProgress.style.width = progress + '%';
        }
    }

    async function setAutostart(enabled) {
        await fetchAPI('/api/autostart', {
            method: 'POST',
            body: JSON.stringify({ enabled })
        });
    }

    async function loadAutostartStatus() {
        const data = await fetchAPI('/api/autostart');
        if (data) {
            const el = document.getElementById('settingAutostart');
            const desc = document.getElementById('autostartDesc');
            
            if (el) {
                el.checked = data.enabled;
                
                if (!data.available) {
                    el.disabled = true;
                    if (desc) {
                        desc.textContent = 'Доступно только в exe версии';
                    }
                }
            }
        }
    }

    // UI Updates
    function setConnected(connected) {
        state.connected = connected;
        elements.connectionStatus?.classList.toggle('disconnected', !connected);
        const statusText = elements.connectionStatus?.querySelector('.status-text');
        if (statusText) {
            statusText.textContent = connected ? 'Подключено' : 'Отключено';
        }
    }

    function updateUI() {
        const status = state.status;
        if (!status) return;

        // Mode
        if (status.analysis) {
            const mode = status.analysis.mode;
            const config = modeConfig[mode] || modeConfig.idle;
            
            if (elements.modeIcon) elements.modeIcon.innerHTML = config.icon;
            if (elements.modeName) elements.modeName.textContent = config.name;
            if (elements.modeDesc) elements.modeDesc.textContent = config.desc;

            // Session time
            const workMins = status.analysis.work_minutes || 0;
            const hours = Math.floor(workMins / 60);
            const mins = workMins % 60;
            if (elements.sessionTime) {
                elements.sessionTime.textContent = hours > 0 
                    ? `${hours}:${mins.toString().padStart(2, '0')}` 
                    : `${mins}:00`;
            }

            // Progress ring (50 min default work period)
            const progress = Math.min(workMins / 50, 1);
            const dashoffset = 283 * (1 - progress);
            if (elements.sessionProgress) {
                elements.sessionProgress.style.strokeDashoffset = dashoffset;
            }

            // Recommendations
            if (elements.recommendationsList) {
                const recs = status.analysis.recommendations || [];
                if (recs.length > 0) {
                    elements.recommendationsList.innerHTML = recs
                        .map(r => `<li>${r}</li>`)
                        .join('');
                } else {
                    elements.recommendationsList.innerHTML = '<li class="empty">Нет рекомендаций</li>';
                }
            }
        }

        // Activity
        if (status.activity) {
            if (elements.currentApp) {
                elements.currentApp.textContent = status.activity.current_app || '—';
            }
            
            if (elements.activityLevel) {
                elements.activityLevel.className = 'level-fill ' + (status.activity.activity_level || 'normal');
            }
        }

        // Environment
        if (status.environment) {
            const env = status.environment;
            
            // Используем локальный state.currentSound вместо серверного
            const soundActive = state.currentSound !== 'none';
            toggleEnvItem(elements.envSound, soundActive, 
                soundActive ? `Звук: ${getSoundName(state.currentSound)}` : 'Звук выкл.');
            toggleEnvItem(elements.envNight, env.night_mode, 
                env.night_mode ? 'Ночной вкл.' : 'Ночной выкл.');
            toggleEnvItem(elements.envFocus, env.focus_mode, 
                env.focus_mode ? 'Фокус вкл.' : 'Фокус выкл.');
            toggleEnvItem(elements.envNotif, env.notifications_filtered, 
                env.notifications_filtered ? 'Фильтр вкл.' : 'Уведомления');

            // Не перезаписываем currentSound с сервера - звук играет локально
            updateSoundCards();
        }
    }

    function toggleEnvItem(el, active, text) {
        if (!el) return;
        el.classList.toggle('active', active);
        const span = el.querySelector('span');
        if (span) span.textContent = text;
    }

    function getSoundName(sound) {
        const names = {
            rain: 'Дождь',
            forest: 'Лес',
            cafe: 'Кафе',
            ocean: 'Океан',
            fire: 'Камин',
            white_noise: 'Белый шум'
        };
        return names[sound] || sound;
    }

    function updateSoundCards() {
        document.querySelectorAll('.sound-card').forEach(card => {
            card.classList.toggle('active', card.dataset.sound === state.currentSound);
        });
    }

    function updateStatsUI() {
        const stats = state.stats;
        if (!stats) return;

        // Total times
        if (elements.workTimeTotal) {
            elements.workTimeTotal.textContent = formatTime(stats.work_seconds || 0);
        }
        if (elements.entertainmentTime) {
            elements.entertainmentTime.textContent = formatTime(stats.entertainment_seconds || 0);
        }

        // Apps list
        if (elements.appsList) {
            const apps = stats.apps || [];
            if (apps.length > 0) {
                elements.appsList.innerHTML = apps.map(app => `
                    <div class="app-item">
                        <span class="app-name">${app.app}</span>
                        <span class="app-time">${app.formatted}</span>
                    </div>
                `).join('');
            } else {
                elements.appsList.innerHTML = '<div class="empty">Нет данных</div>';
            }
        }
    }

    function updateSettingsUI() {
        const config = state.config;
        if (!config) return;

        const setChecked = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.checked = value;
        };

        const setValue = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.value = value;
        };

        setChecked('settingSoundEnabled', config.sound?.enabled);
        setChecked('settingNightMode', config.display?.night_mode_enabled);
        setChecked('settingBreaksEnabled', config.breaks?.enabled);
        setChecked('settingNotifFilter', config.notifications?.filter_enabled);
        setValue('settingWorkDuration', config.breaks?.work_duration);
        setValue('settingColorTemp', config.display?.color_temperature);
    }

    function formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        return `${hours}ч ${mins}м`;
    }

    // Polling
    function startPolling() {
        fetchStatus();
        setInterval(fetchStatus, UPDATE_INTERVAL);
    }

    // Start
    document.addEventListener('DOMContentLoaded', init);

})();
