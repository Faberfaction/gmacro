# MacroForge

A CNC macro simulation and development environment for Haas machines.

## Overview

MacroForge is a Python-based GUI application that allows users to:
- Write and debug CNC macro programs
- Create variable mappings for friendly naming
- Simulate macro execution step-by-step
- Visualize tool paths and machine movements
- Support multiple Haas machine configurations

## Features

- **Macro Editor** with syntax highlighting for G-code and macro variables
- **Variable Mapper** for creating friendly variable names (#DIA, #LENGTH, etc.)
- **Simulator** for step-through execution and debugging
- **Machine Templates** for different Haas machine types
- **Project Management** for saving and loading macro projects

## Installation

### Requirements
- Python 3.11+
- PySide6

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/gmacro.git
cd gmacro

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install PySide6

# Run the application
python main.py
```

## Project Structure

```
gmacro/
├── main.py              # Application entry point
├── src/
│   ├── constants.py     # Global constants and patterns
│   ├── core/
│   │   ├── templates/   # Machine templates and models
│   │   └── simulator/   # Simulation engine
│   └── gui/
│       ├── editor/      # Macro editor and syntax highlighting
│       ├── main_window.py
│       ├── variable_map/  # Variable mapping widget
│       ├── backplot/    # Tool path visualization
│       └── wizards/     # Project creation wizard
```

## Usage

1. **Create a New Project** - Use the wizard to set up a project with your machine template
2. **Write Macros** - Edit G-code and macros in the editor
3. **Create Variables** - Use the variable mapper to define friendly names
4. **Simulate** - Step through execution to debug your macros
5. **Save** - Projects are saved with variable mappings

## Development

### Running from Source

The application uses a modular architecture:
- `SimulationController` - Manages program execution
- `MacroEditor` - Syntax highlighting and code editing
- `VariableMapWidget` - Variable mapping UI
- `MacroHighlighter` - PySide6 syntax highlighter

## License

TBD

## Author

Created as a tool for CNC macro development and education.
