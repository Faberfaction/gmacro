# src/constants.py

# Colors
GREEN = "#00ff00"
RED = "#ff5555"
PURPLE = "#c586c0"
TEAL = "#4ec9b0"
DARK_GREEN = "#00aa00"
BLUE = "#569cd6"
LIGHT_RED = "#ff5555"
GREEN_VAR = "#b5cea8"
CYAN = "#4ec9b0"
GRAY_GREEN = "#6a9955"
LIGHT_GRAY = "#d4d4d4"
ORANGE = "#f4a261"
PALE_YELLOW = "#e5e510"

# Defaults
DEFAULT_VAR_NUMBER = "101"
DEFAULT_UNITS = "Imperial"

# Regex patterns
G_CODE_PATTERN = r'\bG\d+\b'
M_CODE_PATTERN = r'\bM\d+\b'
S_CODE_PATTERN = r'\bS\d+\b'
T_CODE_PATTERN = r'\bT\d+\b'
FEED_PATTERN = r'\bF\d*\.?\d*\b'
AXIS_X_PATTERN = r'\bX\s*-?\d*\.?\d*\b'
AXIS_Y_PATTERN = r'\bY\s*-?\d*\.?\d*\b'
AXIS_Z_PATTERN = r'\bZ\s*-?\d*\.?\d*\b'
VARIABLE_PATTERN = r'#\w+'
COMMENT_PATTERN = r'\(.*?\)'
NUMBER_PATTERN = r'(?<![\w#])[+-]?\d+\.?\d*\b'
LOGIC_PATTERN = r'\b(IF|WHILE|DO1|END1|GOTO)\b'