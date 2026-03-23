import uuid

TYPE_COLORS = {
    "Тип A": "#22c55e",
    "Тип B": "#eab308",
    "Тип C": "#ef4444",
}


def normalize_object(raw):
    obj_type = raw.get("type", "Тип A")
    if obj_type not in TYPE_COLORS:
        obj_type = "Тип A"
    return {
        "id": str(raw.get("id") or uuid.uuid4()),
        "name": str(raw.get("name", "объект")).strip() or "объект",
        "x": float(raw.get("x", 0)),
        "y": float(raw.get("y", 0)),
        "radius": max(0, int(raw.get("radius", 50))),
        "type": obj_type,
        "show_radius": bool(raw.get("show_radius", True)),
    }
