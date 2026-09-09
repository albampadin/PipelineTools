import os
import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta


class CleanerItemType(str, Enum):
    EMPTY_FOLDER = "Empty folder"
    DUPLICATE = "Duplicate"
    LARGE_FILE = "Large file"
    OLD_FILE = "Old file"
    TMP = "Temporal file"

class CleanerStatus(str, Enum):
    PENDING = "pending"
    DELETED = "deleted"
    FAILED = "failed"
    IGNORED = "ignored"

@dataclass
class CleanerConfig:
    recursive: bool = False

    check_empty_folder: bool = True
    check_duplicates: bool = True
    check_large_files: bool = False
    check_old_files : bool = False
    check_tmp_files: bool = False

    large_file_size_mb: int = 500
    old_file_days: int = 365


@dataclass
class CleanerPlan:
    path: Path
    kind: CleanerItemType
    status: CleanerStatus = CleanerStatus.PENDING
    info: str = "" 
    group_id: Optional[str] = None
    original_path: Optional[Path] = None
    error: Optional[str] = None


FIND_EXTENSIONS = {
    "TMP": [".tmp", ".temp",],
    "BACKUP": [ ".bak"],
    "OLD": [ ".old"]
}


def _get_files(path:Path, recursive:bool)->List[Path]:
    files = []

    if recursive:
        for root,dirs,fs in os.walk(path):
            for filename in fs:
                files.append(Path(root)/filename)
    else:
        for item in path.iterdir():
            if item.is_file():
                files.append(item)
    return files

def _get_directories(path:Path, recursive:bool)->List[Path]:
    directories = []

    if recursive:
        for root,dirs,fs in os.walk(path):
            for dirname in dirs:
                directories.append(Path(root)/dirname)
    else:
        for item in path.iterdir():
            if item.is_dir():
                directories.append(item)

    return directories

def _calculate_hash(path:Path, chunk_size: int = 1024*1024)->str:
    hasher= hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size)

            if not chunk:
                break

            hasher.update(chunk)

    return hasher.hexdigest()

def _find_empty_folder(path:Path, recursive: bool,)->List[CleanerPlan]:
    directories = _get_directories(path, recursive)
    directories.sort( key = lambda path: len(path.parts), reverse=True) #de más profundo a menos

    plans = []

    for directory in directories:
        try:
            if not any(directory.iterdir()):
                plans.append(CleanerPlan(path=directory, kind=CleanerItemType.EMPTY_FOLDER,info = "Carpeta vacía"))
        except Exception as exc:
            plans.append(CleanerPlan(path=directory, kind=CleanerItemType.EMPTY_FOLDER, status= CleanerStatus.FAILED, info="No sep udo comprobar la carpeta", error=str(exc)))

    return plans

def _find_duplicates(files:List[Path])->List[CleanerPlan]:
    files_by_size: Dict[int,List[Path]]={} #por logica dos archivos con tamaños distinto no deben ser idénticos

    for path in files:
        try: size = path.stat().st_size
        except OSError:
            continue

        files_by_size.setdefault(size,[]).append(path)

    plans = []
    group_counter = 1

    for size,same_size_files in files_by_size.items():
        if len(same_size_files) < 2: 
            continue

        hashes: Dict[str,List[Path]]={}

        for path in same_size_files:
            try: 
                file_hash = _calculate_hash(path)
            except Exception:
                continue

            hashes.setdefault(file_hash,[]).append(path)

        for file_hash,duplicate_files in hashes.items():
            if len(duplicate_files) < 2: 
                continue

            duplicate_files.sort(key=lambda path:path.stat().st_mtime)  #el archivo más antiguo es el original

            group_id = f"DUP-{group_counter}"
            group_counter +=1

            og = duplicate_files[0] #se considera al primero como el original

            for path in duplicate_files[1:]:
                plans.append(CleanerPlan(path=path, kind=CleanerItemType.DUPLICATE, info=f"Igual que: {og.name} ({og})", group_id=group_id, original_path=og))
    return plans

def _find_large_files(files: List[Path], size_mb: int)->List[CleanerPlan]:
    min_size = size_mb *1024*1024
    plans = []

    for path in files:
        try: size = path.stat().st_size
        except OSError: continue

        if size >= min_size:
            size_display = size/(1024*1024)
            plans.append(CleanerPlan(path=path, kind=CleanerItemType.LARGE_FILE, info=f"{size_display:.1f} MB"))

    return plans

def _find_old_files(files:List[Path], days: int)->List[CleanerPlan]:
    cutoff = datetime.now()-timedelta(days=days)
    plans = []

    for path in files:
        try: 
            modified = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError: 
            continue

        if modified < cutoff:
            age_days = (datetime.now() - modified).days
            plans.append(CleanerPlan(path=path,kind=CleanerItemType.OLD_FILE, info=f"No modificado desde hace {age_days} dias"))
        
    return plans

def _find_tmp_files(files:List[Path])-> List[CleanerPlan]:
    plans = []    

    for path in files:
        ext = path.suffix.lower()

        for cat, exts in FIND_EXTENSIONS.items():
            if ext in exts:
                plans.append(CleanerPlan(path=path, kind=CleanerItemType.TMP, info= f"{cat}: '{ext}'"))
                break

    return plans 


#-------------------
def build_cleaner_plan(folder:str, cfg:CleanerConfig) -> List[CleanerPlan]:
    base = Path(folder)

    if not base.is_dir():
        raise NotADirectoryError(f"La carpeta no existe: {folder}")

    plans = []

    if cfg.check_empty_folder:
        plans.extend(_find_empty_folder(base,cfg.recursive))

    files = _get_files(base,cfg.recursive)

    if cfg.check_duplicates: plans.extend(_find_duplicates(files))
    if cfg.check_old_files: plans.extend(_find_old_files(files, cfg.old_file_days))
    if cfg.check_large_files:plans.extend(_find_large_files(files,cfg.large_file_size_mb))
    if cfg.check_tmp_files:plans.extend(_find_tmp_files(files))

    return plans

#-------------------
def apply_cleaner_plan(plans:List[CleanerPlan])->List[CleanerPlan]:
    for plan in plans:
        if plan.status != CleanerStatus.PENDING:
            continue

        try: 
            if plan.kind == CleanerItemType.EMPTY_FOLDER: plan.path.rmdir()
            else: plan.path.unlink()

            plan.status = CleanerStatus.DELETED

        except Exception as exc:
            plan.status = CleanerStatus.FAILED
            plan.error = str(exc)

    return plans
