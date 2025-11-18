"""Utilities for loading randomization metadata from YAML configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml


CONFIG_PATH = Path(__file__).resolve().parent / "config" / "randomization.yaml"


@lru_cache
def _load_config() -> Dict[str, object]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        return {}
    return data


def get_qualification_meta(qualification_name: str) -> Dict[str, object]:
    data = _load_config()
    quals = data.get("qualifications", {})
    if not isinstance(quals, dict):
        return {}
    meta = quals.get(qualification_name, {})
    return meta if isinstance(meta, dict) else {}


def get_module_meta(qualification_name: str, module_code: str) -> Dict[str, object]:
    qual_meta = get_qualification_meta(qualification_name)
    modules = qual_meta.get("modules", {})
    if not isinstance(modules, dict):
        return {}
    meta = modules.get(module_code, {})
    return meta if isinstance(meta, dict) else {}


def allowed_letters(qualification_name: str, module_code: str) -> List[str]:
    module_meta = get_module_meta(qualification_name, module_code)
    letters = module_meta.get("letters", [])
    if not isinstance(letters, (list, tuple)):
        return []
    return [str(letter) for letter in letters]


def cover_title(qualification_name: str, module_code: str) -> Optional[str]:
    module_meta = get_module_meta(qualification_name, module_code)
    value = module_meta.get("cover_title")
    return str(value) if value else None


def randomization_status(qualification_name: str, module_code: str) -> str:
    letters = allowed_letters(qualification_name, module_code)
    if len(letters) > 1:
        return "paired"
    if letters:
        return "single"
    return "unconfigured"
