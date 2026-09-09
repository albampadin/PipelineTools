from UI.base_tool import BaseTool

from PyQt5.QtWidgets import (QPushButton, QFileDialog, QMessageBox, QHBoxLayout, QCheckBox, QLabel, QSpinBox, QComboBox)

from PyQt5.QtCore import Qt

from CORE.Cleaner.cleaner_core import (CleanerConfig, CleanerStatus,CleanerPlan, CleanerItemType, apply_cleaner_plan, build_cleaner_plan)

class FileCleaner(BaseTool):
    def __init__(self):
        super().__init__("File Cleaner", columns=["Item","Tipo", "Info"], selectable=True)
    
        self.folder = None
        self.current_plan = []  # última preview calculada
        self.current_config = None
        self.visible_plans = []


        # Botones principales
        self.btn_select = QPushButton("Seleccionar carpeta")
        self.btn_preview = QPushButton("Preview")
        self.btn_apply = QPushButton("Aplicar / Borrar")

        self.btn_apply.setEnabled(False)  # no tiene sentido aplicar sin preview antes

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self.btn_select)
        buttons_row.addWidget(self.btn_preview)
        buttons_row.addWidget(self.btn_apply)


        self.btn_check_all = QPushButton("Seleccionar todo")
        self.btn_uncheck_all = QPushButton("Deseleccionar todo")
        self.btn_invert = QPushButton("Invertir seleccion")

        check_row = QHBoxLayout()
        check_row.addWidget(self.btn_check_all)
        check_row.addWidget(self.btn_uncheck_all)
        check_row.addWidget(self.btn_invert)


        self.check_recursive = QCheckBox("Recursivo (incluir subcarpetas)")

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.check_recursive)

        self.check_empty_folders = QCheckBox("Carpetas vacías")
        self.check_duplicates = QCheckBox("Duplicados")
        self.check_large_files = QCheckBox("Archivos grandes")
        self.check_old_files = QCheckBox("Archivos viejos")
        self.check_tmp_files = QCheckBox("archivos temporales")

        self.check_empty_folders.setChecked(True)
        self.check_duplicates.setChecked(True)

        cleaner_row = QHBoxLayout()
        cleaner_row.addWidget(self.check_empty_folders)
        cleaner_row.addWidget(self.check_duplicates)
        cleaner_row.addWidget(self.check_large_files)
        cleaner_row.addWidget(self.check_old_files)
        cleaner_row.addWidget(self.check_tmp_files)

        self.large_file_size = QSpinBox()
        self.large_file_size.setRange(1,999999)
        self.large_file_size.setValue(500)
        self.large_file_size.setSuffix(" MB")

        large_row = QHBoxLayout()
        large_row.addWidget(QLabel("Archivos grandes desde: "))
        large_row.addWidget(self.large_file_size)

        self.old_file_days = QSpinBox()
        self.old_file_days.setRange(1,999999)
        self.old_file_days.setValue(365)
        self.old_file_days.setSuffix(" días")

        old_row = QHBoxLayout()
        old_row.addWidget(QLabel("Archivos no modficados desde hace: "))
        old_row.addWidget(self.old_file_days)

        self.filter_box = QComboBox()
        self.filter_box.addItem("Todos", None)
        self.filter_box.addItem("Carpetas Vacías", CleanerItemType.EMPTY_FOLDER)
        self.filter_box.addItem("Duplicados", CleanerItemType.DUPLICATE)
        self.filter_box.addItem("Archivos grandes",CleanerItemType.LARGE_FILE)
        self.filter_box.addItem("Archivos antiguos", CleanerItemType.OLD_FILE)
        self.filter_box.addItem("Archivos temporales", CleanerItemType.TMP)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtrar resultados:"))
        filter_row.addWidget(self.filter_box)


        #Insertar en el layout de forma ordenada
        self.layout.insertLayout(0, buttons_row)
        self.layout.insertLayout(1,check_row)
        self.layout.insertLayout(2, folder_layout)
        self.layout.insertLayout(3, cleaner_row)
        self.layout.insertLayout(4, large_row)
        self.layout.insertLayout(5, old_row)
        self.layout.insertLayout(6, filter_row)


        self.btn_select.clicked.connect(self.select_folder)
        self.btn_preview.clicked.connect(self.preview)
        self.btn_apply.clicked.connect(self.apply_changes)

        self.btn_check_all.clicked.connect(self.check_all)
        self.btn_uncheck_all.clicked.connect(self.uncheck_all)
        self.btn_invert.clicked.connect(self.invert_selection)


        self.check_recursive.stateChanged.connect(self._invalidate_preview)
        self.check_tmp_files.stateChanged.connect(self._invalidate_preview)
        self.check_old_files.stateChanged.connect(self._invalidate_preview)
        self.check_large_files.stateChanged.connect(self._invalidate_preview)
        self.check_duplicates.stateChanged.connect(self._invalidate_preview)
        self.check_empty_folders.stateChanged.connect(self._invalidate_preview)
        self.large_file_size.valueChanged.connect(self._invalidate_preview)
        self.old_file_days.valueChanged.connect(self._invalidate_preview)
        self.filter_box.currentIndexChanged.connect(self._filter_plans)
        self._set_selection_buttons_enabled(False)       

    #--------

    def check_all(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                continue
            item.setCheckState(Qt.Checked)


    def uncheck_all(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                continue
            else:
                item.setCheckState(Qt.Unchecked)

    def invert_selection(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                continue
            if item.checkState() == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)

    
    def _invalidate_preview(self) -> None:
        self.current_plan = []
        self.current_config = None
        self.btn_apply.setEnabled(False)
        self.clear_table()
        self._set_selection_buttons_enabled(False)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            self.folder = folder
            self.add_log(f"Carpeta seleccionada: {folder}")
            self._invalidate_preview()
        else:
             return

    def _set_selection_buttons_enabled(self, enabled: bool):
        self.btn_check_all.setEnabled(enabled)
        self.btn_uncheck_all.setEnabled(enabled)
        self.btn_invert.setEnabled(enabled)


    def _build_config(self)-> CleanerConfig:
        config = CleanerConfig()

        config.recursive = self.check_recursive.isChecked()
        config.check_empty_folder = self.check_empty_folders.isChecked()
        config.check_duplicates = self.check_duplicates.isChecked()
        config.check_large_files = self.check_large_files.isChecked()
        config.check_old_files = self.check_old_files.isChecked()
        config.check_tmp_files = self.check_tmp_files.isChecked()

        config.old_file_days = self.old_file_days.value()
        config.large_file_size_mb = self.large_file_size.value()

        return config
    
        
    def _show_plans(self, plans): 
        self.clear_table()
        self.visible_plans = list(plans)

        type_names = {
            CleanerItemType.EMPTY_FOLDER: "Carpeta vacía",
            CleanerItemType.DUPLICATE: "Duplicado",
            CleanerItemType.LARGE_FILE : "Archivo grande",
            CleanerItemType.OLD_FILE: "Archivo antiguo",
            CleanerItemType.TMP: "Archivo temporal",

        }
        status_names = {
        CleanerStatus.PENDING: "Pendiente",
        CleanerStatus.DELETED: "Eliminado", 
        CleanerStatus.FAILED: "Error",
        CleanerStatus.IGNORED: "Ignorado", 
        }

        for plan in plans:
            type_text = type_names.get(plan.kind, plan.kind.value)
            status_text = status_names.get(plan.status, plan.status.value)

            if plan.kind == CleanerItemType.DUPLICATE: 
                type_text = f"{type_text} [{plan.group_id}]"

            info = plan.error if plan.error else str(plan.info)

            self.add_row([plan.path.name, f"{type_text} - {status_text}", info], status_key=plan.status.value)


    def _update_current_plan(self, updated_plans):
        updated_by_path = {plan.path: plan for plan in updated_plans}
        for index,plan in enumerate(self.current_plan):
                if plan.path in updated_by_path:
                    self.current_plan[index] = updated_by_path[plan.path]


    def _get_selected_plans(self):
        selected_plans = []

        for row, plan in enumerate(self.visible_plans):
            item = self.table.item(row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                selected_plans.append(plan)

        return selected_plans

    def _filter_plans(self):
        if not self.current_plan:
            return

        selected_kind = self.filter_box.currentData()
        if selected_kind is None:
            filtered_plans = self.current_plan
        else:
            filtered_plans = [plan for plan in self.current_plan if plan.kind == selected_kind]

        self._show_plans(filtered_plans)
        self._set_selection_buttons_enabled(bool(filtered_plans))
        self.btn_apply.setEnabled(any(plan.status == CleanerStatus.PENDING for plan in self.current_plan))

    
        # ----------------------------
        
    def preview(self) -> None:
        if not self.folder:
            self.add_log("No hay carpeta seleccionada.")
            return
        try:
            self.current_config = self._build_config()
            plans = build_cleaner_plan(self.folder, self.current_config)

        except Exception as exc:
            self.add_log(f"Error creando preview: {exc}")
            return

        self.current_plan = plans
        self._show_plans(plans)
        self.btn_apply.setEnabled(any(plan.status == CleanerStatus.PENDING for plan in plans))
        self._set_selection_buttons_enabled(bool(plans))

        self.add_log(f"Preview generada de: {len(plans)} elemento(s) encontrado(s)")


    def apply_changes(self) -> None:
        if not self.current_plan: 
            return 

        selected_plans = self._get_selected_plans()

        if not selected_plans:
            QMessageBox.information(self,"File Cleaner", "no hay elementos seleccionados")
            return
        answer = QMessageBox.question(self,"Confirmar eliminación", (f"Eliminar {len(selected_plans)} elementos(s)\n\n Esta operación no se puede deshacer."), QMessageBox.Yes | QMessageBox.No, )
        if answer != QMessageBox.Yes:
            return
        try:
            #config = self._build_config()
            updated_plans = apply_cleaner_plan(selected_plans)
        except Exception as exc: 
            QMessageBox.critical( self, "Error", str(exc), )
            self.add_log( f"Error aplicando limpieza: {exc}" )
            return 
        
        # Actualizamos los planes originales 
        self._update_current_plan(updated_plans)
        self.filter_box.blockSignals(True)
        self.filter_box.setCurrentIndex(0)
        self.filter_box.blockSignals(False)
        self._show_plans(self.current_plan)

        self.btn_apply.setEnabled( any( plan.status == CleanerStatus.PENDING for plan in self.current_plan ) )
        self.add_log( f"Limpieza completada: " f"{len(updated_plans)} elemento(s)." )