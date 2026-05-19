from PySide6.QtCore import QTimer

from .state import SimulatorState
from .executor import Executor

class SimulationController:
    def __init__(self, editor, template):
        self.editor = editor
        self.template = template
        
        self.state = SimulatorState(template)
        self.executor = Executor(self.state)

        self.is_running = False
        self.speed = 100  # percentage (100 = normal)
        self.timer = QTimer()
        self.timer.timeout.connect(self._auto_step)

        self.current_line = 0
        self.lines = []

    def load_program(self, code: str):
        """Load program lines from the editor"""
        self.lines = [line.strip() for line in code.split('\n') if line.strip()]
        self.current_line = 0
        self.state.reset()

    def step(self):
        """Execute one line (manual step)"""
        print(f"DEBUG: Current line index = {self.current_line}, Total lines = {len(self.lines)}")
        
        if self.current_line >= len(self.lines):
            print("DEBUG: End of program reached (or no lines loaded)")
            self.stop()
            return False, "End of program"

        line = self.lines[self.current_line]
        print(f"DEBUG: Stepping line {self.current_line + 1}: {line}")

        success, error = self.executor.execute_line(line)

        if success:
            self.editor.highlight_line(self.current_line)
            self.current_line += 1
            print(f"DEBUG: Successfully stepped to line {self.current_line}")
            return True, None
        else:
            self.stop()
            print(f"DEBUG: Error at line {self.current_line + 1}: {error}")
            return False, error

    def run(self):
        """Start continuous running"""
        if self.is_running:
            return
        self.is_running = True
        interval = max(10, int(1000 / (self.speed / 50)))
        self.timer.start(interval)

    def stop(self):
        """Stop running"""
        self.is_running = False
        self.timer.stop()

    def reset(self):
        """Reset to beginning"""
        self.stop()
        self.current_line = 0
        self.state.reset()
        self.editor.highlight_line(0)

    def _auto_step(self):
        """Called by timer during Run mode"""
        success, error = self.step()
        if not success:
            self.stop()

    def set_speed(self, percent: int):
        """Set execution speed 10–200%"""
        self.speed = max(10, min(200, percent))
        if self.is_running:
            self.run()  # restart timer with new speed