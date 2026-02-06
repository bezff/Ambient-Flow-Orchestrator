<p align="center">
  <img src="banner.png" alt="AFO Banner" width="100%">
</p>

# AFO

**Ambient Flow Orchestrator** — a Windows application that monitors your activity and automatically adjusts your work environment to match your current task.

---

## Why

When working at a computer, you want everything to be just right: the right background sounds, comfortable screen brightness, minimal distracting notifications. AFO does this automatically — it watches which apps are open, determines your mode (work, study, rest) and adjusts the environment.

## Features

- Tracks active applications and time spent in them
- Understands when you're in "flow" vs just scrolling feeds
- Plays ambient sounds (rain, cafe, noise) when you need to focus
- Switches screen to warm mode in the evening
- Reminds you to take breaks
- Health reminders — water, stretching, eye rest
- Procrastination detection — warns when spending too much time in entertainment apps during work hours
- Pomodoro timer — flexible work/break intervals with visualization and statistics
- Global hotkeys for quick control
- Auto-start with Windows (configurable in the app)


## Installation

Requires Windows 10/11 and Python 3.10+

```
pip install -r requirements.txt
```

## Building exe

Run `build.bat` — it will create `dist/AFO.exe`

## Auto-start

In the app settings there's an "Auto-start" toggle — it will add AFO to Windows startup.

> Only works in exe version

## Hotkeys

| Shortcut | Action |
|----------|--------|
| `Ctrl+Alt+M` | Toggle ambient sound |
| `Ctrl+Alt+B` | Start break |
| `Ctrl+Alt+P` | Start/pause Pomodoro |
| `Ctrl+Alt+S` | Skip Pomodoro phase |

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/status | current state |
| GET | /api/stats | daily statistics |
| GET/POST | /api/config | settings |
| POST | /api/sound | sound control |
| POST | /api/break | start break |
| GET/POST | /api/autostart | autostart |
| GET/POST | /api/reminders | reminder settings |
| POST | /api/reminders/snooze | snooze reminder |
| POST | /api/reminders/dismiss | mark as done (reset timer) |
| GET/POST | /api/procrastination | procrastination detection settings |
| GET/POST | /api/pomodoro | pomodoro status and settings |
| POST | /api/pomodoro/start | start timer |
| POST | /api/pomodoro/pause | pause/resume |
| POST | /api/pomodoro/stop | stop timer |
| POST | /api/pomodoro/skip | skip phase |
| GET/POST | /api/hotkeys | hotkey settings |

## License

MIT
