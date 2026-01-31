import os
from datetime import datetime
from typing import Any
import subprocess as sp

from gamuLogger import Logger

from .utils import get_max_edit_time, files_exists, apply_variables, expand_files


class Rule:
    def __init__(self, name, config, variables: dict[str, Any] = {}, files_groups : dict[str, list[str]] = {}):
        self.name = name
        
        self.tags : list[str] = config.get('tags', [])
        
        Logger.debug(f"Initializing rule: {name}")
        
        required_files = config.get('required-files', [])
        if isinstance(required_files, str):
            required_files = files_groups.get(required_files, [])
        Logger.debug(f"Expanding required-files for rule {name}...")
        required_files = [apply_variables(item, variables) for item in required_files]
        self.required_files = expand_files(required_files)
        
        expected_files = config.get('expected-files', [])
        if isinstance(expected_files, str):
            expected_files = files_groups.get(expected_files, [])
        Logger.debug(f"Expanding expected-files for rule {name}...")
        expected_files = [apply_variables(item, variables) for item in expected_files]
        self.expected_files = expand_files(expected_files)
        
        working_dir = config.get('working-directory', None)
        if working_dir:
            working_dir = apply_variables(working_dir, variables)
            Logger.debug(f"Setting working directory for rule {name} to: {working_dir}")
            self.working_directory = working_dir
        else:
            self.working_directory = variables['PROJECT_DIR']
        
        commands = config.get('commands', [])
        Logger.debug(f"Processing commands for rule {name}...")
        self.commands = [apply_variables(cmd, variables) for cmd in commands]        
    
    
    def __repr__(self) -> str:
        return f"<Rule {self.name}: {len(self.required_files)} required files, {len(self.expected_files)} expected files, {len(self.commands)} commands>"
    

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
        summary += f"  Working Directory: {self.working_directory}\n"
        summary += f"  Commands ({len(self.commands)}):\n"
        for cmd in self.commands:
            summary += f"    - {cmd}\n"
        return summary


    def __execute_commands(self):
        """Execute the commands defined in the rule."""

        Logger.info(f'Executing commands for rule {self.name}...')
        original_wd = os.getcwd()
        if self.working_directory:
            os.chdir(self.working_directory)
            Logger.debug(f'Changed working directory to: {self.working_directory}')

        try:
            for cmd in self.commands:
                Logger.debug(f'Executing command: \033[30m{cmd}\033[0m')
                try:
                    result = sp.run(cmd, shell=True, check=True, text=True, stdout=sp.PIPE, stderr=sp.PIPE)
                    Logger.debug(f'Command output:\033[32m\n{result.stdout.strip()}\033[0m')
                except sp.CalledProcessError as e:
                    Logger.error(f'Command failed with return code {e.returncode}:\033[31m\n{e.stderr.strip()}\033[0m')
                    raise RuntimeError(f'Command failed: {cmd}') from e
        finally:
            os.chdir(original_wd)
            Logger.debug(f'Restored working directory to: {original_wd}')


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
        return get_max_edit_time(self.required_files)


    def __get_last_edited_time_expected(self) -> float:
        """Get the last edited time among expected files."""
        return get_max_edit_time(self.expected_files)
    
    
    def __must_be_rerun(self) -> bool:
        """Determine if the rule must be re-executed based on file modification times."""
        if (not self.expected_files # the rule has no expected files, so we cannot check if it is up to date
        or not files_exists(self.expected_files)): # some expected files are missing
            return True
        last_required = self.__get_last_edited_time_required()
        last_expected = self.__get_last_edited_time_expected()
        dt_required = datetime.fromtimestamp(last_required)
        dt_expected = datetime.fromtimestamp(last_expected)
        Logger.debug(f'Last required file edit time: {dt_required.isoformat()}')
        Logger.debug(f'Last expected file edit time: {dt_expected.isoformat()}')
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