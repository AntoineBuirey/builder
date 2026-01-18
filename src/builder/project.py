import yaml
import tomllib
import os
import sys
import subprocess as sp
from typing import Any

from gamuLogger import Logger
Logger.set_module('project')

from .rule import Rule


def load_pyproject_toml(filepath) -> dict[str, Any]:
    """Load and parse pyproject.toml file."""
    with open(filepath, 'rb') as f:
        pyproject_data = tomllib.load(f)
        if not "project" in pyproject_data:
            raise ValueError("pyproject.toml does not contain a [project] section.")
    return pyproject_data["project"]


class Project:
    def __init__(self, config_file : str):
        self.config_file = config_file
        config = self.__load_config()
        
        project_dir = os.path.dirname(config_file)
        pyproject_path = os.path.join(project_dir, 'pyproject.toml')
        
        variables = {
            'PROJECT_DIR': project_dir,
            'PYTHON': sys.executable
        }
        
        self.vars = load_pyproject_toml(pyproject_path)
        self.vars.update(config.get('vars', {}))
        self.vars.update(variables)
        self.__resolve_all_variables()
        
        self.files_groups = config.get('files-groups', {})
        
        rules = config.get('rules', {})
        self.rules : dict[str, Rule] = {}
        for name in rules:
            Logger.debug(f'Loading rule: \033[33m{name}\033[0m')
            self.rules[name] = Rule(name, rules[name], self.vars, self.files_groups)
        



    def __load_config(self):
        """Load configuration from a YAML file."""
        with open(self.config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config
    
    def __resolve_variable_value(self, value: str) -> str:
        """Resolve nested items in variable value
            - replace ${VAR} with the value of VAR
            - execute commands in $(command) and replace with output
        """
        last_value = ""
        while last_value != value:
            last_value = value
            # Substitute ${VAR}
            for key, val in self.vars.items():
                if not f'${{{key}}}' in value:
                    continue
                Logger.debug(f'Substituting \033[33m${{{key}}}\033[0m with \033[32m{val}\033[0m at:\n\033[30m{value}\033[0m')
                value = value.replace(f'${{{key}}}', str(val))
            # Expand $(command)
            while '$(' in value:
                start_idx = value.index('$(')
                end_idx = value.index(')', start_idx)
                command = value[start_idx + 2:end_idx]
                Logger.debug(f'Running command: \033[33m{command}\033[0m')
                try:
                    result = sp.check_output(command, shell=True, text=True, stderr=sp.PIPE).strip()
                    Logger.debug(f'Command output: \033[32m{result}\033[0m')
                    value = value[:start_idx] + result + value[end_idx + 1:]
                except sp.CalledProcessError as e:
                    Logger.error(f'{e}')
                    Logger.debug(e.stderr)
                    raise ValueError(f'Failed to execute command: {command}') from e
        return value
    
    def __resolve_all_variables(self):
        """Resolve all variables in self.vars."""
        def resolve_item(item):
            if isinstance(item, str):
                return self.__resolve_variable_value(item)
            elif isinstance(item, dict):
                return {k: resolve_item(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [resolve_item(i) for i in item]
            else:
                return item
        for key in self.vars:
            self.vars[key] = resolve_item(self.vars[key])


    def get_summary(self) -> str:
        """Get a summary of the project."""
        summary = f"Project Configuration from: {self.config_file}\n"
        summary += f"Variables:\n"
        for k, v in self.vars.items():
            summary += f"  {k}: {v}\n"
        summary += f"Rules ({len(self.rules)}):\n"
        for rule in self.rules.values():
            summary += rule.get_summary() + "\n"
        return summary
    

    def run(self):
        """Run all rules in the project."""
        for rule in self.rules.values():
            Logger.info(f'Running rule: \033[33m{rule.name}\033[0m')
            rule.execute()
        Logger.info('Project build completed successfully.')
