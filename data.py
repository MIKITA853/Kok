import json
import os
from datetime import datetime
from pathlib import Path

FILE_NAME = "tasks.json"
CONFIG_NAME = "config.json"
BACKUP_DIR = "backup"
MAX_BACKUPS = 10
DATE_FORMAT = "%d-%m-%Y"


def _safe_read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return default


def load_tasks(path=FILE_NAME):
    raw = _safe_read_json(path, [])
    if not isinstance(raw, list):
        return []
    return raw


def save_tasks(tasks, path=FILE_NAME):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=4)
    except Exception:
        return False

    _write_backup(tasks)
    return True


def _write_backup(tasks):
    try:
        backup_path = Path(BACKUP_DIR)
        backup_path.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        file_path = backup_path / f"tasks_{stamp}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=4)

        backups = sorted(backup_path.glob("tasks_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[MAX_BACKUPS:]:
            old.unlink(missing_ok=True)
    except Exception:
        # Бэкап не должен ломать основной save.
        return


def export_tasks(tasks, destination):
    with open(destination, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)


def import_tasks(source):
    data = _safe_read_json(source, None)
    if not isinstance(data, list):
        raise ValueError("Файл должен содержать список задач")
    return data


def load_config(path=CONFIG_NAME):
    cfg = _safe_read_json(path, {})
    if not isinstance(cfg, dict):
        return {"theme": "dark"}
    return {"theme": cfg.get("theme", "dark")}


def save_config(config, path=CONFIG_NAME):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False
