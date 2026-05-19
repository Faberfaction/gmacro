from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression

class MacroHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.setup_formats()

    def setup_formats(self):
        """Define text formats for different elements"""
        
        # G-code words (G00, G01, G02, G03, G96, G97, etc.)
        self.gcode_format = QTextCharFormat()
        self.gcode_format.setForeground(QColor("#569cd6"))   # blue
        self.gcode_format.setFontWeight(QFont.Bold)

        # M-codes
        self.mcode_format = QTextCharFormat()
        self.mcode_format.setForeground(QColor("#c586c0"))   # purple

        # Variables (#100, #500, V1, etc.)
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor("#b5cea8"))  # green

        # Friendly names (after mapping)
        self.friendly_format = QTextCharFormat()
        self.friendly_format.setForeground(QColor("#c586c0"))  # purple

        # Comments
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6a9955"))   # gray-green

        # Numbers
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#b5cea8"))

    def highlightBlock(self, text: str):
        """Main highlighting logic"""
        # 1. Highlight G-codes (G followed by numbers)
        gcode_pattern = QRegularExpression(r'\bG\d+\b')
        self.highlight_pattern(text, gcode_pattern, self.gcode_format)

        # 2. Highlight M-codes
        mcode_pattern = QRegularExpression(r'\bM\d+\b')
        self.highlight_pattern(text, mcode_pattern, self.mcode_format)

        # 3. Highlight variables (#xxx or Vxxx)
        var_pattern = QRegularExpression(r'[#V]\d+')
        self.highlight_pattern(text, var_pattern, self.variable_format)

        # 4. Highlight comments (anything after ;)
        comment_pattern = QRegularExpression(r';.*$')
        self.highlight_pattern(text, comment_pattern, self.comment_format)

        # 5. Highlight numbers
        number_pattern = QRegularExpression(r'\b\d+\.?\d*\b')
        self.highlight_pattern(text, number_pattern, self.number_format)

    def highlight_pattern(self, text: str, pattern: QRegularExpression, fmt: QTextCharFormat):
        """Helper to apply format to all matches"""
        match_iterator = pattern.globalMatch(text)
        while match_iterator.hasNext():
            match = match_iterator.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), fmt)