# Termux Storage Manager

A lightweight, self-hosted web dashboard for managing storage, packages and backups inside **Termux on Android**. Runs a small Flask server on your phone and serves a sleek dark-themed UI at `localhost:5000`.

No cloud. No accounts. Everything runs locally on your device.

---

## Features

### 📊 Storage Overview

- Total Termux storage usage
- Breakdown of `$HOME` and `$PREFIX` (usr)
- Live disk usage bar (total / used / available / percent) for `/data`

### 🏠 Home Folder Browser

- Lists files and folders in `$HOME` with sizes
- Sort by size to find the biggest space hogs
- One-click delete (with confirmation)
- Live search filter

### 📦 APT Packages

- Lists all installed packages larger than 1 MB, sorted by size
- One-click uninstall (uses `pkg uninstall -y`)
- Search filter

### 🐍 Pip Packages

- Lists installed Python packages
- Uninstall individual packages
- Purge pip cache with one click

### 🧹 Cleanup Tools

- Clean APT cache (`pkg clean`)
- Clean pip cache
- Recursively remove all `__pycache__` folders in `$HOME`
- Safe path deletion by absolute path

### 💾 Backup and Restore

- **Full backup** — tarball of your entire Termux home
- **Scripts backup** — tarball of only your scripts/ folder
- Automatic `.txt` restore guide generated alongside every backup
- Backups saved to `/sdcard/` for easy transfer

---

## Project Structure

    termuxBR/
    ├── app.py              Flask backend + all API endpoints
    ├── SETUP.txt           Original setup instructions
    ├── templates/
    │   └── index.html      Single-page dashboard UI
    └── README.md           This file

---

## Getting Started

### Requirements

- Termux installed on Android
- Python 3.8+
- Flask
- `pkg` package manager (comes with Termux)
- Optional: `termux-api` for `termux-open-url` (auto-browser-open)

### Install

    pkg install python
    pip install flask

### Configure

Copy the project into your Termux home:

    mkdir -p ~/storage_manager/templates
    cp app.py ~/storage_manager/
    cp templates/index.html ~/storage_manager/templates/

### Run

    cd ~/storage_manager
    python app.py

Then open **http://localhost:5000** in your browser (auto-opens if `termux-api` is installed).

### Remote access (same Wi-Fi)

The server binds to `0.0.0.0:5000`, so you can access it from any device on the same network:

    ip addr | grep 192.168

Then open `http://<phone-ip>:5000` from your laptop.

---

## API Reference

Base URL: `http://localhost:5000`. All endpoints return JSON unless noted.

### Storage

| Method | Endpoint                       | Purpose                                |
|--------|--------------------------------|----------------------------------------|
| GET    | `/api/storage/overview`        | Total Termux / home / usr sizes + disk |
| GET    | `/api/storage/home_breakdown`  | Top 30 largest items in `$HOME`        |

### Packages (APT)

| Method | Endpoint                  | Purpose                        |
|--------|---------------------------|--------------------------------|
| GET    | `/api/packages/large`     | Installed packages > 1 MB      |
| POST   | `/api/packages/delete`    | Uninstall a package by name    |

### Pip

| Method | Endpoint                 | Purpose                  |
|--------|--------------------------|--------------------------|
| GET    | `/api/pip/list`          | Installed pip packages   |
| POST   | `/api/pip/uninstall`     | Uninstall a package      |
| POST   | `/api/pip/cache_purge`   | Clear pip cache          |

### Cleanup

| Method | Endpoint                     | Purpose                                 |
|--------|------------------------------|-----------------------------------------|
| POST   | `/api/cleanup/apt`           | Run `pkg clean`                         |
| POST   | `/api/cleanup/pycache`       | Recursively delete all `__pycache__`    |
| POST   | `/api/cleanup/delete_path`   | Delete a file/folder by absolute path   |

### Backup

| Method | Endpoint                | Purpose                         |
|--------|-------------------------|---------------------------------|
| POST   | `/api/backup/full`      | Tarball entire `$HOME`          |
| POST   | `/api/backup/scripts`   | Tarball scripts-only backup     |

Each backup endpoint also writes a matching `*_RESTORE.txt` guide next to the archive.

---

## Safety Notes

- **Package names are sanitised** — shell metacharacters (`;`, `&`, `|`, `` ` ``, `$`, `(`, `)`) are rejected before running `pkg uninstall`.
- **Delete operations require confirmation** in the UI.
- **Backups are written to `/sdcard/`**, not into Termux home — so a wipe of `$HOME` doesn't destroy your backups.
- **No external network access** — the app only ever talks to local `subprocess` commands on your device.

### Common errors and fixes

| Error                       | Fix                                      |
|-----------------------------|------------------------------------------|
| Permission denied           | `chmod -R 700 /data/data/com.termux/files/home` |
| No space left on device     | Free phone storage first                 |
| Cannot open backup file     | Check `/sdcard/*.tar.gz` exists          |
| Packages not responding     | `pkg update && pkg upgrade -y`           |

---

## Tech Stack

- **Backend:** Python 3, Flask, `subprocess`
- **Frontend:** Vanilla JavaScript, HTML, CSS (no framework, no build step)
- **Fonts:** JetBrains Mono, Space Grotesk (Google Fonts)
- **Platform:** Termux (Android)

---

## Credits

Made by [@tusharsharmalogic-cmyk](https://github.com/tusharsharmalogic-cmyk)

Other projects:
- [COREX](https://github.com/tusharsharmalogic-cmyk/COREX) — 2D Phaser game
- [my-journal](https://github.com/tusharsharmalogic-cmyk/my-journal) — Self-hosted journaling app