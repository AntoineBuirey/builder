import tomllib
import json
from typing import Any, Callable


FilesLoaders : dict[str, Callable[[str], dict[str, Any]]] = {
    'pyproject.toml': lambda path: __load_pyproject_toml(path),
    'package.json': lambda path: __load_package_json(path),
}


def __load_pyproject_toml(filepath) -> dict[str, Any]:
    """Load and parse pyproject.toml file."""
    with open(filepath, 'rb') as f:
        pyproject_data = tomllib.load(f)
        if not "project" in pyproject_data:
            raise ValueError("pyproject.toml does not contain a [project] section.")
    return pyproject_data["project"]

def __load_package_json(filepath) -> dict[str, Any]:
    """Load and parse package.json file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        package_data = json.load(f)
    return package_data

def load_project_file(filepath: str) -> dict[str, Any]:
    """Determine file type and load accordingly."""
    for filename, loader in FilesLoaders.items():
        if filepath.endswith(filename):
            return loader(filepath)
    raise ValueError(f"Unsupported file type for: {filepath}")

def is_project_file(filepath: str) -> bool:
    """Check if the given file is a supported project file."""
    return any(filepath.endswith(filename) for filename in FilesLoaders.keys())