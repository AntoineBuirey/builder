import yaml
import os
import sys
import subprocess as sp
import re
from typing import Any

from gamuLogger import Logger

from .rule import Rule
from .uses import load_project_file, is_project_file

from .utils import flatten, list2str



class Project:
    def __init__(self, config_file : str, cl_variables: dict[str, str] = {}):
        self.config_file = os.path.abspath(config_file)
        
        Logger.debug(f'Loading project configuration from: \033[33m{self.config_file}\033[0m')
        
        config = self.__load_config()
        
        project_dir = os.path.dirname(self.config_file)
        
        variables = { # Add default variables
            'PROJECT_DIR': project_dir,
            'PYTHON': sys.executable,
            'PLATFORM': sys.platform,
            'USER': os.getenv('USER', ''),
            'HOME_DIR': os.path.expanduser('~')
        }
        
        self.vars = {}
        self.imports : dict[str, Project] = {}
        
        imports_list = config.get('imports', [])
        
        Logger.debug(f'Loading {len(imports_list)} imports...')
        for imp in imports_list:
            path = imp['path']
            if not os.path.isabs(path):
                path = os.path.join(project_dir, path)
            path = os.path.normpath(path)
            if os.path.isdir(path):
                if os.path.exists(os.path.join(path, 'build.yml')):
                    path = os.path.join(path, 'build.yml')
                else:
                    raise ValueError(f'Import path is a directory but no build.yml found: {path}')
                
            Logger.debug(f'Loading file: \033[33m{path}\033[0m')
            if is_project_file(path):
                self.__load_config_file(imp, path)
            else:
                self.__load_sub_project(imp, path, cl_variables)

        self.vars.update(config.get('vars', {})) # variables from config file, can override pyproject.toml variables
        self.vars.update(variables) # builtin variables have priority over config file
        self.vars.update(cl_variables)  # Command line variables have highest priority
        self.__resolve_all_variables()
        
        self.files_groups = config.get('files-groups', {})
        
        rules = config.get('rules', {})
        self.rules : dict[str, Rule] = {}
        for name in rules:
            Logger.debug(f'Loading rule: \033[33m{name}\033[0m')
            self.rules[name] = Rule(name, rules[name], self.get_all_vars(), self.files_groups)
            
    def __load_config_file(self, imp: dict[str, str], path: str):
        data = load_project_file(path)
        as_name = imp.get('as', os.path.splitext(os.path.basename(path))[0]) # use filename without extension
        for key, value in flatten(data).items():
            key = f'{as_name}.{key}'
            if isinstance(value, list):
                value = list2str(value)
            elif isinstance(value, (str, int, float, bool)):
                value = str(value)
            else:
                Logger.debug(f'Skipping used data key: \033[33m{key}\033[0m (type: {type(value).__name__})')
                continue
                
            self.vars[key] = value
            Logger.debug(f'Stored used data key: \033[33m{key}\033[0m')
    
    def __load_sub_project(self, imp: dict[str, Any], path: str, cl_variables: dict[str, str]):
        project = Project(path, cl_variables)
        alias = imp.get('as', os.path.splitext(os.path.basename(path))[0])
        self.imports[alias] = project
        Logger.debug(f'Loaded import: \033[33m{path}\033[0m with alias: \033[33m{alias}\033[0m')
        
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
            for key, val in self.get_all_vars().items():
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
                    Logger.debug(f'Command output: \033[32m{result.strip()}\033[0m')
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
        for imp in self.imports.values():
            summary += imp.get_summary() + "\n"
        return summary
    
    def select_rules(self, names_patterns : list[str], tags : list[str]) -> dict[str, Rule]:
        """Select rules by names or tags."""
        selected_rules : dict[str, Rule] = {}
        for name, rule in self.get_all_rules().items():
            name_match = not names_patterns or any(re.fullmatch(pattern, name) for pattern in names_patterns)
            tag_match = not tags or any(tag in rule.tags for tag in tags)
            if name_match and tag_match:
                selected_rules[name] = rule
                Logger.debug(f'Selected rule: \033[33m{name}\033[0m')
        return selected_rules

    def run(self, rules : dict[str, Rule], force : bool = False):
        """Run the specified rules."""
        for name, rule in rules.items():
            Logger.info(f'Running rule: \033[33m{name}\033[0m')
            rule.execute(force)
        Logger.info('All done.')

    def get(self, name: str) -> Rule:
        """Get a rule or a variable by name. Support imported rules."""
        tokens = name.split('.', 1)
        if len(tokens) == 1:
            if name in self.rules:
                return self.rules[name]
            elif name in self.vars:
                return self.vars[name]
            else:
                raise KeyError(f'Rule not found: {name}')
        else:
            import_alias = tokens[0]
            rule_name = tokens[1]
            if import_alias in self.imports:
                import_obj = self.imports[import_alias]
                return import_obj.get(rule_name)
            else:
                raise KeyError(f'Import not found: {import_alias}')
            
    def get_rule(self, name: str) -> Rule:
        """Get a rule by name, including imported rules."""
        tokens = name.split('.', 1)
        if len(tokens) == 1:
            if name in self.rules:
                return self.rules[name]
            else:
                raise KeyError(f'Rule not found: {name}')
        else:
            import_alias = tokens[0]
            rule_name = tokens[1]
            if import_alias in self.imports:
                import_obj = self.imports[import_alias]
                return import_obj.get_rule(rule_name)
            else:
                raise KeyError(f'Import not found: {import_alias}')
            
    def get_var(self, name: str) -> str:
        """Get a variable by name, including imported variables."""
        tokens = name.split('.', 1)
        if len(tokens) == 1:
            if name in self.vars:
                return self.vars[name]
            else:
                raise KeyError(f'Variable not found: {name}')
        else:
            import_alias = tokens[0]
            var_name = tokens[1]
            if import_alias in self.imports:
                import_obj = self.imports[import_alias]
                return import_obj.get_var(var_name)
            else:
                raise KeyError(f'Import not found: {import_alias}')
    
    
    def get_all_vars(self) -> dict[str, str]:
        """Get all project variables, including imported ones."""
        all_vars = dict(self.vars)  # Start with local vars
        if not self.imports: # fail-fast
            return all_vars
        Logger.trace(f"Imports found: {list(self.imports.keys())}")
        for alias, import_obj in self.imports.items():
            imported_vars = import_obj.get_all_vars()
            imported_vars = {f'{alias}.{k}': v for k, v in imported_vars.items()}
            all_vars.update(imported_vars)
        return all_vars
    
    def get_all_rules(self) -> dict[str, Rule]:
        """Get all project rules, including imported ones."""
        all_rules = dict(self.rules)  # Start with local rules
        for alias, import_obj in self.imports.items():
            imported_rules = import_obj.get_all_rules()
            imported_rules = {f'{alias}.{k}': v for k, v in imported_rules.items()}
            all_rules.update(imported_rules)
        return all_rules

    