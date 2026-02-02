from dataclasses import dataclass
import subprocess as sp

from gamuLogger import Logger


@dataclass
class CommandMetaData:
    always_run: bool = False # If true, the command will always run regardless of failures in previous commands
    silent: bool = False     # If true, the command's output will be suppressed
    
def run_command(command: str, log: bool):
    process = sp.Popen(command, shell=True, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
    while process.poll() is None:
        if log:
            if process.stdout is not None:
                log_lines = process.stdout.readline().strip()
                for log_line in log_lines.splitlines():
                    Logger.info(log_line)
            if process.stderr is not None:
                err_lines = process.stderr.readline().strip()
                for err_line in err_lines.splitlines():
                    Logger.info(f"\033[31m{err_line}\033[0m")
    if log:
        if process.stdout is not None:
            logs = process.stdout.read().strip()
            for log_line in logs.splitlines():
                Logger.info(log_line)
        if process.stderr is not None:
            errs = process.stderr.read().strip()
            for err in errs.splitlines():
                Logger.info(f"\033[31m{err}\033[0m")
    if process.returncode != 0:
        stderr = process.stderr.read().strip() if process.stderr is not None else ''
        raise sp.CalledProcessError(process.returncode, command, stderr=stderr)
        
    

class CommandExecutionError(Exception):
    pass

class Command:
    def __init__(self, raw_command: str):
        self.metadata = CommandMetaData()
        
        cmd = raw_command.strip()
        nb_macros = 0
        for token in cmd.split():
            token = token.strip().lower()
            if not token.startswith('@'):
                break
            nb_macros += 1
            if token == '@always-run':
                Logger.trace(f'Found @always-run token in command: {cmd}')
                self.metadata.always_run = True
            elif token == '@silent':
                Logger.trace(f'Found @silent token in command: {cmd}')
                self.metadata.silent = True
            else:
                Logger.warning(f'Unknown preprocessor token in command: {token}. skipping.')
        
        self.command = ' '.join(cmd.split()[nb_macros:])
        
    def execute(self):
        Logger.debug(f'Executing command: \033[30m{self.command}\033[0m')
        try:
            run_command(self.command, not self.metadata.silent)
        except sp.CalledProcessError as e:
            if self.metadata.silent:
                Logger.error(f'Command failed with return code {e.returncode}:\033[31m\n{e.stderr.strip()}\033[0m')
            else:
                Logger.error(f'Command failed with return code {e.returncode}.')
            raise CommandExecutionError() from e