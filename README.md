# 📁 File Organizer

Real-time Downloads folder organizer powered by [`watchdog`](https://github.com/gorakhargosh/watchdog).  
Monitors your **Downloads** folder and automatically sorts new files into sub-folders by type — the moment a download finishes.

---

## ✨ Features

| Feature | Detail |
|---|---|
| Real-time monitoring | Uses `watchdog` Observer; reacts in under a second |
| Skip in-progress downloads | Ignores `.crdownload`, `.part`, `.tmp`, etc. |
| Stability check | Waits for file size to stop growing before moving |
| Duplicate handling | Renames to `file_1.pdf`, `file_2.pdf`, … automatically |
| Easy configuration | Edit `config.json` — no code changes needed |
| Rotating log file | `logs/organizer.log` (5 MB × 3 backups) |
| Graceful shutdown | Ctrl+C drains the thread pool cleanly |

---

## 📂 Project Structure

```
File Organizer/
├── config.json          # Extension mappings & settings
├── main.py              # Entry point
├── requirements.txt
├── logs/
│   └── organizer.log    # Created automatically at runtime
└── src/
    ├── __init__.py
    ├── config_loader.py # Loads & validates config.json
    ├── file_handler.py  # Move logic, duplicate resolution, error handling
    ├── logger_setup.py  # Rotating file + console logging
    └── watcher.py       # Watchdog event handler & observer factory
```

---

## 🐍 Setup with Miniconda

### 1. Create a dedicated Conda environment

```bash
conda create -n file-organizer python=3.11 -y
conda activate file-organizer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Script

### Foreground (development / testing)

```bash
# Make sure the conda env is active
conda activate file-organizer

python main.py
```

You'll see live output in the terminal.  Press **Ctrl+C** to stop.

### Custom config path

```bash
python main.py --config /path/to/my_config.json
```

---

## 🔄 Running in the Background

### Windows — using `pythonw` (no console window)

```powershell
# From inside the project folder, with the env active
conda activate file-organizer

# Start silently in background (logs still go to organizer.log)
Start-Process pythonw -ArgumentList "main.py" -WorkingDirectory (Get-Location) -WindowStyle Hidden
```

To stop it, find the process in Task Manager → Python, or run:

```powershell
Stop-Process -Name pythonw
```

#### Windows — auto-start with Task Scheduler

1. Open **Task Scheduler** → *Create Basic Task*
2. Trigger: **At log on**
3. Action: **Start a program**
   - Program: `C:\Users\<YOU>\miniconda3\envs\file-organizer\pythonw.exe`
   - Arguments: `main.py`
   - Start in: `D:\Development\Python\File Organizer`
4. Finish.

---

### macOS / Linux — using `nohup`

```bash
conda activate file-organizer
nohup python main.py > /dev/null 2>&1 &
echo $! > organizer.pid   # save PID so you can stop it later
```

To stop:

```bash
kill $(cat organizer.pid)
```

#### macOS — auto-start with launchd

Create `~/Library/LaunchAgents/com.fileorganizer.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>           <string>com.fileorganizer</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/YOUR_USER/miniconda3/envs/file-organizer/bin/python</string>
    <string>/path/to/File Organizer/main.py</string>
  </array>
  <key>RunAtLoad</key>       <true/>
  <key>KeepAlive</key>       <true/>
  <key>WorkingDirectory</key><string>/path/to/File Organizer</string>
</dict>
</plist>
```

Then load it:

```bash
launchctl load ~/Library/LaunchAgents/com.fileorganizer.plist
```

#### Linux — systemd user service

Create `~/.config/systemd/user/file-organizer.service`:

```ini
[Unit]
Description=File Organizer - Downloads watcher

[Service]
ExecStart=/home/YOUR_USER/miniconda3/envs/file-organizer/bin/python main.py
WorkingDirectory=/path/to/File Organizer
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now file-organizer
systemctl --user status file-organizer   # verify
```

---

## ⚙️ Customising `config.json`

```jsonc
{
  "watch_folder": "~/Downloads",          // Change to any folder path
  "categories": {
    "Documents": [".pdf", ".docx", ...],  // Add/remove extensions freely
    "MyCustomFolder": [".fig", ".sketch"] // Add entirely new categories
  },
  "temp_extensions": [".crdownload", ".part", ".tmp"],
  "log_file": "logs/organizer.log",
  "log_level": "INFO",                    // DEBUG for verbose output
  "move_delay_seconds": 1.5               // Increase for slow disks / large files
}
```

All changes take effect on the **next restart** of the script.

---

## 📋 Log Output Example

```
2026-10-24 08:15:32 | INFO     | src.watcher      | Observer scheduled for: /Users/azhar/Downloads
2026-10-24 08:15:32 | INFO     | __main__          | Observer started. Press Ctrl+C to stop.
2026-10-24 08:16:10 | INFO     | src.file_handler  | Moved: 'report.pdf'  ->  'Downloads/Documents/report.pdf'
2026-10-24 08:16:45 | INFO     | src.file_handler  | Moved: 'song.mp3'    ->  'Downloads/Audio/song.mp3'
2026-10-24 08:17:01 | INFO     | src.file_handler  | Moved: 'report_1.pdf'->  'Downloads/Documents/report_1.pdf'
2026-10-24 08:17:22 | WARNING  | src.file_handler  | PermissionError moving 'installer.exe': file may still be in use
```
