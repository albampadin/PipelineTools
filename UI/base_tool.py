"""
Widget base compartido por todas las herramientas del launcher.

Cada herramienta (BatchRenamer, ProjectCleaner, LODGenerator, ...)
hereda de BaseTool y añade sus propios controles encima de la tabla
y el log. 
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QTableWidget, QTableWidgetItem,QPushButton,QCheckBox,QHBoxLayout
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

# Un solo sitio donde se define qué color representa cada estado.
STATUS_COLORS = {
    "ok": QColor("#d4f7d4"),
    "renamed": QColor("#d4f7d4"),
    "moved":  QColor("#d4f7d4"),
    "copied": QColor("#d4f7d4"),

    "deleted":  QColor("#c6d3a8"),

    "ignored": QColor("#ffffff"),
    "pending": QColor("#ffffff"),

    "collision": QColor("#f8d7da"),
    "failed": QColor("#f8d7da"),

    "warning": QColor("#fff3cd"),
}


class BaseTool(QWidget):
    def __init__(self, title: str = "Tool", columns = None, selectable = False):
        super().__init__()
        self.setWindowTitle(title)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.selectable = selectable


        self.table = QTableWidget()

        columns = columns or ["Item", "Status", "Info"]
        if self.selectable:
            columns = ["Select"] + columns
        
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)

        self.layout.addWidget(self.table)
        self.layout.addWidget(self.log)

#------------ common functions -----------

    def add_log(self, text: str) -> None:
        self.log.append(text)

    def add_row(self, values, status_key: str = None, checked:bool = True) -> None:
        """
        status_key es opcional y separado de los valores a propósito: el texto que ve el usuario puede
        cambiar o traducirse sin romper el color, porque el color se decide por status_key, no por el texto mostrado.
        """
        row = self.table.rowCount()
        self.table.insertRow(row)

        column_offset = 0

        if self.selectable:
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            checkbox.setCheckState(Qt.Checked if checked else Qt.Unchecked)

            self. table.setItem(row, 0, checkbox)
            column_offset = 1

        #for column, value in enumerate(values):
        #    item = QTableWidgetItem(str(value))

            color = None   
            if status_key in STATUS_COLORS:
                color = STATUS_COLORS[status_key]

            #self.table.setItem(row, column, item)
            for index,value in enumerate(values):
                item = QTableWidgetItem(str(value)) 
                if color: item.setBackground(color)
                self.table.setItem(row, index + column_offset, item)

    def clear_table(self) -> None:
        self.table.setRowCount(0)