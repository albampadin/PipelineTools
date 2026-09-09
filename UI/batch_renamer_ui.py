# UI del Batch Renamer
from PyQt5.QtWidgets import (
    QPushButton, QFileDialog, QLineEdit, QMessageBox, QHBoxLayout,
    QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QLabel, QWidget)
from PyQt5.QtCore import Qt
from UI.base_tool import BaseTool, STATUS_COLORS

from CORE.BatchRenamer.batch_renamer_core import (build_rename_plan, apply_rename_plan, RenameConfig, save_config, load_config, plan_summary, RenameStatus)


class BatchRenamer(BaseTool):
    def __init__(self):
        super().__init__("Batch Renamer", columns=["Item","Status", "Info"], selectable=True)

        self.folder = None
        self.row_checkboxes:dict[int,QCheckBox] = {}
        self.current_plan = []  # última preview calculada
        self.visible_plans = []

        # Botones principales
        self.btn_select = QPushButton("Seleccionar carpeta")
        self.btn_preview = QPushButton("Preview")
        self.btn_apply = QPushButton("Aplicar")
        self.btn_apply.setEnabled(False)  # no tiene sentido aplicar sin preview antes

        self.btn_check_all = QPushButton("Seleccionar todo")
        self.btn_uncheck_all = QPushButton("Deseleccionar todo")
        self.btn_invert = QPushButton("Invertir seleccion")

        self.btn_save_cfg = QPushButton(" Guardar configuración")
        self.btn_load_cfg = QPushButton(" Cargar configuración")

        # Cajas de texto 
        self.prefix = QLineEdit()
        self.prefix.setPlaceholderText("Prefijo")

        self.suffix = QLineEdit()
        self.suffix.setPlaceholderText("Sufijo")

        self.replace_old = QLineEdit()
        self.replace_old.setPlaceholderText("Reemplazar esto")

        self.replace_new = QLineEdit()
        self.replace_new.setPlaceholderText("Por esto")

        # organizacion visual de las cajas de texto: horizontal
        fields_row = QHBoxLayout()
        fields_row.addWidget(self.prefix)
        fields_row.addWidget(self.suffix)
        fields_row.addWidget(self.replace_old)
        fields_row.addWidget(self.replace_new)

        check_row = QHBoxLayout()
        check_row.addWidget(self.btn_check_all)
        check_row.addWidget(self.btn_uncheck_all)
        check_row.addWidget(self.btn_invert)
        

        #opciones avanzadas
        self.normalize_box = QComboBox()
        self.normalize_box.addItems(["", "minúscula", "mayúscula", "título"])

        self.autonumber_check = QCheckBox("Auto-numbering")
        self.autonumber_start = QLineEdit()
        self.autonumber_start.setPlaceholderText("Inicio (1)")
        self.autonumber_padding = QLineEdit()
        self.autonumber_padding.setPlaceholderText("Padding (3)")

        advanced_row = QHBoxLayout()
        advanced_row.addWidget(QLabel("Normalizar:"))
        advanced_row.addWidget(self.normalize_box)
        advanced_row.addWidget(self.autonumber_check)
        advanced_row.addWidget(self.autonumber_start)
        advanced_row.addWidget(self.autonumber_padding)


        #Tabla: múltiples reemplazos
        self.multi_table = QTableWidget(0,2)
        self.multi_table.setHorizontalHeaderLabels(["Buscar","Reemplazar"])
        self.btn_add_multi = QPushButton("Añadir reemplazo")


        multi_layout = QVBoxLayout()
        multi_layout.addWidget(QLabel("Múltiples reemplazos: "))
        multi_layout.addWidget(self.multi_table)
        multi_layout.addWidget(self.btn_add_multi)

        multi_widget = QWidget()
        multi_widget.setLayout(multi_layout)


        self.check_recursive = QCheckBox("Recursivo (incluir subcarpetas)")
        self.check_folders = QCheckBox("Renombrar Carpetas")

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.check_recursive)
        folder_layout.addWidget(self.check_folders)

        self.filter_box =QComboBox()
        self.filter_box.addItems(["Todos", "Renombrados", "Pendientes", "Coincidencias", "Ignorados"])

        filter_layout=QHBoxLayout()
        filter_layout.addWidget(self.filter_box)
    

        # organizacion visual de los botones: horizontal
        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self.btn_select)
        buttons_row.addWidget(self.btn_preview)
        buttons_row.addWidget(self.btn_apply)
        buttons_row.addWidget(self.btn_save_cfg)
        buttons_row.addWidget(self.btn_load_cfg)

        #Insetar en el layout de forma ordenada
        self.layout.insertLayout(0, buttons_row)
        self.layout.insertLayout(1, fields_row)
        self.layout.insertLayout(2, advanced_row)
        self.layout.addWidget(multi_widget)
        self.layout.insertLayout(3, folder_layout)
        self.layout.insertLayout(4, check_row)
        self.layout.insertLayout(5, filter_layout)

        #conectar eventos
        self.btn_select.clicked.connect(self.select_folder)
        self.btn_preview.clicked.connect(self.preview)
        self.btn_apply.clicked.connect(self.apply_changes)
        self.btn_add_multi.clicked.connect(self.add_multi_row)
        self.btn_load_cfg.clicked.connect(self.load_config_ui)
        self.btn_save_cfg.clicked.connect(self.save_config_ui)
        self.btn_check_all.clicked.connect(self.check_all)
        self.btn_uncheck_all.clicked.connect(self.uncheck_all)
        self.btn_invert.clicked.connect(self.invert_selection)
        self.filter_box.currentIndexChanged.connect(self.apply_filter)

        # Mecaniso de seguridad: si el usuario edita cualquier texto la vita previa se limpi. Evita aplicar reglas antiguas si no coinciden con lo actual.    
        for field in (self.prefix, self.suffix, self.replace_old, self.replace_new, self.autonumber_start, self.autonumber_padding):
            field.textChanged.connect(self._invalidate_preview)

        self.normalize_box.currentIndexChanged.connect(self._invalidate_preview)
        self.autonumber_check.stateChanged.connect(self._invalidate_preview)
        self.check_folders.stateChanged.connect(self._invalidate_preview)
        self.check_recursive.stateChanged.connect(self._invalidate_preview)
        self.multi_table.itemChanged.connect(self._invalidate_preview)

        self._set_selection_buttons_enabled(False)

    #--------
    def collect_config(self)->RenameConfig:       
        multi_repl = {}
        for row in range(self.multi_table.rowCount()):
            old_item = self.multi_table.item(row, 0)
            new_item = self.multi_table.item(row, 1)
            if old_item and new_item:
                old = old_item.text().strip()
                new = new_item.text().strip()
                if old: 
                    multi_repl[old] = new

        normalize = self.normalize_box.currentText() or None

        start = int(self.autonumber_start.text() if self.autonumber_start.text().isdigit() else 1)
        padding = int(self.autonumber_padding.text() if self.autonumber_padding.text().isdigit() else 3)

        recursive = self.check_recursive.isChecked()
        rename_folders= self.check_folders.isChecked()

        return RenameConfig(
            prefix=self.prefix.text(),
            suffix=self.suffix.text(),
            replace_old=self.replace_old.text(),
            replace_new= self.replace_new.text(),
            multi_replacements=multi_repl,
            normalize=normalize,
            autonumber=self.autonumber_check.isChecked(),
            autonumber_start=start,
            autonumber_padding=padding,
            rename_folders= rename_folders,
            recursive = recursive
        )
        
    def apply_config_to_ui(self, cfg:RenameConfig):
        self.prefix.setText(cfg.prefix)
        self.suffix.setText(cfg.suffix)
        self.replace_old.setText(cfg.replace_old)
        self.replace_new.setText(cfg.replace_new)

        idx = self.normalize_box.findText(cfg.normalize) if cfg.normalize else 0
        self.normalize_box.setCurrentIndex(idx)

        self.autonumber_check.setChecked(cfg.autonumber)
        self.autonumber_start.setText(str(cfg.autonumber_start))
        self.autonumber_padding.setText(str(cfg.autonumber_padding))

        self.check_folders.setChecked(cfg.rename_folders)
        self.check_recursive.setChecked(cfg.recursive)

        self.multi_table.setRowCount(0)
        for old,new in cfg.multi_replacements.items():
            row = self.multi_table.rowCount()
            self.multi_table.insertRow(row)
            self.multi_table.setItem(row,0,QTableWidgetItem(old))
            self.multi_table.setItem(row,1,QTableWidgetItem(new))

    def save_config_ui(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar configuración", "", "JSON (*.json)")
        if not path: return
        cfg = self.collect_config()
        save_config(cfg,path)
        self.add_log(f"Configuracion guardada en: {path}")

    def load_config_ui(self):
        path, _ = QFileDialog.getOpenFileName(self, "Cargar configuración", "", "JSON (*.json)")
        if not path: return
        cfg = load_config(path)
        self.apply_config_to_ui(cfg)
        self._invalidate_preview()
        self.add_log(f"Configuración cargada desde: {path}")

    def add_multi_row(self):
        row = self.multi_table.rowCount()
        self.multi_table.insertRow(row)
        self.multi_table.setItem(row, 0, QTableWidgetItem(""))
        self.multi_table.setItem(row, 1, QTableWidgetItem(""))
        self._invalidate_preview()


    def _invalidate_preview(self) -> None:
        self.current_plan = []
        self.visible_plans = []
        self.btn_apply.setEnabled(False)
        self._set_selection_buttons_enabled(False)
        self.clear_table()

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            self.folder = folder
            self.add_log(f"Carpeta seleccionada: {folder}")
            self._invalidate_preview()
            self.clear_table()

    def _set_selection_buttons_enabled(self, enabled: bool):
        self.btn_check_all.setEnabled(enabled)
        self.btn_uncheck_all.setEnabled(enabled)
        self.btn_invert.setEnabled(enabled)

    def _show_plans(self, plans):
        self.clear_table()
        self.visible_plans = list(plans)

        for plan in self.visible_plans:
            status_text = ""
            status_key = None
            info = ""

            if plan.status == RenameStatus.COLLISION:
                status_text = "Coincidencia"
                status_key = "collision"
                info = plan.error or plan.new_name
            elif plan.status == RenameStatus.RENAMED:
                status_text = "Renombrado"
                status_key = "renamed"
                info = plan.new_name
            elif plan.status == RenameStatus.FAILED:
                status_text = "Fallo"
                status_key = "failed"
                info = (plan.error or "")
            elif plan.status == RenameStatus.IGNORED:
                status_text = "Ignorado"
                status_key = "ignored"
                info = (plan.error or plan.new_name)
            else:
                status_text = "Preview"
                status_key = "pending"
                info = plan.new_name

            self.add_row([plan.original_name, status_text, info], status_key=status_key,checked=(plan.status == RenameStatus.PENDING))


    def _get_selected_plans(self):
        selected_plans = []
        for row,plan in enumerate(self.visible_plans):
            item = self.table.item(row, 0)
            if not item: 
                continue
            checked = (item.checkState() == Qt.Checked)
            if (checked and plan.status == RenameStatus.PENDING):
                selected_plans.append(plan)

        return selected_plans

    def check_all(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row,0)
            if item:
                item.setCheckState(Qt.Checked)

    def uncheck_all(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row,0)
            if item:
                item.setCheckState(Qt.Unchecked)
                

    def invert_selection(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row,0)
            if not item: 
                continue
            if item.checkState()== Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)


    def apply_filter(self):
        if not self.current_plan:
            self.clear_table()
            self.visible_plans = []
            self._set_selection_buttons_enabled(False)
            return
        
        mode = self.filter_box.currentText()
        if mode == "Todos":
            filtered_plans = self.current_plan
        elif mode == "Renombrados":
            filtered_plans= [plan for plan in self.current_plan if plan.status == RenameStatus.RENAMED]
        elif mode == "Pendientes":
            filtered_plans = [plan for plan in self.current_plan if plan.status == RenameStatus.PENDING]
        elif mode == "Coincidencias":
            filtered_plans = [plan for plan in self.current_plan if plan.status == RenameStatus.COLLISION]
        elif mode == "Ignorados":
            filtered_plans = [plan for plan in self.current_plan if plan.status == RenameStatus.IGNORED]
        else:
            filtered_plans = self.current_plan

        self._show_plans(filtered_plans)
        self._set_selection_buttons_enabled(bool(self.visible_plans))
        self.btn_apply.setEnabled(any(plan.status == RenameStatus.PENDING for plan in self.current_plan))
    

# --------------
    def preview(self) -> None:
        if not self.folder:
            self.add_log("No hay carpeta seleccionada.")
            return

        cfg = self.collect_config()
        self.current_plan = build_rename_plan(self.folder, cfg)

        self.filter_box.blockSignals(True)
        self.filter_box.setCurrentIndex(0)
        self.filter_box.blockSignals(False)

        self._show_plans(self.current_plan)
        collisions= sum(1 for plan in self.current_plan if plan.status == RenameStatus.COLLISION)

        if collisions:
            self.add_log(f"{collisions} coincidencia(s) encontrada(s): no se renombrarán al aplicar.")
        else:
            self.add_log("Preview generada sin coincidencias detectadas.")

        has_pending = any(plan.status == RenameStatus.PENDING for plan in self.current_plan)
        self.btn_apply.setEnabled(has_pending)

        self._set_selection_buttons_enabled(bool(self.visible_plans))

        

    def apply_changes(self) -> None:
        if not self.current_plan:
            self.add_log("Genera una preview antes de aplicar.")
            return

        selected_plans =self._get_selected_plans()
        if not selected_plans:
            self.add_log( "no hay rchivos seleccionados para renombrar")
            return
        collisions = [plan for plan in self.current_plan if plan.status == RenameStatus.COLLISION]
        if collisions:
            answer = QMessageBox.question(
                self,
                "Colisiones detectadas",
                f"{len(collisions)} archivo(s) tienen coincidencias y se saltarán.\n"
                f"¿Continuar con los restantes?",
            )
            if answer != QMessageBox.Yes:
                return

        apply_rename_plan(selected_plans)

        for plan in self.current_plan:
            if plan.status == RenameStatus.PENDING:
                if plan not in selected_plans:
                    plan.status = RenameStatus.IGNORED
    

        self.filter_box.blockSignals(True)
        self.filter_box.setCurrentIndex(0)
        self.filter_box.blockSignals(False)

        self._show_plans(self.current_plan)
        
        summary = plan_summary(self.current_plan)

    
        #Mostrar resultados
        self.add_log("Renombrado realizado.")
        self.btn_apply.setEnabled(any(plan.status == RenameStatus.PENDING for plan in self.current_plan))        
        self._set_selection_buttons_enabled(bool(self.visible_plans))

        self.add_log(
            f"--------------------------\n"
            f"Resumen:\n"
            f"  Total: {summary['total']}\n"
            f"  Renombrados: {summary['renamed']}\n"
            f"  Ignorados: {summary['ignored']}\n"
            f"  Colisiones: {summary['collision']}\n"
            f"  Fallos: {summary['failed']}\n"
            f"--------------------------\n"
        )