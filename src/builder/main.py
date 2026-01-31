import os
import sys
import argparse

from gamuLogger import Logger, config_argparse, config_logger

from .project import Project
from .interactive_shell import InteractiveShell
        
def main():
    argparser = argparse.ArgumentParser(description='Build automation tool.')
    argparser.add_argument('--config', '-c', type=str, default="build.yml", help='Path to the build configuration file (YAML format).')
    argparser.add_argument('rules', nargs='*', help='Specific rules to execute. If none provided, all rules will be executed. Support regular expressions.')
    argparser.add_argument('--tag', '-t', action='append', help='Execute only rules with the specified tag(s).')
    argparser.add_argument('--no-run', action='store_true', help='Load the project and display the selected rules without executing them.')
    argparser.add_argument('--variable', '-D', action='append', help='Define a variable, two formats are allowed: NAME=VALUE, or NAME, in which case VALUE is taken from the environment variable NAME (not that this cause VALUE to be empty if NAME is not defined in the environment).', default=[])
    argparser.add_argument('--force-reload', '--force', '-f', action='store_true', help='Force reloading of all files, ignoring any caches.')
    argparser.add_argument('--interactive', '-i', action='store_true', help='Run in interactive mode.')
    config_argparse(argparser)
    
    args = argparser.parse_args()
    config_logger(args)
    
    rules_patterns = args.rules if args.rules else []
    tags = args.tag if args.tag else []
    
    variables : dict[str, str] = {}
    for var_def in args.variable:
        if '=' in var_def:
            name, value = var_def.split('=', 1)
        else:
            name = var_def
            value = os.environ.get(name, '')
        variables[name] = value
        Logger.debug(f'Defined variable from command line: {name}={value}')
    
    try:
        project = Project(args.config, variables)
    except Exception as e:
        Logger.fatal(f'Failed to load project: {e}')
        sys.exit(1)
        
        
    rules = project.select_rules(rules_patterns, tags)
        
    if args.interactive:
        shell = InteractiveShell(project)
        shell.cmdloop()
        sys.exit(0)
        
    if args.no_run:
        Logger.info('Selected rules:')
        for name, rule in rules.items():
            Logger.info(f' - {name}')
        sys.exit(0)
        
    try:
        project.run(rules, force=args.force_reload)
    except Exception as e:
        Logger.fatal(f'Build failed: {e}')
        sys.exit(1)