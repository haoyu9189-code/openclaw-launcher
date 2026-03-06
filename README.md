<p align="center">
  <img src="openclaw-icon-128.png" alt="OpenClaw Logo" width="128" height="128">
</p>

<h1 align="center">OpenClaw Launcher</h1>

<p align="center">
  A desktop launcher for <a href="https://github.com/openclaw/openclaw">OpenClaw</a> — the open-source reimplementation of Captain Claw.
</p>

---

## About

OpenClaw Launcher is a standalone Windows desktop application that makes it easy to download, configure, and launch [OpenClaw](https://github.com/openclaw/openclaw). It provides a clean dark UI built with CustomTkinter.

## Features

- One-click download and install of OpenClaw
- Automatic game asset detection and configuration
- Built-in settings for resolution, audio, and gameplay options
- Level selector with quick launch
- Auto-update support
- Portable — single exe, no installation required

## Usage

1. Download `OpenClaw.exe` from the [Releases](../../releases) page
2. Run `OpenClaw.exe`
3. Follow the on-screen instructions to set up the game

## Building from Source

### Prerequisites

- Python 3.8+
- Dependencies: `customtkinter`, `Pillow`, `PyInstaller`

### Build

```bash
pip install customtkinter Pillow pyinstaller
python build.py
```

The executable will be generated in the `dist/` folder.

## Project Structure

| File | Description |
|------|-------------|
| `openclaw_launcher.py` | Main launcher application (UI + logic) |
| `build.py` | PyInstaller build script |
| `OpenClaw.exe` | Pre-built Windows executable |
| `openclaw.ico` | Application icon |

## Credits

- [OpenClaw](https://github.com/openclaw/openclaw) — the open-source Captain Claw engine this launcher is built for

## License

This project is licensed under the [MIT License](LICENSE).
