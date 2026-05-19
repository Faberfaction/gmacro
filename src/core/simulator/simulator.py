from typing import List, Tuple, Optional
from core.simulator.state import SimulatorState
from core.simulator.executor import Executor
from core.templates import MachineTemplate

class Simulator:
    def __init__(self, template: MachineTemplate):
        self.state = SimulatorState(template=template)
        self.executor = Executor(self.state)
        self.original_lines: List[str] = []   # store original lines for display

    def load_program(self, lines: List[str]):
        """Load a program (list of lines) for execution"""
        self.original_lines = lines.copy()
        self.state.program_counter = 0
        self.state.call_stack.clear()
        self.state.is_running = False

    def step(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute one line.
        Returns: (success, error_message, original_line)
        """
        if self.state.program_counter >= len(self.original_lines):
            return False, "End of program reached", None

        original_line = self.original_lines[self.state.program_counter]
        success, error = self.executor.execute_line(original_line)

        # Always move to next line unless a jump occurred
        if success and not error:
            self.state.program_counter += 1

        return success, error, original_line

    def run(self) -> List[Tuple[str, bool, Optional[str]]]:
        """Run the entire program (for testing)"""
        results = []
        self.state.is_running = True

        while self.state.program_counter < len(self.original_lines):
            success, error, line = self.step()
            results.append((line, success, error))
            if not success:
                break

        self.state.is_running = False
        return results

    def reset(self):
        """Reset simulator to initial state"""
        self.state.program_counter = 0
        self.state.call_stack.clear()
        self.state.is_running = False
        # Variables and modals remain (or we can clear them if desired)