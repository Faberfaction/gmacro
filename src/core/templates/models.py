from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class Tool:
    """Represents a single tool in the machine's tool library."""
    tool_number: str                    # Full format e.g. "T01", "T0101", "T030303"
    offset_number: str = ""             # Offset used with G43 Hxx or Dxx (defaults to tool_number on mills)

    insert_name: str = ""
    nose_radius: float = 0.0            # lathe
    relief_angle: float = 0.0           # lathe
    diameter: float = 0.0               # mill
    corner_radius: float = 0.0          # mill
    helix_angle: float = 0.0            # mill
    flute_length: float = 0.0           # mill
    flute_count: int = 0                # mill

    length_offset: float = 0.0
    diameter_offset: float = 0.0
    wear_length_offset: float = 0.0
    wear_diameter_offset: float = 0.0

    type: str = "turning_insert"
    notes: str = ""


@dataclass
class LatheOptions:
    """Lathe-specific hardware options."""
    has_tailstock: bool = False
    has_subspindle: bool = False        # Often referred to as B-axis
    has_y_axis: bool = False            # Live tooling
    b_axis_max_z: Optional[float] = None   # Sub-spindle movement limit
    tailstock_max_z: Optional[float] = None


@dataclass
class MachineTemplate:
    """Complete machine definition used throughout the application."""
    machine_name: str
    control_type: str                   # "Haas Lathe", "Haas Mill", "Fanuc Mill", "Okuma Lathe", etc.
    default_units: str                  # "Imperial" or "Metric"

    axis_travel: Dict[str, float]
    max_rapid_ipm: float
    max_feed_ipm: float
    acceleration: Dict[str, float]
    spindle_max_rpm: int
    spindle_max_hp: float

    spindles: int = 1
    max_tools: int = 12

    lathe_options: Optional[LatheOptions] = None
    additional_axes: List[str] = field(default_factory=list)   # e.g. ["A", "B"] for 3+2 mills

    starter_tools: List[Tool] = field(default_factory=list)
    initial_modals: Dict[str, any] = field(default_factory=dict)

    tool_number_format: str = "T01"     # Hint for display