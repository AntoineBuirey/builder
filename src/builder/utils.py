import os
import glob
from typing import Iterable, Any
from gamuLogger import Logger

def get_max_edit_time(files: Iterable[str]) -> float:
    """Get the last edited time among an iterable of files."""
    return max(os.path.getmtime(f) for f in files if os.path.exists(f))

def files_exists(files: Iterable[str]) -> bool:
    """Check if all files in the iterable exist."""
    return all(os.path.exists(f) for f in files)

def is_pattern(s : str) -> bool:
    """Check if a string is a pattern (contains wildcard characters)."""
    return '*' in s or '?' in s or '[' in s

def apply_variables(value: str, variables: dict[str, Any]) -> str:
        """Apply variable substitution in a string."""
        for var, var_value in variables.items():
            Logger.trace(f"Substituting variable: {var} with value: {var_value}")
            value = value.replace(f"${{{var}}}", str(var_value))
        return value    

def expand_files(items: list[str]) -> list[str]:
        """Expand file patterns into actual file paths."""
        expanded_files = []
        for item in items:
            if is_pattern(item):
                matched_files = glob.glob(item, recursive=True)
                expanded_files.extend(matched_files)
                Logger.debug(f"Expanding pattern: {item} expanded to {len(matched_files)} files.")
                Logger.trace(matched_files)
            else:
                expanded_files.append(item)
                Logger.debug(f"Added file: {item}")
        Logger.debug(f"Total expanded files: {len(expanded_files)}")
        return expanded_files

def flatten(dic: dict[str, Any], parent_key: str = '', sep: str = '.') -> dict[str, Any]:
    """Flatten a nested dictionary."""
    items = {}
    for k, v in dic.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten(v, new_key, sep=sep))
        else:
            items[new_key] = v
    return items

def list2str(lst: list[Any]) -> str:
    """Convert a list to a comma-separated string (parseable by bash)."""
    return ', '.join(str(item) for item in lst)