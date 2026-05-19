import re
from typing import Tuple, Optional

from .state import SimulatorState

class Executor:
    def __init__(self, state: SimulatorState, main_window=None):
        self.state = state
        self.main_window = main_window   # Optional reference for UI updates
        self.line_number = 0

    def execute_line(self, original_line: str) -> Tuple[bool, Optional[str]]:
        """Execute one line of Macro B code."""
        self.line_number += 1
        self.state.last_original_line = original_line

        # Log for debugging
        print(f"Line {self.line_number}: {original_line.strip()}")

        # Skip empty lines, pure comments, or program markers
        stripped = original_line.strip()
        if not stripped or stripped.startswith('%') or stripped.startswith(';'):
            return True, None

        # Normalize line for execution
        line = self._normalize_line(original_line)

        try:
            if line.startswith('#'):
                return self._execute_variable_assignment(line)

            elif line.startswith('IF'):
                return self._execute_if_goto(line)

            elif line.startswith('WHILE'):
                return self._execute_while_do(line)

            elif line.startswith('GOTO'):
                return self._execute_goto(line)

            elif line.startswith(('G65', 'G66', 'G67', 'M97', 'M98', 'M99')):
                return self._execute_macro_call(line)

            elif line.startswith('G'):
                return self._execute_gcode(line)

            else:
                # Unknown line - skip gracefully for now
                return True, None

        except Exception as e:
            error_msg = f"Line {self.line_number}: {str(e)}"
            self.state.last_error = error_msg
            return False, error_msg

    def _normalize_line(self, line: str) -> str:
        """Normalize line for execution while preserving comments"""
        # Preserve comments exactly
        comment_match = re.search(r'\(.*?\)', line)
        comment = comment_match.group(0) if comment_match else ""

        # Remove comment for processing
        clean = re.sub(r'\(.*?\)', '', line).strip()

        # Uppercase G/M codes and add leading zero for decimals
        clean = re.sub(r'(G|M)(\d+)', lambda m: m.group(1) + m.group(2).zfill(2), clean)
        clean = re.sub(r'\.(\d)', r'0.\1', clean)

        return clean + (" " + comment if comment else "")

    def _execute_variable_assignment(self, line: str) -> Tuple[bool, Optional[str]]:
        """Handle variable assignment with math, trig, rounding"""
        try:
            if '(' in line:
                line = re.sub(r'\(.*?\)', '', line).strip()

            if '=' not in line:
                return False, "Missing '=' in assignment"

            left, right = [part.strip() for part in line.split('=', 1)]

            if not left.startswith('#'):
                return False, "Left side must be a variable (#xxx)"

            value = self._evaluate_expression(right)
            self.state.set_variable(left, value)

            # Live update in Variable Map (safely)
            try:
                main_window = self.editor.window() if hasattr(self, 'editor') else None
                if main_window and hasattr(main_window, 'variable_map_widget'):
                    vm = main_window.variable_map_widget
                    friendly = next((f for f, r in vm.mappings.items() if r == left), None)
                    if friendly:
                        vm.highlight_mapping(friendly)
                    else:
                        vm.highlight_mapping(left)
            except:
                pass  # Don't crash simulation if UI update fails

            print(f"  → Assigned {left} = {value:.4f}")
            return True, None

        except Exception as e:
            return False, f"Assignment error: {str(e)}"

    def _evaluate_expression(self, expr: str) -> float:
        """Safe evaluator with aggressive decimal fixing"""
        if not expr:
            raise ValueError("Empty expression")

        # Replace variables first
        expr = self._replace_variables_in_expression(expr)

        # Replace [ ] with ( )
        expr = expr.replace('[', '(').replace(']', ')')

        # === Aggressive decimal fix ===
        # Turn .125 into 0.125, .5 into 0.5, etc.
        expr = re.sub(r'(?<![\d.])\.(\d+)', r'0.\1', expr)

        safe_dict = {
            "SIN": lambda x: __import__("math").sin(x),
            "COS": lambda x: __import__("math").cos(x),
            "TAN": lambda x: __import__("math").tan(x),
            "ATAN": lambda x: __import__("math").atan(x),
            "SQRT": lambda x: __import__("math").sqrt(x),
            "ABS": abs,
            "ROUND": round,
            "FIX": lambda x: int(x) if x >= 0 else int(x) - 1 if x % 1 != 0 else int(x),
            "FUP": lambda x: int(x) + 1 if x % 1 != 0 else int(x),
        }

        try:
            result = eval(expr, {"__builtins__": {}}, safe_dict)
            return float(result)
        except Exception as e:
            raise ValueError(f"Cannot evaluate '{expr}': {e}")

    def _replace_variables_in_expression(self, expr: str) -> str:
        """Replace both raw and friendly variables with their current values"""
        # Replace friendly names first
        for friendly, value in self.state.friendly_map.items():
            expr = re.sub(rf'\b{friendly}\b', str(value), expr, flags=re.IGNORECASE)

        # Replace raw variables
        for var, value in self.state.variables.items():
            expr = re.sub(rf'\b{var}\b', str(value), expr)

        return expr

    def _execute_gcode(self, line: str) -> Tuple[bool, Optional[str]]:
        """Handle G00, G01, G02, G03 with feed safety and basic arc validation"""
        try:
            # Very basic parsing for now
            parts = line.split()
            if not parts:
                return True, None

            gcode = parts[0]
            if not gcode.startswith('G'):
                return True, None

            g_num = int(gcode[1:])

            # G00 - Rapid (no feed required)
            if g_num == 0:
                # Update position (simplified - we'll expand later)
                self._update_position_from_gcode(parts)
                return True, None

            # G01, G02, G03 - Feed moves
            if g_num in (1, 2, 3):
                if self.state.current_feed <= 0:
                    return False, f"G0{g_num} used without feed rate set (use F or assign feed variable)"

                # Basic arc validation for G02/G03
                if g_num in (2, 3):
                    if not any(p.startswith(('I', 'J', 'K', 'R')) for p in parts):
                        return False, f"G0{g_num} missing arc parameters (I/J/K or R)"

                self._update_position_from_gcode(parts)
                return True, None

            # Other G codes - skip for now
            return True, None

        except Exception as e:
            return False, f"G-code error: {str(e)}"

    def _update_position_from_gcode(self, parts: list):
        """Simple position update from G-code parts (expand later)"""
        for p in parts:
            if p.startswith('X'):
                try:
                    self.state.position['X'] = float(p[1:])
                except:
                    pass
            elif p.startswith('Y'):
                try:
                    self.state.position['Y'] = float(p[1:])
                except:
                    pass
            elif p.startswith('Z'):
                try:
                    self.state.position['Z'] = float(p[1:])
                except:
                    pass

    def _execute_gcode(self, line: str) -> Tuple[bool, Optional[str]]:
        """Handle G00, G01, G02, G03 and canned cycles with validation"""
        try:
            parts = line.split()
            if not parts:
                return True, None

            gcode = parts[0]
            if not gcode.startswith('G'):
                return True, None

            g_num = int(gcode[1:])

            # === Group 1 Motion ===
            if g_num in (0, 1, 2, 3):
                if g_num in (1, 2, 3) and self.state.current_feed <= 0:
                    return False, f"G0{g_num} used without feed rate set"

                if g_num in (2, 3):
                    if not any(p.startswith(('I', 'J', 'K', 'R')) for p in parts):
                        return False, f"G0{g_num} missing arc parameters (I/J/K or R)"

                self._update_position_from_gcode(parts)
                return True, None

            # === Canned Cycles (G81-G89, G13, etc.) ===
            if 81 <= g_num <= 89 or g_num == 13:
                # Check for variables in P or Q blocks - not allowed on most controls
                for p in parts:
                    if (p.startswith('P') or p.startswith('Q')) and '#' in p:
                        return False, f"Canned cycle G{g_num:02d} cannot use variables in P or Q parameters"

                print(f"Canned cycle G{g_num:02d} detected - basic validation passed")
                return True, None

            # Other G codes - skip for now
            return True, None

        except Exception as e:
            return False, f"G-code error: {str(e)}"

    def _execute_if_goto(self, line: str) -> Tuple[bool, Optional[str]]:
        """Handle IF [condition] GOTO Nxxx"""
        try:
            # Very basic parsing - we'll expand with real condition evaluation later
            if "GOTO" in line.upper():
                print(f"IF/GOTO detected: {line}")
                # TODO: evaluate condition and jump to line number
            return True, None
        except Exception as e:
            return False, f"IF/GOTO error: {str(e)}"

    def _execute_while_do(self, line: str) -> Tuple[bool, Optional[str]]:
        """Handle WHILE [condition] DO1 ... END1"""
        try:
            if "WHILE" in line.upper() and "DO1" in line.upper():
                print(f"WHILE/DO1 detected: {line}")
                # TODO: push loop state to call stack and evaluate condition
            return True, None
        except Exception as e:
            return False, f"WHILE/DO1 error: {str(e)}"

    def _execute_goto(self, line: str) -> Tuple[bool, Optional[str]]:
        """Handle GOTO Nxxx"""
        try:
            print(f"GOTO detected: {line}")
            # TODO: jump to line number
            return True, None
        except Exception as e:
            return False, f"GOTO error: {str(e)}"

    def _execute_macro_call(self, line: str) -> Tuple[bool, Optional[str]]:
        """Handle G65, G66, G67, M97, M98, M99"""
        try:
            upper = line.upper()
            if any(cmd in upper for cmd in ["G65", "G66", "G67", "M97", "M98", "M99"]):
                print(f"Macro call detected: {line}")
                # TODO: handle subprogram calls and modal G66
            return True, None
        except Exception as e:
            return False, f"Macro call error: {str(e)}"
        
    def _execute_goto(self, line: str) -> Tuple[bool, Optional[str]]:
        """Handle GOTO Nxxx"""
        try:
            print("GOTO detected - jump logic coming soon")
            return True, None
        except Exception as e:
            return False, f"GOTO error: {str(e)}" 

