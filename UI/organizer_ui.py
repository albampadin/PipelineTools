from UI.base_tool import BaseTool

from PyQt5.QtWidgets import (
    QPushButton, QFileDialog, QLineEdit, QMessageBox, QHBoxLayout,
    QComboBox, QCheckBox, QLabel )

from PyQt5.QtCore import Qt

from CORE.Organizer.organizer_core import (OrganizerConfig, OrganizerMode, OrganizeStatus,OrganizerOperation, OrganizerPlan,apply_organizer_plan,build_organizer_plan)

class FileOrganizer(BaseTool):
    def __init__(self):
        super().__init__("File Organizer", columns=["Item","Status", "Info"], selectable=True)
    
        self.folder = None
        self.row_checkboxes:dict[int,QCheckBox] = {}

        self.current_plan = []  # última preview calculada
        self.visible_plans = []
        self.current_config = None


        # Botones principales
        self.btn_select = QPushButton("Seleccionar carpeta")
        self.btn_preview = QPushButton("Preview")
        self.btn_apply = QPushButton("Aplicar")
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

        #tipo de operacion
        self.operation_box = QComboBox()
        self.operation_box.addItem("Mover", OrganizerOperation.MOVE)
        self.operation_box.addItem("Copiar", OrganizerOperation.COPY)

        operation_layout = QHBoxLayout()
        operation_layout.addWidget(QLabel("Operación:"))
        operation_layout.addWidget(self.operation_box)
        
        #Modo de organización
        self.mode_box = QComboBox()
        self.mode_box.addItem("Extension", OrganizerMode.EXTENSION)
        self.mode_box.addItem("Fecha", OrganizerMode.FECHA)
        self.mode_box.addItem("Nombre", OrganizerMode.NOMBRE)

        mode_layout=QHBoxLayout()
        mode_layout.addWidget(QLabel("Agrupar por:"))
        mode_layout.addWidget(self.mode_box)

        #autonumbering
        self.autonumber_check = QCheckBox("Auto-numbering")
        self.autonumber_start = QLineEdit()
        self.autonumber_start.setPlaceholderText("Inicio (1)")
        self.autonumber_padding = QLineEdit()
        self.autonumber_padding.setPlaceholderText("Padding (3)")

        autonumber_row = QHBoxLayout()
        autonumber_row.addWidget(self.autonumber_check)
        autonumber_row.addWidget(self.autonumber_start)
        autonumber_row.addWidget(self.autonumber_padding)

        #recursivo
        self.check_recursive = QCheckBox("Recursivo (incluir subcarpetas)")

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.check_recursive)

        #filtro
        self.filter_box = QComboBox() 
        self.filter_box.addItem("Todos", None)
        self.filter_box.addItem("PDF", "PDF")
        self.filter_box.addItem("Images", "Images")
        self.filter_box.addItem("Videos", "Videos")
        self.filter_box.addItem("Music", "Music")
        self.filter_box.addItem("Documents", "Documents")
        self.filter_box.addItem("Spreadsheets", "Spreadsheets")
        self.filter_box.addItem("Archives", "Archives")
        self.filter_box.addItem("Others", "Others")

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar resultados:"))
        filter_layout.addWidget(self.filter_box)


        #Insertar en el layout de forma ordenada
        self.layout.insertLayout(0, buttons_row)
        self.layout.insertLayout(1,check_row)
        self.layout.insertLayout(2, autonumber_row)
        self.layout.insertLayout(3, folder_layout)
        self.layout.insertLayout(4, mode_layout)
        self.layout.insertLayout(5, operation_layout)
        self.layout.insertLayout(6, filter_layout)

        self.btn_select.clicked.connect(self.select_folder)
        self.btn_preview.clicked.connect(self.preview)
        self.btn_apply.clicked.connect(self.apply_changes)

        self.btn_check_all.clicked.connect(self.check_all)
        self.btn_uncheck_all.clicked.connect(self.uncheck_all)
        self.btn_invert.clicked.connect(self.invert_selection)

        self.mode_box.currentIndexChanged.connect(self._invalidate_preview)
        self.operation_box.currentIndexChanged.connect(self._invalidate_preview)
        for field in (self.autonumber_padding, self.autonumber_start):
               field.textChanged.connect(self._invalidate_preview)
        self.autonumber_check.stateChanged.connect(self._invalidate_preview)
        self.check_recursive.stateChanged.connect(self._invalidate_preview)
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
        self.visible_plans = []
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


    def _build_config(self)-> OrganizerConfig:
        config = OrganizerConfig()

        config.operation = self.operation_box.currentData()
        config.mode = self.mode_box.currentData()
        config.recursive = self.check_recursive.isChecked()
        config.autonumber = self.autonumber_check.isChecked()
        config.autonumber_start = int(self.autonumber_start.text() if self.autonumber_start.text().isdigit() else 1)
        config.autonumber_padding = int(self.autonumber_padding.text() if self.autonumber_padding.text().isdigit() else 3)

        return config

    
    def _show_plans(self, plans): 
         self.clear_table()
         self.visible_plans = list(plans)

         status_names = {
                OrganizeStatus.PENDING: "Pendiente",
                OrganizeStatus.COLLISION: "Coincidencia",
                OrganizeStatus.MOVED : "Movido",
                OrganizeStatus.COPIED: "Copiado",
                OrganizeStatus.FAILED: "Error",
                OrganizeStatus.IGNORED: "Ignorado"
         }
         for plan in self.visible_plans:
                status_text = status_names.get(plan.status, plan.status.value)
                if plan.error:
                    info = plan.error
                else: 
                    info =  str(plan.destination_path)

                self.add_row([plan.original_path.name, status_text, info], status_key=plan.status.value)


    def _update_current_plan(self, updated_plans):
        updated_by_path = {plan.original_path:plan for plan in updated_plans}
        for index,plan in enumerate(self.current_plan):
             if plan.original_path in updated_by_path:
                  self.current_plan[index] = updated_by_path[plan.original_path]


    def _get_selected_plans(self):
        selected_plans = []

        for row, plan in enumerate(self.visible_plans):
            item = self.table.item(row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                selected_plans.append(plan)
        return selected_plans

    def _filter_plans(self):
        if not self.current_plan:
            self.clear_table()
            self.visible_plans = []
            self._set_selection_buttons_enabled(False)
            return
        
        selected_category = self.filter_box.currentData()

        if selected_category is None:
            filtered_plans = self.current_plan
        else: 
            filtered_plans = [plan for plan in self.current_plan if plan.category == selected_category]

        self._show_plans(filtered_plans)
        self._set_selection_buttons_enabled(bool(filtered_plans))
        self.btn_apply.setEnabled(any(plan.status == OrganizeStatus.PENDING for plan in self.current_plan))


# ----------------------------

    def preview(self) -> None:
        if not self.folder:
            self.add_log("No hay carpeta seleccionada.")
            return
        try:
            self.current_config = self._build_config()
            plans = build_organizer_plan(self.folder, self.current_config)

        except Exception as exc:
            self.add_log(f"Error creando preview: {exc}")
            return

        self.current_plan = plans
        self._show_plans(plans)
        self.filter_box.blockSignals(True)
        self.filter_box.setCurrentIndex(0)
        self.filter_box.blockSignals(False)
        self._show_plans(self.current_plan)


        self.btn_apply.setEnabled(any(plan.status == OrganizeStatus.PENDING for plan in plans))
        self._set_selection_buttons_enabled(bool(self.visible_plans))

        
        self.add_log(f"Preview generada de {len(plans)} archivo(s)")


    def apply_changes(self) -> None:
        if not self.current_plan: 
            return 
        selected_plans = self._get_selected_plans()
        if not selected_plans:
            QMessageBox.information( self, "File Organizer", "No hay elementos seleccionados.", )
            return
        answer = QMessageBox.question( self, "Confirmar", f"¿Aplicar la operación a " f"{len(selected_plans)} elementos?", QMessageBox.Yes | QMessageBox.No, )
        if answer != QMessageBox.Yes:
            return
        try:
            config = self._build_config()
            updated_plans = apply_organizer_plan(selected_plans, operation=self.current_config.operation, keep_metadata=self.current_config.keep_metadata)
        except Exception as exc: 
            QMessageBox.critical( self, "Error", str(exc), )
            self.add_log( f"Error aplicando plan: {exc}" )
            return 
        # Actualizamos los planes originales 
        self.filter_box.blockSignals(True)
        self.filter_box.setCurrentIndex(0)
        self.filter_box.blockSignals(False)
        self._show_plans(self.current_plan)

        self.btn_apply.setEnabled( any( plan.status == OrganizeStatus.PENDING for plan in self.current_plan))
        self._set_selection_buttons_enabled(bool(self.visible_plans))
        self.add_log( f"Operación completada: " f"{len(updated_plans)} elementos." )