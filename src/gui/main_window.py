from pathlib import Path
from datetime import datetime
import json
from PySide6.QtWidgets import QFileDialog, QMessageBox
from src.core.templates.loader import TemplateLoader

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout, QLabel, QToolBar,
    QDockWidget, QPushButton
)
from PySide6.QtCore import Qt, QSize

from src.gui.editor.macro_editor import MacroEditor
from src.gui.variable_map.variable_map_widget import VariableMapWidget
from src.core.simulator.controller import SimulationController
from src.core.templates.models import MachineTemplate
from src.constants import GREEN, RED

class MainWindow(QMainWindow):
    def __init__(self, project_path: Path, template: MachineTemplate):
        super().__init__()
        self.project_path = project_path
        self.template = template

        self.setWindowTitle(f"MacroForge - {project_path.name} [{template.machine_name}]")
        self.resize(1600, 900)

        # Central splitter: Editor | Backplot
        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)

        # Left: Macro Editor
        self.editor = MacroEditor()
        if template:
            self.editor.set_machine_template(template)
        self.splitter.addWidget(self.editor)

        # Load project content
        # self.load_project_content()

        # Right: Backplot (hidden by default)
        self.backplot_placeholder = QLabel(
            "Backplot Area\n\n"
            "Tool path visualization, part bounds, and live tool movement\n"
            "will appear here once simulation is running."
        )
        self.backplot_placeholder.setAlignment(Qt.AlignCenter)
        self.backplot_placeholder.setStyleSheet("""
            background-color: #1e1e1e; 
            color: #888888; 
            font-size: 15px;
            border-left: 1px solid #333;
        """)
        self.backplot_placeholder.setMinimumWidth(450)
        self.backplot_placeholder.setVisible(False)
        self.splitter.addWidget(self.backplot_placeholder)

        # Variable Map Dock Widget (left side)
        self.variable_map_dock = QDockWidget("Variable Map", self)
        self.variable_map_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.variable_map_widget = VariableMapWidget()
        self.variable_map_dock.setWidget(self.variable_map_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.variable_map_dock)
        self.variable_map_dock.setVisible(True)
        self.variable_map_dock.visibilityChanged.connect(self.update_var_map_button_style)

        # Load project content
        self.load_project_content()

        # Simulation Controller (initialize after content is loaded)
        self.controller = SimulationController(self.editor, template)
        self.controller.load_program(self.editor.toPlainText())
       
        # Create toolbar AFTER the dock exists
        self.create_toolbar()

        # Status bar
        self.statusBar().showMessage(f"Project: {project_path.name} | Machine: {template.machine_name} | Units: {template.default_units}")

        print(f"MainWindow opened for project: {project_path}")
        self.reload_program()

    def load_project_content(self):
        """Load the macro file and project settings for the current project"""
        try:
            # Load project settings
            settings_file = self.project_path / "project_settings.json"
            settings = {}
            if settings_file.exists():
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            else:
                print(f"Warning: {settings_file} not found - using defaults")

            # Get main NC filename from settings (default fallback)
            nc_filename = settings.get("main_nc_file", "main.nc")
            nc_file = self.project_path / nc_filename

            # Load NC file into editor
            if nc_file.exists():
                with open(nc_file, "r", encoding="utf-8") as f:
                    code = f.read()
                self.editor.setPlainText(code)
                print(f"Loaded {len(code.splitlines())} lines from {nc_filename}")
            else:
                print(f"Warning: {nc_file} not found - starting with empty editor")
                self.editor.setPlainText(f"({nc_filename.upper()} - New Program)\nG90 G54\n")

            # Load variable map
            if hasattr(self, 'variable_map_widget') and "variable_map" in settings:
                self.variable_map_widget.clear_mappings()
                for item in settings["variable_map"]:
                    friendly = item.get("friendly")
                    raw = item.get("raw")
                    if friendly and raw:
                        self.variable_map_widget.mappings[friendly] = raw
                self.variable_map_widget.refresh_table()
                print(f"Loaded {len(settings['variable_map'])} variable mappings")

            # Store the current nc filename for saving later
            self.main_nc_filename = nc_filename

        except Exception as e:
            print(f"Error loading project content: {e}")
            QMessageBox.warning(self, "Load Error", f"Failed to load project content:\n{e}")

    def create_toolbar(self):
        """Create the main toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # File operations
        toolbar.addSeparator()

        self.open_action = toolbar.addAction("Open")
        self.open_action.triggered.connect(self.open_project)

        self.save_action = toolbar.addAction("Save")
        self.save_action.triggered.connect(self.save_project)

        # Variable Map Toggle Button {#}
        self.var_map_btn = QPushButton("{#}")
        self.var_map_btn.setCheckable(True)
        self.var_map_btn.clicked.connect(self.toggle_variable_map)
        toolbar.addWidget(self.var_map_btn)

        # Backplot Toggle
        toolbar.addSeparator()
        self.toggle_backplot_action = toolbar.addAction("Show Backplot")
        self.toggle_backplot_action.setCheckable(True)
        self.toggle_backplot_action.triggered.connect(self.toggle_backplot)

        # Simulation controls
        toolbar.addSeparator()
        self.step_action = toolbar.addAction("Step")
        self.step_motion_action = toolbar.addAction("Step to Motion")
        self.run_action = toolbar.addAction("Run")
        self.pause_action = toolbar.addAction("Pause")
        self.reset_action = toolbar.addAction("Reset")

        self.step_action.triggered.connect(self.controller.step)
        self.step_motion_action.triggered.connect(self.controller.step)   # temporary
        self.run_action.triggered.connect(self.controller.run)
        self.pause_action.triggered.connect(self.controller.stop)
        self.reset_action.triggered.connect(self.controller.reset)

    def save_project(self):
        """Save the current project (project_settings.json + main NC file)"""
        if not hasattr(self, 'editor'):
            return

        try:
            # Use the stored filename or default to main.nc
            nc_filename = getattr(self, 'main_nc_filename', "main.nc")
            nc_file = self.project_path / nc_filename

            # Save the NC program
            with open(nc_file, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())

            # Save variable map
            if hasattr(self, 'variable_map_widget'):
                var_map = self.variable_map_widget.get_all_mappings()
            else:
                var_map = []

            settings = {
                "project_name": self.project_path.name,
                "machine_name": self.template.machine_name,
                "units": self.template.default_units,
                "main_nc_file": nc_filename,           # Important: persist filename
                "work_offsets": {"G54": {"X": 0.0, "Y": 0.0, "Z": 0.0}},
                "variable_map": var_map,
                "last_saved": datetime.now().isoformat()
            }

            with open(self.project_path / "project_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)

            self.statusBar().showMessage(f"Project saved: {self.project_path.name} ({nc_filename})")
        except Exception as e:
            QMessageBox.warning(self, "Save Failed", f"Could not save project: {e}")

    def open_project(self):
        """Open an existing project folder"""
        folder = QFileDialog.getExistingDirectory(self, "Open Project Folder", str(Path.home() / "Documents"))
        if not folder:
            return

        project_path = Path(folder)
        settings_file = project_path / "project_settings.json"

        if not settings_file.exists():
            QMessageBox.warning(self, "Invalid Project", "No project_settings.json found in this folder.")
            return

        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)

            machine_name = settings.get("machine_name")
            loader = TemplateLoader()
            template = loader.get_template_by_name(machine_name)

            if not template:
                QMessageBox.warning(self, "Error", f"Machine template '{machine_name}' not found.")
                return

            # Clear previous variable mappings before loading new ones
            if hasattr(self, 'variable_map_widget'):
                self.variable_map_widget.clear_mappings()

            # Load main.nc into editor
            nc_file = project_path / settings.get("main_nc_file", "main.nc")
            if nc_file.exists():
                with open(nc_file, "r", encoding="utf-8") as f:
                    code = f.read()
                self.editor.setPlainText(code)

            self.project_path = project_path
            self.template = template
            self.editor.set_machine_template(template)

            # Load variable map
            if hasattr(self, 'variable_map_widget') and "variable_map" in settings:
                for item in settings["variable_map"]:
                    friendly = item.get("friendly")
                    raw = item.get("raw")
                    if friendly and raw:
                        self.variable_map_widget.mappings[friendly] = raw
                self.variable_map_widget.refresh_table()

            self.statusBar().showMessage(f"Opened project: {project_path.name}")
        except Exception as e:
            QMessageBox.warning(self, "Open Failed", f"Could not open project: {e}")

    def toggle_variable_map(self):
        """Toggle the Variable Map dock"""
        if hasattr(self, 'variable_map_dock'):
            checked = not self.variable_map_dock.isVisible()
            self.variable_map_dock.setVisible(checked)
            self.update_var_map_button_style()

    def update_var_map_button_style(self, visible=None):
        """Update button color based on dock visibility"""
        if not hasattr(self, 'variable_map_dock') or not hasattr(self, 'var_map_btn'):
            return

        if visible is None:
            visible = self.variable_map_dock.isVisible()

        if visible:
            self.var_map_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {GREEN};
                    font-weight: bold;
                    font-size: 16px;
                    padding: 4px 12px;
                }}
            """)
            self.var_map_btn.setChecked(True)
        else:
            self.var_map_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {RED};
                    font-weight: bold;
                    font-size: 16px;
                    padding: 4px 12px;
                }}
            """)
            self.var_map_btn.setChecked(False)

    def showEvent(self, event):
        """Called when the window is shown - perfect time to set initial button state"""
        super().showEvent(event)
        # Update button style after the window and dock are fully realized
        self.update_var_map_button_style()

    def toggle_backplot(self, checked: bool):
        """Toggle backplot panel"""
        if hasattr(self, 'backplot_placeholder'):
            self.backplot_placeholder.setVisible(checked)
            if checked:
                self.toggle_backplot_action.setText("Hide Backplot")
            else:
                self.toggle_backplot_action.setText("Show Backplot")

    def reload_program(self):
        """Reload editor content into simulator"""
        if hasattr(self, 'controller'):
            self.controller.load_program(self.editor.toPlainText())   

