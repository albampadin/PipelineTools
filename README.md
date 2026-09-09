# PipelineTools

Suite de herramientas para automatizar y agilizar tareas habituales dentro de un pipeline de producción y organización de archivos.
El proyecto está desarrollado en Python y utiliza PyQt5 para la interfaz gráfica.

## Características
Actualmente el proyecto incluye tres herramientas orientadas a la gestión y organización de archivos:

- **Batch Renamer**
  - Renombrado masivo de archivos.
  - Preview antes de aplicar cambios.
  - Selección individual de elementos.
  - Seleccionar, deseleccionar todo e invertir selección.
  - Prefijos y sufijos.
  - Reemplazos de texto.
  - Múltiples reemplazos.
  - Normalización de mayúsculas/minúsculas.
  - Auto-numbering.
  - Detección de coincidencias.
  - Renombrado recursivo.
  - Renombrado de carpetas.
  - Guardado y carga de configuraciones.

- **File Organizer**
  - Organización de archivos según diferentes criterios (Extensión, Alfabéticamente, Fecha (Año-Mes)).
  - Preview de las operaciones.
  - Selección de operaciones antes de ejecutarlas.
  - Opción de mover o copiar los elementos seleccionados.

- **File Cleaner**
  - Detección de archivos que pueden ser eliminados según criterios (Carpetas vacías, duplicados, archivos temporales, archivos antiguos y grandes archivos).
  - Preview antes de borrar.
  - Selección de elementos.
  - Aplicación controlada de las operaciones.
 
[![Vista general de la herramienta](images/demo.jpg)](https://github.com/albampadin/PipelineTools)

---

## Uso
```
  python launcher.py
```

Esto abre una única ventana con un panel lateral para cambiar entre herramientas. Las herramientas siguen un flujo común:

**Seleccionar Carpeta → Preview → Revisar y Seleccionar → Aplicar**

La aplicación no modifica archivos directamente al generar una preview.
Primero se genera un plan de operaciones que el usuario puede revisar y seleccionar qué elementos quiere procesar para finalmente aplicar los cambios.
Este enfoque busca reducir errores y hacer las operaciones sobre archivos más seguras y predecibles.

---

## Tecnologías

- Python 3
- PyQt5

## Estructura del proyecto

```text
PipelineTools/
│
├── CORE/             →  genera y ejecuta los planes de operaciones
│   ├── BatchRenamer/
│   │   └── batch_renamer_core.py
│   │
│   ├── Cleaner/
│   │   └── cleaner_core.py
│   │
│   └── Organizer/
│       └── organizer_core.py
│
├── UI/                →  interacción con el usuario (PyQt5)
│   ├── base_tool.py
│   ├── batch_renamer_ui.py
│   ├── cleaner_ui.py
│   └── organizer_ui.py
│
├── requirements.txt
├── README.md
└── launcher.py
```

Añadir una herramienta nueva no requiere tocar **'launcher.py'** más que para registrarla en *TOOL_REGISTRY*: solo hace falta un módulo en *CORE/<Herramienta>/* con la lógica pura y una clase en *UI/* que herede de **'BaseTool.py'**.

---

## Estado del proyecto

El proyecto se encuentra actualmente en desarrollo.
Las herramientas se están construyendo progresivamente manteniendo una estructura común tanto entre interfaz como en lógica.

---

## Licencia
Este proyecto está bajo licencia MIT - ver [LICENSE](LICENSE).
La interfaz se encarga de la interacción con el usuario y el CORE se encarga de generar y ejecutar los planes de operaciones
