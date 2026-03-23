import uuid
from datetime import datetime

DATE_FORMAT = "%d-%m-%Y"
PRIORITY_ORDER = {"Высокий": 0, "Средний": 1, "Низкий": 2}
CATEGORIES = ["Работа", "Личное", "Учёба"]
PRIORITIES = ["Высокий", "Средний", "Низкий"]


def normalize_task(raw):
    category = raw.get("category", "Личное")
    priority = raw.get("priority", "Средний")
    return {
        "id": str(raw.get("id") or uuid.uuid4()),
        "text": str(raw.get("text", "")).strip(),
        "done": bool(raw.get("done", False)),
        "deadline": str(raw.get("deadline", "без срока")).strip() or "без срока",
        "category": category if category in CATEGORIES else "Личное",
        "priority": priority if priority in PRIORITIES else "Средний",
    }


def parse_deadline(deadline_text):
    if not deadline_text or deadline_text.lower() == "без срока":
        return None
    try:
        return datetime.strptime(deadline_text, DATE_FORMAT).date()
    except ValueError:
        return None


def is_overdue(task, today=None):
    today = today or datetime.now().date()
    due = parse_deadline(task.get("deadline", ""))
    return due is not None and (not task.get("done")) and due < today


def tasks_for_today(tasks, today=None):
    today = today or datetime.now().date()
    return [t for t in tasks if (not t.get("done")) and parse_deadline(t.get("deadline", "")) == today]


def get_filtered_sorted_tasks(tasks, filters, sort_mode):
    status = filters.get("status", "Все")
    category = filters.get("category", "Все")
    priority = filters.get("priority", "Все")
    query = filters.get("query", "").strip().lower()

    rows = []
    for task in tasks:
        if query and query not in task["text"].lower():
            continue
        if status == "Выполненные" and not task["done"]:
            continue
        if status == "Невыполненные" and task["done"]:
            continue
        if category != "Все" and task["category"] != category:
            continue
        if priority != "Все" and task["priority"] != priority:
            continue
        rows.append(task)

    if sort_mode == "По дедлайну":
        rows.sort(key=lambda t: (parse_deadline(t["deadline"]) is None, parse_deadline(t["deadline"]) or datetime.max.date()))
    elif sort_mode == "По приоритету":
        rows.sort(key=lambda t: PRIORITY_ORDER.get(t["priority"], 99))
    elif sort_mode == "По статусу":
        rows.sort(key=lambda t: t["done"])

    return rows
