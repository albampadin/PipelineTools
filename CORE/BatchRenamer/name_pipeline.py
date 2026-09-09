import os
from typing import Callable, List

class NameTransformPipeline:
    def __init__(self):
        self.steps: List[Callable[[str], str]] = []

    def add(self, func: Callable[[str], str]):
        self.steps.append(func)

    def run(self, name: str) -> str:
        for step in self.steps:
            name = step(name)
        return name

# ---- TRANSFORMACIONES DISPONIBLES -----
def multi_replace(replacements: dict[str, str]):
    return lambda name: _multi_replace(name, replacements)

def _multi_replace(name: str, replacements:dict[str,str]) -> str:
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name

def add_prefix_suffix(prefix: str = "", suffix: str = ""):
    return  lambda name: f"{prefix}{name}{suffix}"

def normalize_case(mode: str):
    mode = mode.lower()
    if mode == "minúscula":
        return lambda name: name.lower()
    if mode == "mayúscula":
        return lambda name: name.upper()
    if mode == "título":
        return lambda name: name.title()
    return lambda name: name

def auto_numbering(start: int = 1, padding: int = 3):
    counter = {"value": start}
    return lambda name: _auto_number(name, counter, padding)

def _auto_number(name: str, counter: dict, padding:int) -> str:
    num = str(counter["value"]).zfill(padding)
    counter["value"] += 1
    return f"{name}_{num}"


# ---- FUNCIÓN PRINCIPAL ------
def build_new_name(filename: str, pipeline: NameTransformPipeline) -> str:
    name, ext = os.path.splitext(filename)
    new_name = pipeline.run(name)
    return f"{new_name}{ext}"
