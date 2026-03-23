import json
import os
from datetime import datetime
from pathlib import Path

OBJECTS_FILE = "objects.json"
BACKUP_DIR = "backup"
MAX_BACKUPS = 10


def _safe_read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_objects(path=OBJECTS_FILE):
    data = _safe_read_json(path, [])
    return data if isinstance(data, list) else []


def save_objects(objects, path=OBJECTS_FILE):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(objects, f, ensure_ascii=False, indent=2)
    except Exception:
        return False

    _write_backup(objects)
    return True


def _write_backup(objects):
    try:
        backup_path = Path(BACKUP_DIR)
        backup_path.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        file_path = backup_path / f"objects_{stamp}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(objects, f, ensure_ascii=False, indent=2)

        backups = sorted(backup_path.glob("objects_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[MAX_BACKUPS:]:
            old.unlink(missing_ok=True)
    except Exception:
        return


def export_objects(objects, destination):
    with open(destination, "w", encoding="utf-8") as f:
        json.dump(objects, f, ensure_ascii=False, indent=2)


def import_objects(source):
    data = _safe_read_json(source, None)
    if not isinstance(data, list):
        raise ValueError("Файл должен содержать список объектов")
    return data
