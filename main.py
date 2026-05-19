import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.templates.loader import TemplateLoader
from src.gui.main_window import MainWindow
from src.core.templates.models import MachineTemplate

if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        # === TEMPORARY TESTING BYPASS ===
        # Change this line to any machine name you want for quick testing
        test_machine_name = "Haas ST-20Y"

        loader = TemplateLoader()
        template = loader.get_template_by_name(test_machine_name)

        if not template:
            QMessageBox.critical(None, "Template Not Found", 
                f"Could not find template '{test_machine_name}'\n\n"
                f"Available machines: {', '.join([t.machine_name for t in loader.get_all_templates()])}")
            sys.exit(1)

        # Create a temporary project path for testing
        test_project_path = Path.home() / "Documents" / "Haas_ST-20Y_project"

        print(f"Launching MainWindow directly with: {test_machine_name}")
        main_win = MainWindow(test_project_path, template)
        main_win.show()

        sys.exit(app.exec())
    except Exception as e:
        QMessageBox.critical(None, "Application Error", f"Failed to start MacroForge: {e}")
        sys.exit(1)
