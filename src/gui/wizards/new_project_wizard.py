import sys
from typing import Optional
from pathlib import Path
from datetime import datetime
import json
from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QRadioButton, QMessageBox, QPushButton,
    QDialog, QFileDialog, QInputDialog, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QApplication,
    QLineEdit, QDoubleSpinBox, QFormLayout, QDialogButtonBox
)

# Add the src directory to Python path
src_path = Path(__file__).parent.parent.parent  # goes up to src/
sys.path.insert(0, str(src_path))

from core.templates.loader import TemplateLoader
from core.templates.models import MachineTemplate, Tool

class NewProjectWizard(QWizard):
    def __init__(self, template_loader: TemplateLoader, parent=None):
            super().__init__(parent)
            self.template_loader = template_loader
            self.selected_template: MachineTemplate | None = None
            self.selected_units = "Imperial"
            self.changes_made = False

            self.setWindowTitle("New Project - MacroForge")
            self.setWizardStyle(QWizard.ModernStyle)

            self.addPage(MachineSelectionPage(self))
            self.addPage(UnitsPage(self))
            self.addPage(ReviewPage(self))

    def accept(self):
        """Called when user clicks 'Create Project'"""
        if not self.selected_template:
            QMessageBox.warning(self, "Missing Selection", 
                              "Please select a machine before creating the project.")
            self.back()   # Go back to machine selection page
            return

        project_path = self._get_project_path_from_user()
        if not project_path:
            return

        success = self._create_project_folder(project_path)
        if success:
            # Snapshot the template before closing (fixes handoff bug)
            selected_template = self.selected_template
            
            # Launch main window with the selected template
            try:
                from gui.main_window import MainWindow
                self.main_win = MainWindow(project_path, selected_template)
                self.main_win.show()
                self.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open main window: {e}")
                return
        else:
            QMessageBox.critical(self, "Error", "Failed to create project folder.")

    def _get_project_path_from_user(self) -> Optional[Path]:
        """Ask user for project location and name."""
        # Choose base directory
        base_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Folder for New Project",
            str(Path.home() / "Documents"),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if not base_dir:
            return None

        base_path = Path(base_dir)

        # Ask for project name
        name, ok = QInputDialog.getText(
            self,
            "Project Name",
            "Enter a name for the new project:",
            QLineEdit.Normal,
            f"{self.selected_template.machine_name.replace(' ', '_')}_project"
        )

        if not ok or not name.strip():
            return None

        project_name = name.strip()
        project_path = base_path / project_name

        # Check if folder already exists
        if project_path.exists():
            reply = QMessageBox.question(
                self,
                "Folder Exists",
                f"The folder '{project_name}' already exists.\n\nDo you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return None

        return project_path

    def _create_project_folder(self, project_path: Path) -> bool:
        """Create the project folder and initial files."""
        try:
            project_path.mkdir(parents=True, exist_ok=True)

            # project_settings.json
            settings = {
                "project_name": project_path.name,
                "machine_name": self.selected_template.machine_name,
                "units": self.selected_units,
                "work_offsets": {
                    "G54": {"X": 0.0, "Y": 0.0, "Z": 0.0}
                },
                "variable_map": [],
                "created_date": datetime.now().isoformat()
            }

            with open(project_path / "project_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)

            # main.nc with header comment
            with open(project_path / "main.nc", "w", encoding="utf-8") as f:
                f.write(f"({self.selected_template.machine_name} - New Project)\n")
                f.write(f"(Created: {datetime.now().strftime('%Y-%m-%d %H:%M')})\n")
                f.write(f"(Units: {self.selected_units})\n\n")

            return True

        except Exception as e:
            QMessageBox.critical(self, "Project Creation Error", 
                f"Failed to create project folder: {e}")
            return False
        
class MachineSelectionPage(QWizardPage):
    def __init__(self, wizard: NewProjectWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Select Machine")
        self.setSubTitle("Choose the machine this project will be based on")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Machine dropdown
        self.machine_combo = QComboBox()
        self.machine_combo.setMinimumWidth(350)
        layout.addWidget(QLabel("Machine:"))
        layout.addWidget(self.machine_combo)

        # Info label
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("padding: 8px; background-color: #2d2d2d; border-radius: 4px;")
        layout.addWidget(self.info_label)

        # Populate dropdown
        self.populate_machine_combo()

        # Connect signal
        self.machine_combo.currentIndexChanged.connect(self.on_machine_selected)

        # Register field for wizard validation - this makes "Next" button enable
        self.registerField("machine_name*", self.machine_combo, "currentText")

    def populate_machine_combo(self):
            """Populate dropdown with clear built-in and custom sections"""
            self.machine_combo.clear()

            # === Built-in Templates ===
            self.machine_combo.addItem("── Built-in Templates ──", None)   # Header (non-selectable)
            
            for name in self.wizard.template_loader.get_builtin_names():
                template = self.wizard.template_loader.get_template_by_name(name)
                if template:
                    self.machine_combo.addItem(name, template)

            # === Custom Templates ===
            custom_names = self.wizard.template_loader.get_custom_names()
            if custom_names:
                self.machine_combo.addItem("── Custom Templates ──", None)  # Header
                for name in custom_names:
                    template = self.wizard.template_loader.get_template_by_name(name)
                    if template:
                        self.machine_combo.addItem(name, template)
            else:
                # Optional: show a disabled "No custom templates yet" line
                self.machine_combo.addItem("(No custom templates yet)", None)

    def on_machine_selected(self, index: int):
        data = self.machine_combo.itemData(index)
        
        if isinstance(data, MachineTemplate):
            self.wizard.selected_template = data
            
            info = f"<b>{data.machine_name}</b><br>{data.control_type}<br>"
            info += f"Max Tools: {data.max_tools} | Spindles: {data.spindles}"
            
            if data.lathe_options:
                lo = data.lathe_options
                if lo.has_y_axis:
                    info += "<br>• Y-axis: Yes"
                if lo.has_subspindle:
                    info += "<br>• Sub-spindle: Yes"
                if lo.has_tailstock:
                    info += "<br>• Tailstock: Yes"
            
            self.info_label.setText(info)
            self.completeChanged.emit()
        else:
            self.wizard.selected_template = None
            self.info_label.setText("")
            self.completeChanged.emit()

    def isComplete(self) -> bool:
        """Tell the wizard this page is complete when a machine is selected"""
        return self.wizard.selected_template is not None

class UnitsPage(QWizardPage):
    def __init__(self, wizard: NewProjectWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Units")
        self.setSubTitle("Select measurement units for this project")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Radio buttons
        self.imperial_radio = QRadioButton("Imperial (inches)")
        self.metric_radio = QRadioButton("Metric (mm)")
        
        self.imperial_radio.setChecked(True)   # Default = Imperial

        layout.addSpacing(20)
        layout.addWidget(self.imperial_radio)
        layout.addWidget(self.metric_radio)
        layout.addSpacing(30)

        # Information note
        note_label = QLabel(
            "All numeric values (positions, feeds, tool dimensions, etc.) will be displayed with\n"
            "4 decimal places for Imperial or 3 decimal places for Metric."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        layout.addWidget(note_label)

        # Connect signals
        self.imperial_radio.toggled.connect(self.update_units)
        self.metric_radio.toggled.connect(self.update_units)

    def update_units(self):
        """Update the wizard's selected units when radio button changes"""
        if self.imperial_radio.isChecked():
            self.wizard.selected_units = "Imperial"
        else:
            self.wizard.selected_units = "Metric"

    def validatePage(self) -> bool:
        """Always allow moving to next page"""
        return True

class ReviewPage(QWizardPage):

    def __init__(self, wizard: NewProjectWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Review Machine Settings")
        self.setSubTitle("Check settings before creating the project")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Summary
        self.summary_text = QLabel()
        self.summary_text.setWordWrap(True)
        self.summary_text.setStyleSheet("font-size: 14px; padding: 10px; background-color: #2d2d2d; border-radius: 6px;")
        layout.addWidget(self.summary_text)

        # Tools table (basic overview)
        self.tools_table = QTableWidget(0, 3)
        self.tools_table.setHorizontalHeaderLabels(["Tool #", "Type", "Insert Name / Dimension"])
        self.tools_table.setEditTriggers(QTableWidget.NoEditTriggers)  # read-only
        self.tools_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tools_table)

        # Buttons
        btn_layout = QHBoxLayout()
        self.edit_tools_btn = QPushButton("Edit Tools...")
        self.edit_tools_btn.clicked.connect(self.open_tool_editor)

        self.save_custom_btn = QPushButton("Save as New Custom Template")
        self.save_custom_btn.clicked.connect(self.save_as_custom_template)
        self.save_custom_btn.setVisible(False)

        btn_layout.addWidget(self.edit_tools_btn)
        btn_layout.addWidget(self.save_custom_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def initializePage(self):
        """Called every time this page becomes visible"""
        self.update_summary_and_table()

    def update_summary_and_table(self):
        """Populate summary and tools table"""
        if not self.wizard.selected_template:
            self.summary_text.setText("No machine selected.")
            self.tools_table.setRowCount(0)
            return

        template = self.wizard.selected_template

        # Build summary
        summary = f"<b>{template.machine_name}</b><br>"
        summary += f"Control: {template.control_type}<br>"
        summary += f"Units: {self.wizard.selected_units}<br>"
        summary += f"Max Tools: {template.max_tools} | Spindles: {template.spindles}<br>"

        if template.lathe_options:
            lo = template.lathe_options
            if lo.has_y_axis:
                summary += "• Y-axis (live tooling): Yes<br>"
            if lo.has_subspindle:
                summary += "• Sub-spindle (B-axis): Yes<br>"
            if lo.has_tailstock:
                summary += "• Tailstock: Yes<br>"

        if template.additional_axes:
            summary += f"• Additional axes: {', '.join(template.additional_axes)}<br>"

        self.summary_text.setText(summary)

        # Populate tools table
        self.tools_table.setRowCount(len(template.starter_tools))
        for row, tool in enumerate(template.starter_tools):
            self.tools_table.setItem(row, 0, QTableWidgetItem(tool.tool_number))
            self.tools_table.setItem(row, 1, QTableWidgetItem(tool.type))

            dimension = tool.insert_name
            if tool.diameter > 0:
                dimension += f" Ø{tool.diameter:.4f}"
            elif tool.nose_radius > 0:
                dimension += f" R{tool.nose_radius:.4f}"
            self.tools_table.setItem(row, 2, QTableWidgetItem(dimension))

    def open_tool_editor(self):
            """Open the Tool Editor dialog and apply changes back to the template"""
            if not self.wizard.selected_template:
                QMessageBox.warning(self, "No Template", "No machine template selected.")
                return

            # Open the dialog with current starter tools
            dialog = ToolEditorDialog(self.wizard.selected_template.starter_tools, self)
            
            if dialog.exec() == QDialog.Accepted:
                # Apply the edited tools back to the selected template
                self.wizard.selected_template.starter_tools = dialog.tools.copy()
                
                # Refresh the review page table and summary
                self.update_summary_and_table()
                
                # Mark that changes were made (so "Save as Custom Template" button can appear)
                self.wizard.changes_made = True
                self.save_custom_btn.setVisible(True)

    def save_as_custom_template(self):
        """Save the current modified template as a new custom template."""
        if not self.wizard.selected_template:
            QMessageBox.warning(self, "No Template", "No machine selected.")
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Save Custom Template",
            "Enter a name for the new custom template:",
            QLineEdit.Normal,
            f"{self.wizard.selected_template.machine_name} (Custom)"
        )

        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()

        # Create copy with edited tools
        custom_template = MachineTemplate(
            machine_name=new_name,
            control_type=self.wizard.selected_template.control_type,
            default_units=self.wizard.selected_units,
            axis_travel=self.wizard.selected_template.axis_travel.copy(),
            max_rapid_ipm=self.wizard.selected_template.max_rapid_ipm,
            max_feed_ipm=self.wizard.selected_template.max_feed_ipm,
            acceleration=self.wizard.selected_template.acceleration.copy(),
            spindle_max_rpm=self.wizard.selected_template.spindle_max_rpm,
            spindle_max_hp=self.wizard.selected_template.spindle_max_hp,
            spindles=self.wizard.selected_template.spindles,
            max_tools=self.wizard.selected_template.max_tools,
            lathe_options=self.wizard.selected_template.lathe_options,
            additional_axes=self.wizard.selected_template.additional_axes.copy() if self.wizard.selected_template.additional_axes else [],
            starter_tools=[Tool(**t.__dict__) for t in self.wizard.selected_template.starter_tools],  # deep copy
            initial_modals=self.wizard.selected_template.initial_modals.copy(),
            tool_number_format=self.wizard.selected_template.tool_number_format
        )

        # Save and reload
        success = self.wizard.template_loader.create_custom_template(custom_template)

        if success:
            # Force reload of custom templates
            self.wizard.template_loader.reload_custom_templates()
            
            QMessageBox.information(
                self, 
                "Custom Template Saved", 
                f"Custom template '{new_name}' has been saved.\n\n"
                "It should now appear in the dropdown on next wizard launch."
            )
            self.save_custom_btn.setVisible(False)
            self.wizard.changes_made = False
        else:
            QMessageBox.warning(self, "Save Failed", "Failed to save custom template.")
        
class ToolEditorDialog(QDialog):
    def __init__(self, starter_tools: list[Tool], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Tools")
        self.resize(1000, 650)

        self.tools = [Tool(**tool.__dict__) for tool in starter_tools]  # copy

        # Load type lists
        self.tool_types = self._load_tool_types()
        self.insert_types = self._load_insert_types()

        layout = QVBoxLayout(self)

        self.table = QTableWidget(len(self.tools), 5)
        self.table.setHorizontalHeaderLabels([
            "Tool #", "Type", "Insert Name", "Dimension", "Notes"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.populate_table()

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add New Tool")
        delete_btn = QPushButton("Delete Selected")
        add_btn.clicked.connect(self.add_tool)
        delete_btn.clicked.connect(self.delete_selected)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_tool_types(self):
        try:
            path = Path(__file__).parent.parent.parent / "core" / "templates" / "tool_types.json"
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("tool_types", [])
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load tool types: {e}")
            return ["OD Turning", "Solid Endmill", "Twist Drill", "OD Threading", "Boring Bar", "Grooving Tool"]

    def _load_insert_types(self):
        try:
            path = Path(__file__).parent.parent.parent / "core" / "templates" / "insert_types.json"
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("insert_types", [])
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load insert types: {e}")
            return ["CNMG 432", "R390", "IR16 Lay Down"]

    def populate_table(self):
        self.table.setRowCount(len(self.tools))
        for row, tool in enumerate(self.tools):
            # Tool #
            item = QTableWidgetItem(tool.tool_number)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.table.setItem(row, 0, item)

            # Type (combo)
            combo = QComboBox()
            combo.addItems(self.tool_types)
            combo.setCurrentText(tool.type)
            self.table.setCellWidget(row, 1, combo)

            # Insert Name (combo)
            insert_combo = QComboBox()
            insert_combo.addItems(self.insert_types)
            insert_combo.setCurrentText(tool.insert_name)
            self.table.setCellWidget(row, 2, insert_combo)

            # Dimension
            dim = ""
            if tool.diameter > 0:
                dim = f"Ø{tool.diameter:.4f}"
            elif tool.nose_radius > 0:
                dim = f"R{tool.nose_radius:.4f}"
            self.table.setItem(row, 3, QTableWidgetItem(dim))

            # Notes
            notes_item = QTableWidgetItem(tool.notes)
            notes_item.setFlags(notes_item.flags() | Qt.ItemIsEditable)
            self.table.setItem(row, 4, notes_item)

    def add_tool(self):
        next_num = self._get_next_tool_number()
        new_tool = Tool(tool_number=next_num, insert_name="CNMG 432", type="turning_insert")
        self.tools.append(new_tool)
        self.populate_table()
        self.table.selectRow(len(self.tools) - 1)

    def _get_next_tool_number(self) -> str:
        """Return next available tool number like T02, T03, etc."""
        existing = [t.tool_number for t in self.tools]
        num = 1
        while True:
            candidate = f"T{num:02d}"
            if candidate not in existing:
                return candidate
            num += 1

    def delete_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            del self.tools[row]
            self.populate_table()

    def accept(self):
        # Save changes back to the tools list (we'll connect this to wizard later)
        for row in range(len(self.tools)):
            tool = self.tools[row]
            tool.tool_number = self.table.item(row, 0).text() if self.table.item(row, 0) else tool.tool_number
            tool.type = self.table.cellWidget(row, 1).currentText() if self.table.cellWidget(row, 1) else tool.type
            tool.insert_name = self.table.cellWidget(row, 2).currentText() if self.table.cellWidget(row, 2) else tool.insert_name
            tool.notes = self.table.item(row, 4).text() if self.table.item(row, 4) else tool.notes
        super().accept()

