import json
from pathlib import Path
from typing import Dict, List, Optional

REGISTRY_PATH = Path(__file__).resolve().parent / "config" / "qualifications.yaml"


def _ensure_registry_dir() -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_registry() -> Dict[str, List[Dict[str, object]]]:
    _ensure_registry_dir()
    if not REGISTRY_PATH.exists():
        return {"qualifications": []}
    raw = REGISTRY_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return {"qualifications": []}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {"qualifications": []}
        data.setdefault("qualifications", [])
        return data
    except json.JSONDecodeError:
        return {"qualifications": []}


def save_registry(data: Dict[str, List[Dict[str, object]]]) -> None:
    _ensure_registry_dir()
    REGISTRY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_entries() -> List[Dict[str, object]]:
    return load_registry().get("qualifications", [])


def find_entry(name: str) -> Optional[Dict[str, object]]:
    name = (name or "").strip().lower()
    if not name:
        return None
    for entry in get_entries():
        if entry.get("name", "").strip().lower() == name:
            return entry
    return None


def get_module_choices(name: str) -> List[Dict[str, str]]:
    entry = find_entry(name)
    modules = entry.get("modules", []) if entry else []
    if not isinstance(modules, list):
        return []
    return [m for m in modules if isinstance(m, dict)]


def sync_registry_to_db() -> None:
    from .models import Qualification

    data = load_registry()
    for entry in data.get("qualifications", []):
        name = entry.get("name")
        if not name:
            continue
        saqa_id = entry.get("saqa_id", "") or ""
        Qualification.objects.update_or_create(
            name=name,
            defaults={"saqa_id": saqa_id}
        )


def ensure_entry_from_instance(instance) -> None:
    if instance is None:
        return
    data = load_registry()
    quals = data.setdefault("qualifications", [])
    target = None
    for entry in quals:
        if entry.get("name", "") == instance.name:
            target = entry
            break
    if target is None:
        target = {"name": instance.name, "modules": []}
        quals.append(target)
    if instance.saqa_id:
        target["saqa_id"] = instance.saqa_id
    save_registry(data)


def saqa_map_by_pk() -> Dict[str, str]:
    from .models import Qualification

    return {str(q.pk): q.saqa_id for q in Qualification.objects.all()}


def module_map_by_pk() -> Dict[str, List[Dict[str, str]]]:
    from .models import Qualification

    mapping: Dict[str, List[Dict[str, str]]] = {}
    for qual in Qualification.objects.all():
        modules = get_module_choices(qual.name)
        mapping[str(qual.pk)] = modules
    return mapping


def module_map_by_name() -> Dict[str, List[Dict[str, str]]]:
    mapping: Dict[str, List[Dict[str, str]]] = {}
    for entry in get_entries():
        mapping[entry.get("name", "")] = get_module_choices(entry.get("name", ""))
    return mapping