# type: ignore[reportAttributeAccessIssue]
import pytest
from unittest.mock import MagicMock, patch, Mock
import subprocess as sp

from builder.command import Command, CommandExecutionError, CommandMetaData


class TestCommandExecute:
    """Tests for Command.execute() method."""

    @patch('builder.command.run_command')
    def test_execute_success_non_silent(self, mock_run_command):
        """Test successful command execution in non-silent mode."""
        mock_run_command.return_value = None
        
        cmd = Command('echo "test"')
        cmd.execute()
        
        mock_run_command.assert_called_once_with('echo "test"', True)

    @patch('builder.command.run_command')
    def test_execute_success_silent_mode(self, mock_run_command):
        """Test successful command execution in silent mode."""
        mock_run_command.return_value = None
        
        cmd = Command('+silent echo "test"')
        assert cmd.metadata.silent is True
        cmd.execute()
        
        # log parameter should be False (not silent = False)
        mock_run_command.assert_called_once_with('echo "test"', False)

    @patch('builder.command.Logger')
    @patch('builder.command.run_command')
    def test_execute_failure_raises_error(self, mock_run_command, mock_logger):
        """Test that failed command raises CommandExecutionError."""
        error = sp.CalledProcessError(1, 'false', stderr='Command failed')
        mock_run_command.side_effect = error
        
        cmd = Command('false')
        
        with pytest.raises(CommandExecutionError):
            cmd.execute()

    @patch('builder.command.Logger')
    @patch('builder.command.run_command')
    def test_execute_failure_non_silent_logs_generic_error(self, mock_run_command, mock_logger):
        """Test that non-silent mode logs generic error on failure."""
        error = sp.CalledProcessError(1, 'cmd', stderr='some error output')
        mock_run_command.side_effect = error
        
        cmd = Command('failing_cmd')
        assert cmd.metadata.silent is False
        
        with pytest.raises(CommandExecutionError):
            cmd.execute()
        
        # Should log error with return code
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        assert '1' in error_msg

    @patch('builder.command.Logger')
    @patch('builder.command.run_command')
    def test_execute_failure_silent_logs_stderr(self, mock_run_command, mock_logger):
        """Test that silent mode logs stderr on failure."""
        error = sp.CalledProcessError(2, 'cmd', stderr='detailed error output')
        mock_run_command.side_effect = error
        
        cmd = Command('+silent failing_cmd')
        assert cmd.metadata.silent is True
        
        with pytest.raises(CommandExecutionError):
            cmd.execute()
        
        # Should log error with return code and stderr
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        assert '2' in error_msg
        assert 'detailed error output' in error_msg

    @patch('builder.command.run_command')
    def test_execute_with_always_run_macro(self, mock_run_command):
        """Test execution with @always-run macro."""
        mock_run_command.return_value = None
        
        cmd = Command('+always ls -la')
        assert cmd.metadata.always_run is True
        assert cmd.command == 'ls -la'
        cmd.execute()
        
        mock_run_command.assert_called_once_with('ls -la', True)

    @patch('builder.command.run_command')
    def test_execute_with_both_macros(self, mock_run_command):
        """Test execution with both @always-run and @silent macros."""
        mock_run_command.return_value = None
        
        cmd = Command('+always +silent echo "test"')
        assert cmd.metadata.always_run is True
        assert cmd.metadata.silent is True
        assert cmd.command == 'echo "test"'
        cmd.execute()
        
        # Verify log=False is passed for silent mode
        mock_run_command.assert_called_once_with('echo "test"', False)

    @patch('builder.command.run_command')
    def test_execute_command_string_passed_correctly(self, mock_run_command):
        """Test that the correct command string is passed to run_command."""
        mock_run_command.return_value = None
        
        test_cmd = 'python script.py --arg value'
        cmd = Command(test_cmd)
        cmd.execute()
        
        # First argument should be the command
        called_cmd = mock_run_command.call_args[0][0]
        assert called_cmd == test_cmd

    @patch('builder.command.run_command')
    def test_execute_command_with_pipes(self, mock_run_command):
        """Test execution of command with pipes."""
        mock_run_command.return_value = None
        
        cmd = Command('cat file.txt | grep pattern')
        cmd.execute()
        
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args[0][0] == 'cat file.txt | grep pattern'

    @patch('builder.command.run_command')
    def test_execute_command_with_redirects(self, mock_run_command):
        """Test execution of command with output redirection."""
        mock_run_command.return_value = None
        
        cmd = Command('echo "test" > output.txt')
        cmd.execute()
        
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args[0][0] == 'echo "test" > output.txt'

    @patch('builder.command.Logger')
    @patch('builder.command.run_command')
    def test_execute_logs_debug_message(self, mock_run_command, mock_logger):
        """Test that debug message is logged before execution."""
        mock_run_command.return_value = None
        
        cmd = Command('test_command')
        cmd.execute()
        
        # Should log debug message with the command
        mock_logger.debug.assert_called_once()
        debug_msg = mock_logger.debug.call_args[0][0]
        assert 'test_command' in debug_msg

    @patch('builder.command.run_command')
    def test_execute_with_failure_code_1(self, mock_run_command):
        """Test execution with return code 1."""
        error = sp.CalledProcessError(1, 'cmd', stderr='')
        mock_run_command.side_effect = error
        
        cmd = Command('false')
        
        with pytest.raises(CommandExecutionError):
            cmd.execute()

    @patch('builder.command.run_command')
    def test_execute_with_failure_code_127(self, mock_run_command):
        """Test execution with return code 127 (command not found)."""
        error = sp.CalledProcessError(127, 'cmd', stderr='command not found')
        mock_run_command.side_effect = error
        
        cmd = Command('+silent nonexistent_command')
        
        with pytest.raises(CommandExecutionError):
            cmd.execute()

    @patch('builder.command.run_command')
    def test_execute_empty_command_string(self, mock_run_command):
        """Test execution with empty command after macro stripping."""
        mock_run_command.return_value = None
        
        cmd = Command('+always  +silent   ')
        # Command should be empty string after macro stripping
        assert cmd.command == ''
        cmd.execute()
        
        # Should still attempt to run
        mock_run_command.assert_called_once()
        assert mock_run_command.call_args[0][0] == ''

    @patch('builder.command.run_command')
    def test_execute_called_process_error_wrapping(self, mock_run_command):
        """Test that CalledProcessError is wrapped in CommandExecutionError."""
        original_error = sp.CalledProcessError(42, 'cmd', stderr='error')
        mock_run_command.side_effect = original_error
        
        cmd = Command('cmd')
        
        with pytest.raises(CommandExecutionError) as exc_info:
            cmd.execute()
        
        # Should have original error as cause
        assert exc_info.value.__cause__ is original_error

    @patch('builder.command.run_command')
    def test_execute_preserves_command_string(self, mock_run_command):
        """Test that execute doesn't modify the command attribute."""
        mock_run_command.return_value = None
        
        original_cmd = 'echo "preserve me"'
        cmd = Command(original_cmd)
        original_value = cmd.command
        
        cmd.execute()
        
        # Command should remain unchanged
        assert cmd.command == original_value

    @patch('builder.command.run_command')
    def test_execute_multiple_times(self, mock_run_command):
        """Test that command can be executed multiple times."""
        mock_run_command.return_value = None
        
        cmd = Command('echo test')
        cmd.execute()
        cmd.execute()
        cmd.execute()
        
        # Should be called 3 times
        assert mock_run_command.call_count == 3