import sys
import argparse

from gamuLogger import Logger, config_argparse, config_logger

from .project import Project


def main():
    argparser = argparse.ArgumentParser(description='Build automation tool.')
    argparser.add_argument('config', type=str, default="build.yml", help='Path to the build configuration file (YAML format).')
    config_argparse(argparser)
    
    args = argparser.parse_args()
    config_logger(args)
    
    try:
        project = Project(args.config)
    except Exception as e:
        Logger.fatal(f'Failed to load project: {e}')
        sys.exit(1)
        
    try:
        project.run()
    except Exception as e:
        Logger.fatal(f'Build failed: {e}')
        sys.exit(1)