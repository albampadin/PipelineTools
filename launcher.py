""" Launcher de Pipeline Tools.
Desconoce el funcionamiento de las herramientas, solo las registra y las añade,
Version actual: lista a mno. A futuro: deteccion automatica por atributo Tool Name
"""

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow,QListWidget, QStackedWidget, QWidget, QHBoxLayout,)
from UI.batch_renamer_ui import BatchRenamer
from UI.organizer_ui import FileOrganizer
from UI.cleaner_ui import FileCleaner


# ---------------------------------------------------------------
# REGISTRO DE HERRAMIENTAS
# ---------------------------------------------------------------
# Para añadir una herramienta nueva:
#   1. Crea en PipelineTools/CORE/<tool>/<tool>_core.py
#   2. Crea PipelineTools/UI/<tool>_ui.py con una clase que herede de BaseTool
#   3. Añade aquí ("nombre_visible", claseUI).
#
# No hace falta tocar Launcher para nada más que esto.

TOOL_REGISTRY = [
    ("Batch Renamer", BatchRenamer),
    ("File Organizer",FileOrganizer ),
    ("Project Cleaner",FileCleaner),   
       
]


class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pipeline Tools")
        self.resize(1100, 650)

        self.menu = QListWidget()           #Panel lateral con lsita de herramientas
        self.menu.setFixedWidth(200)        

        self.stack = QStackedWidget()       #Panel principal con las herramientas

        for name, tool_class in TOOL_REGISTRY:  #registrar herramientas
            self.menu.addItem(name)
            self.stack.addWidget(tool_class())  #instancia única

        self.menu.currentRowChanged.connect(self.stack.setCurrentIndex)
        if TOOL_REGISTRY:
            self.menu.setCurrentRow(0)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(self.menu)
        layout.addWidget(self.stack, stretch=1)
        
        self.setCentralWidget(container)


def main() -> None:
    app = QApplication(sys.argv)
    window = Launcher()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()