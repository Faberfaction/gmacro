from PySide6.QtWidgets import (
    QMessageBox, QPlainTextEdit, QWidget
)
from PySide6.QtGui import (
    QFont, QTextOption, QSyntaxHighlighter, QTextCharFormat,
    QColor, QPainter, QTextCursor
)
from PySide6.QtCore import Qt, QTimer, QRect, QRegularExpression

from src.core.templates.models import MachineTemplate
from src.constants import (
    PURPLE, PALE_YELLOW, TEAL, DARK_GREEN, BLUE, LIGHT_RED,
    GREEN_VAR, CYAN, GRAY_GREEN, LIGHT_GRAY, ORANGE,
    G_CODE_PATTERN, M_CODE_PATTERN, S_CODE_PATTERN, T_CODE_PATTERN,
    FEED_PATTERN, AXIS_X_PATTERN, AXIS_Y_PATTERN, AXIS_Z_PATTERN,
    VARIABLE_PATTERN, COMMENT_PATTERN, LOGIC_PATTERN
)

class MacroHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.setup_formats()

    def setup_formats(self):
        # G-codes - Purple
        self.gcode_format = QTextCharFormat()
        self.gcode_format.setForeground(QColor(PURPLE))

        # M, S, T codes - Pale Yellow
        self.smt_format = QTextCharFormat()
        self.smt_format.setForeground(QColor(PALE_YELLOW))

        # Feed (F words) - Bright Cyan/Teal
        self.feed_format = QTextCharFormat()
        self.feed_format.setForeground(QColor(TEAL))

        # X words - Dark Green
        self.x_axis_format = QTextCharFormat()
        self.x_axis_format.setForeground(QColor(DARK_GREEN))

        # Y words - Blue
        self.y_axis_format = QTextCharFormat()
        self.y_axis_format.setForeground(QColor(BLUE))

        # Z words - Red
        self.z_axis_format = QTextCharFormat()
        self.z_axis_format.setForeground(QColor(LIGHT_RED))

        # Variables (#100, #PART_DIA) - Green
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor(GREEN_VAR))

        # Friendly names - Cyan
        self.friendly_format = QTextCharFormat()
        self.friendly_format.setForeground(QColor(CYAN))

        # Comments ( ) - Gray-green
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(GRAY_GREEN))

        # Numbers - Light gray
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor(LIGHT_GRAY))

        # Logic keywords - Orange
        self.logic_format = QTextCharFormat()
        self.logic_format.setForeground(QColor(ORANGE))

    def highlightBlock(self, text: str):
        # 1. G-codes
        self.highlight_pattern(text, G_CODE_PATTERN, self.gcode_format)

        # 2. M, S, T codes
        self.highlight_pattern(text, f'\\b[{M_CODE_PATTERN[2]}{S_CODE_PATTERN[2]}{T_CODE_PATTERN[2]}]\\d+\\b', self.smt_format)

        # 3. Feed (F words)
        self.highlight_pattern(text, FEED_PATTERN, self.feed_format)

        # 4. Axis values - much stronger pattern to capture full number including decimal and sign
        self.highlight_pattern(text, AXIS_X_PATTERN, self.x_axis_format)
        self.highlight_pattern(text, AXIS_Y_PATTERN, self.y_axis_format)
        self.highlight_pattern(text, AXIS_Z_PATTERN, self.z_axis_format)

        # 5. Variables
        self.highlight_pattern(text, VARIABLE_PATTERN, self.variable_format)

        # 6. Comments
        self.highlight_pattern(text, COMMENT_PATTERN, self.comment_format)

        # 7. Standalone numbers (not part of axis or F)
        # self.highlight_pattern(text, NUMBER_PATTERN, self.number_format)

        # 8. Logic keywords
        self.highlight_pattern(text, LOGIC_PATTERN, self.logic_format)
   
    def highlight_pattern(self, text: str, pattern: str, fmt: QTextCharFormat):
        regex = QRegularExpression(pattern)
        match_iterator = regex.globalMatch(text)
        while match_iterator.hasNext():
            match = match_iterator.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#2d2d2d"))

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#888888"))
                painter.drawText(0, int(top), self.width() - 5, int(self.editor.fontMetrics().height()),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            block_number += 1

class MacroEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Font
        font = QFont("Consolas", 12)
        self.setFont(font)

        # Line number area
        self.line_number_area = LineNumberArea(self)
        self.line_number_area_width = 50
        self.setViewportMargins(self.line_number_area_width, 0, 0, 0)

        # Word wrap off by default
        self.setWordWrapMode(QTextOption.NoWrap)

        # Auto-indent: 2 spaces
        self.setTabStopDistance(2 * self.fontMetrics().horizontalAdvance(' '))

        # Dark theme
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
            }
        """)

        self.template: MachineTemplate | None = None

        # Create and assign the highlighter
        self.highlighter = MacroHighlighter(self.document())

        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)

        # Timer for monitoring cursor position and highlighting mappings
        self.highlight_timer = QTimer(self)
        self.highlight_timer.setInterval(300)  # check every 300ms
        self.highlight_timer.timeout.connect(self.update_mapping_highlight)
        self.highlight_timer.start()

    def set_machine_template(self, template: MachineTemplate):
        self.template = template
        print(f"Editor configured for machine: {template.machine_name}")

    def update_line_number_area_width(self):
        """Dynamically resize the line number area"""
        digits = len(str(max(1, self.blockCount())))
        new_width = 30 + self.fontMetrics().horizontalAdvance('9') * max(digits, 3)

        if new_width != self.line_number_area_width:
            self.line_number_area_width = new_width
            self.setViewportMargins(self.line_number_area_width, 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Update the line number area when scrolling"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area_width, rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        """Resize the line number area when editor resizes"""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(0, cr.top(), self.line_number_area_width, cr.height())
        )
    
    def keyPressEvent(self, event):
        """Intercept # key to show variable mapping popup without typing #"""
        if event.text() == '#':
            # Prevent # from being typed; show popup instead
            self.show_variable_mapping_popup()
            return

        super().keyPressEvent(event)

    def show_variable_mapping_popup(self):
        """Show context menu with suggestions from the variable map (# not yet typed)"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        menu = QMenu(self)

        # Get all suggestions from the variable map
        if hasattr(self.window(), 'variable_map_widget'):
            vm = self.window().variable_map_widget
            suggestions = vm.get_suggestions("")

            for suggestion in suggestions:
                action = QAction(suggestion, menu)
                action.triggered.connect(lambda checked, s=suggestion: self.insert_suggestion(s))
                menu.addAction(action)

            if suggestions:
                menu.addSeparator()

        # Always show "Create new mapping..." option
        create_action = QAction("Create new mapping...", menu)
        create_action.triggered.connect(self.create_new_variable_mapping)
        menu.addAction(create_action)

        # Show menu below cursor
        cursor = self.textCursor()
        cursor_rect = self.cursorRect(cursor)
        global_pos = self.mapToGlobal(cursor_rect.bottomLeft())
        menu.exec(global_pos)

    def create_new_variable_mapping(self):
        """Open variable map dialog and insert the friendly name with # prefix"""
        if not hasattr(self.window(), 'variable_map_widget'):
            QMessageBox.information(self, "Variable Map", "Variable Map not available.")
            return

        vm = self.window().variable_map_widget
        added_friendly = vm.add_mapping(prefill_friendly="")

        if added_friendly:
            cursor = self.textCursor()
            cursor.insertText(f"#{added_friendly}")
            self.setTextCursor(cursor)
            self.setFocus()

    def insert_suggestion(self, full_suggestion: str):
        """Insert the friendly name with # prefix (extracted from suggestion format)"""
        # Extract friendly name from format like "#DIA (#101)"
        if '(' in full_suggestion:
            friendly_part = full_suggestion.split('(')[0].strip()
        else:
            friendly_part = full_suggestion.strip()

        # Ensure exactly one leading #
        friendly_part = friendly_part.lstrip('#')

        cursor = self.textCursor()
        cursor.insertText(f"#{friendly_part}")
        self.setTextCursor(cursor)
        self.setFocus()

    def update_mapping_highlight(self):
        """Check current word under cursor and highlight in variable map if it's a mapping"""
        if not hasattr(self.window(), 'variable_map_widget'):
            return

        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos = cursor.positionInBlock()

        if pos == 0:
            self.window().variable_map_widget.highlight_mapping("")
            return

        # Extract the word under cursor safely
        start = pos
        while start > 0 and (block_text[start-1].isalnum() or block_text[start-1] == '_'):
            start -= 1

        end = pos
        while end < len(block_text) and (block_text[end].isalnum() or block_text[end] == '_'):
            end += 1

        word = block_text[start:end].strip()

        if word.startswith('#'):
            word = word[1:]  # remove # for lookup

        vm = self.window().variable_map_widget
        vm.highlight_mapping(word)

    def highlight_line(self, line_number: int):
        """Highlight the current executing line in the editor"""
        if line_number < 0:
            return

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)           # ← Fixed
        for _ in range(line_number):
            cursor.movePosition(QTextCursor.Down)

        cursor.select(QTextCursor.LineUnderCursor)       # ← Also fixed
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
