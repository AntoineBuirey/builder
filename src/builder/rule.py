import os
import glob
from typing import Any
import subprocess as sp

from gamuLogger import Logger

def is_pattern(s : str) -> bool:
    """Check if a string is a pattern (contains wildcard characters)."""
    return '*' in s or '?' in s or '[' in s


class Rule:
    def __init__(self, name, config, variables: dict[str, Any] = {}, files_groups : dict[str, list[str]] = {}):
        self.name = name
        
        self.tags : list[str] = config.get('tags', [])
        
        Logger.debug(f"Initializing rule: {name}")
        
        required_files = config.get('required-files', [])
        if isinstance(required_files, str):
            required_files = files_groups.get(required_files, [])
        Logger.debug("Expanding required-files...")
        required_files = [self.__apply_variables(item, variables) for item in required_files]
        self.required_files = self.__expand_files(required_files)
        
        expected_files = config.get('expected-files', [])
        if isinstance(expected_files, str):
            expected_files = files_groups.get(expected_files, [])
        Logger.debug("Expanding expected-files...")
        expected_files = [self.__apply_variables(item, variables) for item in expected_files]
        self.expected_files = self.__expand_files(expected_files)
        
        commands = config.get('commands', [])
        Logger.debug("Applying variables to commands...")
        self.commands = [self.__apply_variables(cmd, variables) for cmd in commands]        
    
    
    def __repr__(self) -> str:
        return f"<Rule {self.name}: {len(self.required_files)} required files, {len(self.expected_files)} expected files, {len(self.commands)} commands>"
    

    def __apply_variables(self, value: str, variables: dict[str, Any]) -> str:
        """Apply variable substitution in a string."""
        for var, var_value in variables.items():
            Logger.trace(f"Substituting variable: {var} with value: {var_value}")
            value = value.replace(f"${{{var}}}", str(var_value))
        return value    
    
    
    def __expand_files(self, items: list[str]) -> list[str]:
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


    def get_summary(self) -> str:
        """Get a summary of the rule."""
        summary = f"Rule: {self.name}\n"
        summary += f"  Tags: {', '.join(self.tags)}\n"
        summary += f"  Required Files ({len(self.required_files)}):\n"
        for f in self.required_files:
            summary += f"    - {f}\n"
        summary += f"  Expected Files ({len(self.expected_files)}):\n"
        for f in self.expected_files:
            summary += f"    - {f}\n"
        summary += f"  Commands ({len(self.commands)}):\n"
        for cmd in self.commands:
            summary += f"    - {cmd}\n"
        return summary


    def __execute_commands(self):
        """Execute the commands defined in the rule."""

        for cmd in self.commands:
            Logger.debug(f'Executing command: \033[30m{cmd}\033[0m')
            try:
                result = sp.run(cmd, shell=True, check=True, text=True, stdout=sp.PIPE, stderr=sp.PIPE)
                Logger.debug(f'Command output:\n\033[32m{result.stdout.strip()}\033[0m')
            except sp.CalledProcessError as e:
                Logger.error(f'Command failed with return code {e.returncode}:\n\033[31m{e.stderr}\033[0m')
                raise RuntimeError(f'Command failed: {cmd}') from e
    
    def __check_required_files(self) -> bool:
        """Check if all required files are present."""
        missing_files = [f for f in self.required_files if not os.path.exists(f)]
        if missing_files:
            Logger.warning(f'Missing required files for rule {self.name}:')
            for f in missing_files:
                Logger.warning(f'  - {f}')
            return False
        Logger.debug(f'All required files are present for rule {self.name}.')
        return True
    

    def __check_expected_files(self) -> bool:
        """Check if all expected files are present."""
        missing_files = [f for f in self.expected_files if not os.path.exists(f)]
        if missing_files:
            Logger.warning(f'Missing expected files for rule {self.name}:\n\t- {'\n\t- '.join(missing_files)}')
            return False
        Logger.debug(f'All expected files are present for rule {self.name}.')
        return True
    
    
    def __get_last_edited_time_required(self) -> float:
        """Get the last edited time among required files."""
        return max(os.path.getmtime(f) for f in self.required_files if os.path.exists(f))
    
    def __get_last_edited_time_expected(self) -> float:
        """Get the last edited time among expected files."""
        return max(os.path.getmtime(f) for f in self.expected_files if os.path.exists(f))
    
    
    def __must_be_rerun(self) -> bool:
        """Determine if the rule must be re-executed based on file modification times."""
        if not self.expected_files or not all(os.path.exists(f) for f in self.expected_files):
            return True
        last_required = self.__get_last_edited_time_required()
        last_expected = self.__get_last_edited_time_expected()
        Logger.debug(f'Last required file edit time: {last_required}')
        Logger.debug(f'Last expected file edit time: {last_expected}')
        return last_required > last_expected
    
    
    def execute(self, force: bool = False):
        """Execute the rule: check required files, run commands, check expected files."""
        if not self.__check_required_files():
            raise RuntimeError(f'Cannot execute rule {self.name}: missing required files.')
        
        if not force and not self.__must_be_rerun():
            Logger.info(f'Rule {self.name} is up to date; skipping execution.')
            return
        
        self.__execute_commands()
        
        if not self.__check_expected_files():
            raise RuntimeError(f'Rule {self.name} execution failed: expected files not found.')
        Logger.info(f'Rule {self.name} executed successfully.')