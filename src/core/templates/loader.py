from pathlib import Path
import json
from typing import Dict, List, Optional

from .models import MachineTemplate, Tool, LatheOptions

class TemplateLoader:
    """
    Loads built-in machine templates (read-only) and manages custom templates.
    """

    def __init__(self):
        self._builtin_templates: Dict[str, MachineTemplate] = {}
        self._custom_templates: Dict[str, MachineTemplate] = {}
        self._load_builtin_templates()
        self.reload_custom_templates()

    def _load_builtin_templates(self):
        """Load all read-only built-in templates from the builtin folder."""
        builtin_dir = Path(__file__).parent / "builtin"
        if not builtin_dir.exists():
            print(f"Warning: Built-in templates directory not found: {builtin_dir}")
            return

        for json_file in builtin_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Convert nested dicts to dataclasses
                if "lathe_options" in data and data["lathe_options"]:
                    data["lathe_options"] = LatheOptions(**data["lathe_options"])
                
                starter_tools = []
                for tool_data in data.get("starter_tools", []):
                    starter_tools.append(Tool(**tool_data))
                data["starter_tools"] = starter_tools

                template = MachineTemplate(**data)
                self._builtin_templates[template.machine_name] = template

            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in built-in template {json_file.name}: {e}")
            except KeyError as e:
                print(f"Error: Missing required field in built-in template {json_file.name}: {e}")
            except Exception as e:
                print(f"Error: Failed to load built-in template {json_file.name}: {e}")

    def get_all_templates(self) -> List[MachineTemplate]:
        """Return all templates: built-in first, then custom."""
        return list(self._builtin_templates.values()) + list(self._custom_templates.values())

    def get_template_by_name(self, name: str) -> Optional[MachineTemplate]:
        """Get a template by exact machine name."""
        if name in self._builtin_templates:
            return self._builtin_templates[name]
        return self._custom_templates.get(name)

    def create_custom_template(self, template: MachineTemplate) -> bool:
        custom_dir = Path(__file__).parent / "custom"
        try:
            custom_dir.mkdir(exist_ok=True)
        except OSError as e:
            print(f"Error: Could not create custom templates directory: {e}")
            return False

        file_path = custom_dir / f"{template.machine_name.lower().replace(' ', '_')}.json"
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                data = template.__dict__.copy()
                if template.lathe_options:
                    data["lathe_options"] = template.lathe_options.__dict__
                data["starter_tools"] = [tool.__dict__ for tool in template.starter_tools]
                
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Reload so it's immediately available
            self.reload_custom_templates()
            return True
            
        except OSError as e:
            print(f"Error: Could not write custom template file {file_path}: {e}")
            return False
        except json.JSONEncodeError as e:
            print(f"Error: Could not serialize template data: {e}")
            return False
        except Exception as e:
            print(f"Error: Failed to save custom template: {e}")
            return False

    def reload_custom_templates(self):
            """Reload all custom templates from disk."""
            self._custom_templates.clear()
            custom_dir = Path(__file__).parent / "custom"
            if not custom_dir.exists():
                return

            for json_file in custom_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if "lathe_options" in data and data["lathe_options"]:
                        data["lathe_options"] = LatheOptions(**data["lathe_options"])
                    
                    starter_tools = [Tool(**tool_data) for tool_data in data.get("starter_tools", [])]
                    data["starter_tools"] = starter_tools

                    template = MachineTemplate(**data)
                    self._custom_templates[template.machine_name] = template

                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON in custom template {json_file.name}: {e}")
                except KeyError as e:
                    print(f"Error: Missing required field in custom template {json_file.name}: {e}")
                except Exception as e:
                    print(f"Error: Failed to load custom template {json_file.name}: {e}")

    def get_builtin_names(self) -> List[str]:
        """Return only built-in template names (for dropdown grouping)."""
        return list(self._builtin_templates.keys())

    def get_custom_names(self) -> List[str]:
        """Return only custom template names."""
        return list(self._custom_templates.keys())