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

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/status | current state |
| GET | /api/stats | daily statistics |
| GET/POST | /api/config | settings |
| POST | /api/sound | sound control |
| POST | /api/break | start break |
| GET/POST | /api/autostart | autostart |

## License

MIT
