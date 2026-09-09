import json
import os

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional

_temp_counter = 0

from CORE.BatchRenamer.name_pipeline import (
    NameTransformPipeline,
    build_new_name,
    multi_replace,
    add_prefix_suffix,
    normalize_case,
    auto_numbering,
)

#--------- # STATUS ------
class RenameStatus(str, Enum):
    PENDING = "pending"
    COLLISION = "collision"
    RENAMED = "renamed"
    FAILED = "failed"
    IGNORED = "ignored"


# ---- CONFIGURACIÓN ----
@dataclass
class RenameConfig:
    # Configuración reutilizable del renombrado. Esta clase representa LO QUE QUIERE HACER EL USUARIO. Se puede guardar/cargar fácilmente como JSON
    prefix: str = ""
    suffix: str = ""
    replace_old: str = ""
    replace_new: str = ""

    multi_replacements: dict[str, str] = field(default_factory=dict)
    normalize: Optional[str] = None
    autonumber: bool = False
    autonumber_start: int = 1
    autonumber_padding: int = 3

    rename_folders: bool = False
    recursive: bool = False

# ---------- PLAN DE RENOMBRADO ------
@dataclass
class RenamePlan:
    #   Representa un posible cambio. NO ejecuta nada sobre el disco.
    original_name: str
    new_name: str
    original_path: str
    new_path: str

    status: RenameStatus = RenameStatus.PENDING
    error: Optional[str] = None


# -------- JSON -----
def save_config(config: RenameConfig, filepath: str):
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(asdict(config), file,indent=4, ensure_ascii=False)

def load_config(filepath: str) -> RenameConfig:
    with open(filepath, "r", encoding="utf-8") as file:
        return RenameConfig(**json.load(file))

# ------- PIPELINE -------
def build_pipeline(config: RenameConfig) -> NameTransformPipeline:
    # 1. Construye el pipeline a partir de RenameConfig
    pipeline = NameTransformPipeline()

    # 2. Múltiples reemplazos
    if config.multi_replacements: pipeline.add(multi_replace(config.multi_replacements))

    # 3. Reemplazo simple
    if config.replace_old:pipeline.add(multi_replace({config.replace_old: config.replace_new}))

    # 4. Normalización
    if config.normalize: pipeline.add( normalize_case(config.normalize))

    # 5. Prefijo + sufijo
    if config.prefix or config.suffix: pipeline.add(add_prefix_suffix(config.prefix,config.suffix))

    # 6. Autonumerado
    if config.autonumber: pipeline.add(auto_numbering(start=config.autonumber_start,padding=config.autonumber_padding))

    return pipeline

#---- VALIDACIÓN DE NOMBRES------
def validate_new_name(new_name: str) -> Optional[str]:
    #    Comprueba si el nombre generado es válido. Devuelve un mensaje de error si no es válido. Devuelve None si es correcto.
    if not new_name: return "El nombre generado está vacío."
    # Un nombre de archivo no debería contener separadores.
    if "/" in new_name or "\\" in new_name: return ("El nombre generado contiene un separador de ruta.")
    # Windows tiene restricciones adicionales.
    if os.name == "nt":
        invalid_chars = '<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars):
            return (f"El nombre contiene caracteres no válidos: '{new_name!r}'")
        
    return None

# ------BUILD RENAME PLAN & RECURSIVO--------
def build_rename_plan(folder: str, config: RenameConfig) -> list[RenamePlan]:
    # Construye un plan de renombrado. NO modifica ningún archivo.

    if not os.path.isdir(folder): 
        raise NotADirectoryError(f"La carpeta no existe o no es válida: {folder}")

    paths =[]

    if config.recursive:
        for root, dirs, files in os.walk(folder):
            for f in files:                         #archivos
                paths.append(os.path.join(root,f))
            if config.rename_folders:               #carpetas
                for d in dirs:
                    paths.append(os.path.join(root,d))
    else:
        for e in os.listdir(folder):
            full = os.path.join(folder,e)
            if os.path.isfile(full):
                paths.append(full)
            elif config.rename_folders and os.path.isdir(full):
                paths.append(full)


    pipeline = build_pipeline(config)
    plans = []

    # Crear planes
    for path in paths:
        filename = os.path.basename(path)
        folder_path = os.path.dirname(path)

        new_name = build_new_name(filename,pipeline)
        new_path = os.path.join(folder_path, new_name)

        plan = RenamePlan(original_name=filename, new_name=new_name, original_path=path, new_path=new_path)

        # Validar nombre generado
        error = validate_new_name(new_name)
        if error:
            plan.status = RenameStatus.COLLISION
            plan.error = error
        plans.append(plan)


    #  DETECTAR COINCIDENCIAS INTERNAS 
    by_new_name: dict[str, list[RenamePlan]] = {}
    for plan in plans:
        key = os.path.normcase(os.path.abspath(plan.new_path))
        by_new_name.setdefault( key,[]).append(plan)

    for group in by_new_name.values():
        if len(group) > 1:
            for plan in group:
                plan.status = RenameStatus.COLLISION
                plan.error = (f"Varios archivos quieren utilizar el mismo nombre: '{plan.new_name}'." )

    #COINCIDENCIAS EXTERNAS
    original_paths = {os.path.normcase(os.path.abspath(plan.original_path)) for plan in plans}

    for plan in plans:
        if plan.status != RenameStatus.PENDING:
            continue

        original_key = os.path.normcase(os.path.abspath(plan.original_path))
        destination_key = os.path.normcase(os.path.abspath(plan.new_path))

        if original_key != destination_key and os.path.lexists(plan.new_path):
            if destination_key not in original_paths:
                plan.status = RenameStatus.COLLISION 
                plan.error = ("El destino ya existe y no forma parte de la ejecución actual.")

    return plans


def _make_temp_path(original_path: str) -> str:     # Genera una ruta temporal única.
    global _temp_counter

    directory = os.path.dirname(original_path)
    filename = os.path.basename(original_path)

    while True:
        temp_name = (f".tmp_rename_{_temp_counter}_{filename}")
        _temp_counter += 1
        temp_path = os.path.join(directory,temp_name)
        if not os.path.lexists(temp_path):
            return temp_path

#------------------------------------------------------
def apply_rename_plan(plans: list[RenamePlan]) -> list[RenamePlan]: # Ejecuta el plan de renombrado. Utiliza nombres temporales para permitir: A -> B & B -> A
    pending = [plan for plan in plans if plan.status == RenameStatus.PENDING]
    pending.sort(key=lambda plan: plan.original_path.count(os.sep),reverse=True)

    # PASO 1. Mover todos los originales a nombres temporales.
    temporary_moves: list[tuple[RenamePlan, str]] = []
    for plan in pending:
        orig = os.path.normcase(os.path.abspath(plan.original_path))
        dest = os.path.normcase(os.path.abspath(plan.new_path))

        if orig == dest:   continue # No hay cambio.

        temp_path = _make_temp_path(plan.original_path)
        try:
            os.rename(plan.original_path, temp_path)
            temporary_moves.append((plan,temp_path))
        except OSError as exc:
            plan.status = RenameStatus.FAILED
            plan.error = str(exc)

    # PASO 2. Mover temporales a destinos finales.
    for plan, temp_path in temporary_moves:
        try:        # Por seguridad, comprobamos que el destino no haya aparecido mientras ejecutábamos el plan.
            if os.path.lexists(plan.new_path):
                raise FileExistsError( f"El destino ya existe: {plan.new_path}")
            
            os.rename(temp_path, plan.new_path)
            plan.status = RenameStatus.RENAMED
            plan.error = None

        except OSError as exc:
            plan.status = RenameStatus.FAILED
            plan.error = str(exc)
            
            try:       # Intentar restaurar el original
                if os.path.lexists(temp_path): 
                    os.rename(temp_path,plan.original_path)
            except OSError:
                pass

    # PASO 3. Marcar archivos cuyo nombre no cambia.
    for plan in plans:
        if plan.status == RenameStatus.PENDING:
            plan.status = RenameStatus.RENAMED

    return plans


# ------ Log Helpers -> Meter a UI -------
def has_errors(plans: list[RenamePlan]) -> bool:
    return any(plan.status in {RenameStatus.COLLISION, RenameStatus.FAILED} for plan in plans)

def has_pending(plans: list[RenamePlan]) -> bool:
    return any(plan.status == RenameStatus.PENDING for plan in plans)

def plan_summary(plans: list[RenamePlan]) -> dict:
    summary = {
        "total": len(plans),
        "pending": 0,
        "collision": 0,
        "renamed": 0,
        "failed": 0,
        "ignored":0,
    }
    for plan in plans: 
        summary[plan.status.value] += 1
    return summary