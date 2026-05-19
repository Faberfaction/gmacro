from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QMessageBox, QInputDialog,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox
)
from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt

class VariableMapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        header = QLabel("Variable Mapping")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        layout.addWidget(header)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Friendly Name", "Raw Variable", "Description"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")

        self.add_btn.clicked.connect(self.add_mapping)
        self.edit_btn.clicked.connect(self.edit_mapping)
        self.delete_btn.clicked.connect(self.delete_mapping)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)

        self.mappings = {}  # friendly_name -> raw_variable

    def add_mapping(self, prefill_friendly: str = "") -> str | None:
        """Add a new mapping using a single dialog box with # labels for both fields"""
        if prefill_friendly is None or isinstance(prefill_friendly, bool):
            prefill_friendly = ""

        prefill_raw = None  # Track raw input across retries

        while True:  # Loop to allow retry on duplicate
            dialog = QDialog(self)
            dialog.setWindowTitle("New Variable Mapping")
            layout = QFormLayout(dialog)

            friendly_layout = QHBoxLayout()
            friendly_label = QLabel("#")
            friendly_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            friendly_edit = QLineEdit(str(prefill_friendly).upper().lstrip('#'))
            friendly_layout.addWidget(friendly_label)
            friendly_layout.addWidget(friendly_edit)
            layout.addRow("Friendly Name:", friendly_layout)

            raw_layout = QHBoxLayout()
            raw_label = QLabel("#")
            raw_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            # Use preserved raw input if available, otherwise suggest next available
            default_raw = prefill_raw if prefill_raw else self._get_next_available_raw_number()
            raw_edit = QLineEdit(default_raw)
            raw_layout.addWidget(raw_label)
            raw_layout.addWidget(raw_edit)
            layout.addRow("Raw Variable:", raw_layout)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addRow(button_box)

            if dialog.exec() != QDialog.Accepted:
                if hasattr(self.window(), 'editor'):
                    self.window().editor.setFocus()
                return None

            try:
                friendly = friendly_edit.text().strip().upper().lstrip('#')
                raw_number = raw_edit.text().strip()
                prefill_raw = raw_number  # Preserve for next retry if needed

                if not friendly:
                    QMessageBox.warning(self, "Invalid", "Friendly Name cannot be empty.")
                    prefill_friendly = ""  # Clear for next attempt
                    continue

                if not raw_number.isdigit():
                    QMessageBox.warning(self, "Invalid", "Raw variable must be a number (e.g. 101)")
                    prefill_friendly = friendly  # Keep friendly name, let them fix raw
                    continue

                # Check for duplicate friendly name - reject, don't allow overwrite
                if friendly in self.mappings:
                    QMessageBox.warning(self, "Duplicate", 
                        f"Friendly name '{friendly}' already exists.\nPlease choose a unique name.")
                    prefill_friendly = friendly  # Let them edit it
                    continue

                raw = f"#{raw_number}"
                
                # Check for duplicate raw variable number
                if raw in self.mappings.values():
                    QMessageBox.warning(self, "Duplicate", 
                        f"Raw variable '{raw}' is already in use.\nPlease choose a different number.")
                    prefill_friendly = friendly  # Keep friendly, let them fix raw
                    continue

                self.mappings[friendly] = raw
                self.refresh_table()

                # Return focus to editor
                if hasattr(self.window(), 'editor'):
                    self.window().editor.setFocus()

                return friendly

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create variable mapping: {e}")
                if hasattr(self.window(), 'editor'):
                    self.window().editor.setFocus()
                return None

    def _get_next_available_raw_number(self) -> str:
        """Return next available raw variable number as string (e.g. '102')"""
        used = []
        for v in self.mappings.values():
            if v.startswith('#') and v[1:].isdigit():
                used.append(int(v[1:]))
        
        num = 101
        while num in used:
            num += 1
        return str(num)

    def edit_mapping(self):
        row = self.table.currentRow()
        if row < 0:
            return

        friendly = self.table.item(row, 0).text().lstrip('#')
        current_raw = self.table.item(row, 1).text()

        new_raw, ok = QInputDialog.getText(self, "Edit Mapping", f"Raw Variable for {friendly}:", text=current_raw)
        if ok and new_raw.strip():
            if not new_raw.startswith('#'):
                new_raw = '#' + new_raw
            
            new_raw = new_raw.strip()
            
            # Check if trying to change to a different raw variable that's already in use
            if new_raw != current_raw and new_raw in self.mappings.values():
                QMessageBox.warning(self, "Duplicate", 
                    f"Raw variable '{new_raw}' is already in use by another mapping.\nPlease choose a different number.")
                return
            
            self.mappings[friendly] = new_raw
            self.refresh_table()

    def delete_mapping(self):
        row = self.table.currentRow()
        if row < 0:
            return

        friendly = self.table.item(row, 0).text()
        reply = QMessageBox.question(self, "Delete", f"Delete mapping '{friendly}'?")
        if reply == QMessageBox.Yes:
            del self.mappings[friendly]
            self.refresh_table()

    def clear_mappings(self):
        """Clear all mappings (used when opening a new project)"""
        self.mappings.clear()
        self.refresh_table()

    def refresh_table(self):
        """Refresh the table from current mappings"""
        self.table.setRowCount(len(self.mappings))
        for row, (friendly, raw) in enumerate(self.mappings.items()):
            # Show friendly name with # prefix for visual consistency
            display_friendly = f"#{friendly}" if not friendly.startswith('#') else friendly
            
            self.table.setItem(row, 0, QTableWidgetItem(display_friendly))
            self.table.setItem(row, 1, QTableWidgetItem(raw))
            self.table.setItem(row, 2, QTableWidgetItem(""))

    def get_mapping(self, friendly_name: str) -> str | None:
        """Used by editor popup"""
        return self.mappings.get(friendly_name.upper())
    
    def get_suggestions(self, partial: str) -> list:
        """Return friendly suggestions in the format '#FRIENDLY (#101)'"""
        if not partial:
            partial = ""

        partial = partial.upper()
        suggestions = []

        for friendly, raw in self.mappings.items():
            if partial in friendly.upper():
                display = f"#{friendly} ({raw})"
                suggestions.append(display)

        # Sort alphabetically
        suggestions.sort()
        return suggestions

    def highlight_mapping(self, friendly_name: str):
        """Highlight the row for a given friendly name"""
        if not friendly_name:
            self.table.clearSelection()
            return

        friendly = friendly_name.upper().lstrip('#')

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text().upper().lstrip('#') == friendly:
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                return

        # No match
        self.table.clearSelection()

    def get_last_added_friendly(self) -> str:
        """Return the last added friendly name (for insertion after dialog)"""
        if self.mappings:
            return list(self.mappings.keys())[-1]
        return ""
    
    def get_all_mappings(self):
        """Return list of mappings suitable for saving to project_settings.json"""
        return [{"friendly": friendly, "raw": raw} 
                for friendly, raw in self.mappings.items()]
