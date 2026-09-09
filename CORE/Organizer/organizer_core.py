import os
from dataclasses import dataclass,field
from enum import Enum
from pathlib import Path
import shutil
from typing import Optional, List

class OrganizerMode(str,Enum):
    EXTENSION = "extension"
    FECHA = "fecha"
    NOMBRE = "nombre"

class OrganizerOperation(str, Enum):
    MOVE = "move"
    COPY = "copy"

class OrganizeStatus(str, Enum):
    PENDING = "pending"
    COLLISION = "collision"
    MOVED = "moved"
    COPIED = "copied"
    FAILED = "failed"
    IGNORED = "ignored"

@dataclass
class OrganizerConfig:
    mode: OrganizerMode = OrganizerMode.EXTENSION
    operation : OrganizerOperation = OrganizerOperation.MOVE
    recursive: bool = False
    autonumber: bool = False
    autonumber_start: int = 1
    autonumber_padding: int = 3
    keep_metadata: bool = True           # usar copy2 en vez de copy

@dataclass
class OrganizerPlan:
    original_path: Path
    destination_path: Path
    category: str
    status: OrganizeStatus.PENDING
    error: Optional[str] = None


FILE_CATEGORIES = {
    "PDF": [".pdf"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    "Videos": [".mp4", ".mov", ".avi", ".mkv"],
    "Music": [".mp3", ".wav", ".aac"],
    "Documents": [".doc", ".docx", ".txt", ".rtf",".md"],
    "Spreadsheets": [".xls", ".xlsx", ".csv"],
    "Archives": [".zip", ".rar", ".7z"],
}

def get_category_by_extension(path:Path)->str:
    ext = path.suffix.lower()
    for category,exts in FILE_CATEGORIES.items():
        if ext in exts: return category
    return "Others"

def get_category_by_date(path:Path)->str:
    ts = path.stat().st_mtime
    from datetime import datetime
    dt = datetime.fromtimestamp(ts)
    return f"{dt.year}-{dt.month:02d}"

def get_category_by_name(path:Path)-> str:
    name = path.stem
    if not name: return "Others"
    first_letter = name[0].upper()
    return first_letter


def autonumber_name(name: str, counter: int, padding: int)->str:
    stem = f"{counter:0{padding}d}"
    return f"{stem}_{name}"

#-------------------
def build_organizer_plan(folder:str, cfg:OrganizerConfig) -> List[OrganizerPlan]:
    base = Path(folder)

    if not base.is_dir():
        raise NotADirectoryError(f"La carpeta no existe: {folder}")

    files =[]

    if cfg.recursive: 
        for root,dirs,fs in os.walk(base):
            for filename in fs:
                files.append(Path(root)/filename)
    else:
        for f in base.iterdir():
            if f.is_file():
                files.append(f)

    plans : List[OrganizerPlan] = []
    counter = cfg.autonumber_start

    for path in files:
        if cfg.mode == OrganizerMode.EXTENSION:
            category = get_category_by_extension(path)
        elif cfg.mode == OrganizerMode.FECHA:
            category = get_category_by_date(path)
        elif cfg.mode == OrganizerMode.NOMBRE:
            category = get_category_by_name(path)
        else:
            category = "Others"

        dest_folder = base/category

        new_name = path.name

        if cfg.autonumber:
            new_name = autonumber_name(path.name,counter, cfg.autonumber_padding)
            counter +=1
        dest_path = dest_folder/new_name

        plan = OrganizerPlan(original_path=path, destination_path=dest_path, category=category, status=OrganizeStatus.PENDING)

        if dest_path.exists():
            plan.status = OrganizeStatus.COLLISION
            plan.error = "El destino ya existe."
        plans.append(plan)

    return plans

#-------------------
def apply_organizer_plan(plans:List[OrganizerPlan], operation: OrganizerOperation, keep_metadata:bool = True)->List[OrganizerPlan]:
    for plan in plans:
        if plan.status != OrganizeStatus.PENDING:
            continue

        try:
            plan.destination_path.parent.mkdir(parents=True, exist_ok=True) #creación de carpeta

            if operation == OrganizerOperation.MOVE:
                shutil.move(plan.original_path,plan.destination_path)
                plan.status = OrganizeStatus.MOVED
            elif operation == OrganizerOperation.COPY:
                if keep_metadata:
                    shutil.copy2(plan.original_path, plan.destination_path)
                else:
                    shutil.copy(plan.original_path,plan.destination_path)
                plan.status = OrganizeStatus.COPIED

        except Exception as exc:
            plan.status = OrganizeStatus.FAILED
            plan.error = str(exc)
    return plans
