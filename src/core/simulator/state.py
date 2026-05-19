from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.templates.models import MachineTemplate

@dataclass
class SimulatorState:
    """Holds all runtime state during macro execution."""
    template: MachineTemplate

    # Variables
    variables: Dict[str, float] = field(default_factory=dict)      # raw "#100" -> value
    friendly_map: Dict[str, str] = field(default_factory=dict)     # "PART_DIA" -> "#105"

    # Motion state
    position: Dict[str, float] = field(default_factory=lambda: {"X": 0.0, "Y": 0.0, "Z": 0.0})
    current_feed: float = 0.0
    current_spindle_rpm: float = 0.0

    # Modals
    modals: Dict[str, any] = field(default_factory=dict)

    # Control flow
    call_stack: List[int] = field(default_factory=list)
    program_counter: int = 0

    # Runtime status
    is_running: bool = False
    last_error: Optional[str] = None

    def set_variable(self, key: str, value: float):
        """Set a variable (supports both raw and friendly names)"""
        if key.startswith('#'):
            self.variables[key] = value
        else:
            # Store friendly name mapping
            self.friendly_map[key.upper()] = value
            # Also store under raw if we have a mapping
            if key.upper() in self.friendly_map:
                raw = self.friendly_map[key.upper()]
                self.variables[raw] = value

    def get_variable(self, key: str) -> float:
        """Get a variable value (supports friendly and raw)"""
        if key.startswith('#'):
            return self.variables.get(key, 0.0)
        else:
            # Look up friendly name
            friendly = key.upper()
            if friendly in self.friendly_map:
                raw = self.friendly_map[friendly]
                return self.variables.get(raw, 0.0)
            return 0.0

    def reset(self):
        """Reset simulation state"""
        self.variables.clear()
        self.friendly_map.clear()
        self.position = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        self.current_feed = 0.0
        self.current_spindle_rpm = 0.0
        self.modals.clear()
        self.call_stack.clear()
        self.program_counter = 0
        self.is_running = False
        self.last_error = None