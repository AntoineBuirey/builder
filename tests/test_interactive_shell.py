# type: ignore[reportAttributeAccessIssue]import pytest

import pytest
import io
from unittest.mock import Mock
from contextlib import redirect_stdout, redirect_stderr

from builder.interactive_shell import InteractiveShell
from builder.rule import Rule


@pytest.fixture
def mock_project():
    """Create a mock Project instance."""
    project = Mock()
    project.get_all_rules = Mock(return_value={})
    project.get_all_vars = Mock(return_value={})
    project.vars = {}
    project.get_summary = Mock(return_value="Test Summary")
    return project


@pytest.fixture
def mock_rules():
    """Create mock Rule instances."""
    rules = {}
    
    # Create mock rule 1
    rule1 = Mock(spec=Rule)
    rule1.name = 'build'
    rule1.tags = ['build', 'compile']
    rule1.commands = ['gcc main.c']
    rule1.execute = Mock()
    rule1.get_summary = Mock(return_value="Build Rule Summary")
    rules['build'] = rule1
    
    # Create mock rule 2
    rule2 = Mock(spec=Rule)
    rule2.name = 'test'
    rule2.tags = ['test']
    rule2.commands = ['pytest', 'coverage']
    rule2.execute = Mock()
    rule2.get_summary = Mock(return_value="Test Rule Summary")
    rules['test'] = rule2
    
    return rules


@pytest.fixture
def mock_variables():
    """Create mock variables."""
    return {
        'BUILD_DIR': 'build',
        'SOURCE_DIR': 'src',
        'VERSION': '1.0.0',
        'DEBUG': True,
        'TIMEOUT': 30
    }


@pytest.fixture
def shell_with_rules(mock_project, mock_rules, mock_variables):
    """Create InteractiveShell with mocked rules and variables."""
    mock_project.get_all_rules = Mock(return_value=mock_rules)
    mock_project.get_all_vars = Mock(return_value=mock_variables)
    mock_project.vars = mock_variables
    return InteractiveShell(mock_project)


@pytest.fixture
def shell_empty(mock_project):
    """Create InteractiveShell with no rules."""
    mock_project.get_all_rules = Mock(return_value={})
    mock_project.get_all_vars = Mock(return_value={})
    mock_project.vars = {}
    return InteractiveShell(mock_project)


class TestInteractiveShellInit:
    """Tests for InteractiveShell initialization."""
    
    def test_init_with_project(self, mock_project):
        """Test initialization with a project."""
        shell = InteractiveShell(mock_project)
        
        assert shell.project == mock_project
        assert shell.rules_dict is not None
    
    def test_init_sets_prompt(self, mock_project):
        """Test that prompt is set correctly."""
        shell = InteractiveShell(mock_project)
        assert shell.prompt == "builder> "
    
    def test_init_sets_intro(self, mock_project):
        """Test that intro is set."""
        shell = InteractiveShell(mock_project)
        assert "Builder Interactive Shell" in shell.intro
    
    def test_init_populates_rules_dict(self, shell_with_rules, mock_rules):
        """Test that rules_dict is populated from project."""
        assert len(shell_with_rules.rules_dict) == len(mock_rules)
        assert 'build' in shell_with_rules.rules_dict
        assert 'test' in shell_with_rules.rules_dict


class TestDoList:
    """Tests for the list command."""
    
    def test_list_shows_rules(self, shell_with_rules):
        """Test that list command shows all rules."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_list("")
        
        result = output.getvalue()
        assert 'build' in result
        assert 'test' in result
    
    def test_list_shows_headers(self, shell_with_rules):
        """Test that list command shows column headers."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_list("")
        
        result = output.getvalue()
        assert 'Rule Name' in result
        assert 'Tags' in result
        assert 'Commands' in result
    
    def test_list_shows_tags(self, shell_with_rules):
        """Test that list command shows rule tags."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_list("")
        
        result = output.getvalue()
        assert 'build' in result
        assert 'test' in result
    
    def test_list_empty_rules(self, shell_empty):
        """Test list command with no rules."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_empty.do_list("")
        
        result = output.getvalue()
        assert "No rules available" in result
    
    def test_list_shows_command_count(self, shell_with_rules):
        """Test that list shows command count."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_list("")
        
        result = output.getvalue()
        # Should show command counts
        assert '1' in result or '2' in result


class TestDoRun:
    """Tests for the run command."""
    
    def test_run_single_rule(self, shell_with_rules):
        """Test running a single rule."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_run("build")
        
        shell_with_rules.rules_dict['build'].execute.assert_called_once()
    
    def test_run_multiple_rules(self, shell_with_rules):
        """Test running multiple rules."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_run("build test")
        
        shell_with_rules.rules_dict['build'].execute.assert_called_once()
        shell_with_rules.rules_dict['test'].execute.assert_called_once()
    
    def test_run_shows_rule_name(self, shell_with_rules):
        """Test that run command shows which rule is running."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_run("build")
        
        result = output.getvalue()
        assert 'build' in result
    
    def test_run_invalid_rule(self, shell_with_rules):
        """Test running a non-existent rule."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_run("nonexistent")
        
        result = output.getvalue()
        assert "Rule not found" in result or "not found" in result.lower()
    
    def test_run_no_args(self, shell_with_rules):
        """Test run command with no arguments."""
        output = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(output), redirect_stderr(stderr):
            shell_with_rules.do_run("")
        
        result = output.getvalue() + stderr.getvalue()
        assert "specify" in result.lower() or "usage" in result.lower()
    
    def test_run_handles_execution_error(self, shell_with_rules):
        """Test run command when rule execution fails."""
        shell_with_rules.rules_dict['build'].execute.side_effect = RuntimeError("Build failed")
        
        output = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(output), redirect_stderr(stderr):
            shell_with_rules.do_run("build")
        
        # Should handle the error gracefully


class TestDoInfo:
    """Tests for the info command."""
    
    def test_info_shows_summary(self, shell_with_rules):
        """Test that info command shows rule summary."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_info("build")
        
        result = output.getvalue()
        # Should call get_summary
        shell_with_rules.rules_dict['build'].get_summary.assert_called_once()
    
    def test_info_invalid_rule(self, shell_with_rules):
        """Test info command with invalid rule."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_info("nonexistent")
        
        result = output.getvalue()
        assert "Rule not found" in result or "not found" in result.lower()
    
    def test_info_no_args(self, shell_with_rules):
        """Test info command with no arguments."""
        output = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(output), redirect_stderr(stderr):
            shell_with_rules.do_info("")
        
        result = output.getvalue() + stderr.getvalue()
        assert "specify" in result.lower() or "usage" in result.lower()
    
    def test_info_shows_available_rules(self, shell_with_rules):
        """Test that info shows available rules when rule not found."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_info("invalid")
        
        result = output.getvalue()
        assert 'build' in result or 'test' in result


class TestDoVars:
    """Tests for the vars command."""
    
    def test_vars_shows_all_variables(self, shell_with_rules):
        """Test that vars command shows all variables."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_vars("")
        
        result = output.getvalue()
        assert 'BUILD_DIR' in result
        assert 'SOURCE_DIR' in result
        assert 'VERSION' in result
    
    def test_vars_shows_values(self, shell_with_rules):
        """Test that vars command shows variable values."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_vars("")
        
        result = output.getvalue()
        assert 'build' in result  # Value of BUILD_DIR
        assert '1.0.0' in result  # Value of VERSION
    
    def test_vars_single_variable(self, shell_with_rules):
        """Test vars command for a single variable."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_vars("BUILD_DIR")
        
        result = output.getvalue()
        assert 'BUILD_DIR' in result
        assert 'build' in result
    
    def test_vars_nonexistent_variable(self, shell_with_rules):
        """Test vars command with nonexistent variable."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_vars("NONEXISTENT")
        
        result = output.getvalue()
        assert "Variable not found" in result or "not found" in result.lower()
    
    def test_vars_empty(self, shell_empty):
        """Test vars command with no variables."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_empty.do_vars("")
        
        result = output.getvalue()
        assert "Project Variables" in result


class TestDoSummary:
    """Tests for the summary command."""
    
    def test_summary_shows_project_summary(self, shell_with_rules):
        """Test that summary command shows project summary."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_summary("")
        
        result = output.getvalue()
        assert "Test Summary" in result  # From mock
    
    def test_summary_calls_project_method(self, shell_with_rules):
        """Test that summary command calls project.get_summary()."""
        shell_with_rules.do_summary("")
        
        shell_with_rules.project.get_summary.assert_called()


class TestDoExit:
    """Tests for the exit command."""
    
    def test_exit_returns_true(self, shell_with_rules):
        """Test that exit command returns True."""
        output = io.StringIO()
        with redirect_stdout(output):
            result = shell_with_rules.do_exit("")
        
        assert result is True
    
    def test_exit_prints_goodbye(self, shell_with_rules):
        """Test that exit command prints goodbye."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_exit("")
        
        result = output.getvalue()
        assert "Goodbye" in result
    
    def test_quit_calls_exit(self, shell_with_rules):
        """Test that quit command calls exit."""
        output = io.StringIO()
        with redirect_stdout(output):
            result = shell_with_rules.do_quit("")
        
        assert result is True


class TestDefault:
    """Tests for the default command handler."""
    
    def test_default_unknown_command(self, shell_with_rules):
        """Test default handler with unknown command."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.default("unknown_command")
        
        result = output.getvalue()
        assert "Unknown command" in result
    
    def test_default_eof(self, shell_with_rules):
        """Test default handler with EOF."""
        output = io.StringIO()
        with redirect_stdout(output):
            result = shell_with_rules.default("EOF")
        
        # default returns result from do_exit, which returns True
        assert result is True or result is None
    
    def test_default_q(self, shell_with_rules):
        """Test default handler with 'q'."""
        output = io.StringIO()
        with redirect_stdout(output):
            result = shell_with_rules.default("q")
        
        # default returns result from do_exit, which returns True
        assert result is True or result is None
    
    def test_default_shows_help_hint(self, shell_with_rules):
        """Test that default shows help hint."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.default("invalid")
        
        result = output.getvalue()
        assert "help" in result.lower()


class TestEmptyline:
    """Tests for handling empty lines."""
    
    def test_emptyline_returns_false(self, shell_with_rules):
        """Test that emptyline returns False."""
        result = shell_with_rules.emptyline()
        assert result is False


class TestIntegration:
    """Integration tests combining multiple commands."""
    
    def test_workflow_list_then_run(self, shell_with_rules):
        """Test workflow: list rules then run one."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_list("")
            shell_with_rules.do_run("build")
        
        shell_with_rules.rules_dict['build'].execute.assert_called_once()
    
    def test_workflow_info_then_run(self, shell_with_rules):
        """Test workflow: show info then run rule."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_info("build")
            shell_with_rules.do_run("build")
        
        shell_with_rules.rules_dict['build'].execute.assert_called_once()
    
    def test_workflow_vars_then_run(self, shell_with_rules):
        """Test workflow: check vars then run rule."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_vars("BUILD_DIR")
            shell_with_rules.do_run("build")
        
        shell_with_rules.rules_dict['build'].execute.assert_called_once()


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_rule_with_no_tags(self, mock_project):
        """Test handling of rule with no tags."""
        rule = Mock(spec=Rule)
        rule.name = 'notags'
        rule.tags = []
        rule.commands = []
        rule.execute = Mock()
        
        mock_project.get_all_rules = Mock(return_value={'notags': rule})
        mock_project.get_all_vars = Mock(return_value={})
        
        shell = InteractiveShell(mock_project)
        output = io.StringIO()
        with redirect_stdout(output):
            shell.do_list("")
        
        result = output.getvalue()
        assert 'notags' in result
    
    def test_command_with_extra_spaces(self, shell_with_rules):
        """Test commands with extra spaces."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_run("  build  ")
        
        # Extra spaces are handled by split(), so command should still work
        shell_with_rules.rules_dict['build'].execute.assert_called_once()
    
    def test_variable_with_special_characters(self, mock_project):
        """Test variables with special characters in values."""
        mock_project.get_all_rules = Mock(return_value={})
        mock_project.get_all_vars = Mock(return_value={
            'COMMAND': 'echo "test | grep pattern"',
            'PATH': '/path/to/dir'
        })
        mock_project.vars = mock_project.get_all_vars()
        
        shell = InteractiveShell(mock_project)
        output = io.StringIO()
        with redirect_stdout(output):
            shell.do_vars("")
        
        result = output.getvalue()
        assert 'COMMAND' in result
    
    def test_very_long_rule_name(self, mock_project):
        """Test handling of very long rule names."""
        long_name = "very_long_rule_name_" * 5
        rule = Mock(spec=Rule)
        rule.name = long_name
        rule.tags = ['test']
        rule.commands = []
        rule.execute = Mock()
        
        mock_project.get_all_rules = Mock(return_value={long_name: rule})
        mock_project.get_all_vars = Mock(return_value={})
        
        shell = InteractiveShell(mock_project)
        output = io.StringIO()
        with redirect_stdout(output):
            shell.do_run(long_name)
        
        rule.execute.assert_called_once()
    
    def test_rule_execution_with_exception(self, shell_with_rules):
        """Test handling of rule execution exceptions."""
        shell_with_rules.rules_dict['build'].execute.side_effect = Exception("Build error")
        
        output = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(output), redirect_stderr(stderr):
            shell_with_rules.do_run("build")
        
        # Should handle exception gracefully


class TestUserInteraction:
    """Tests simulating user interaction patterns."""
    
    def test_multiple_commands_sequence(self, shell_with_rules):
        """Test sequence of multiple commands."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_list("")
            shell_with_rules.do_info("build")
            shell_with_rules.do_vars("BUILD_DIR")
            shell_with_rules.do_run("build")
            shell_with_rules.do_summary("")
        
        shell_with_rules.rules_dict['build'].execute.assert_called()
    
    def test_repeated_run_command(self, shell_with_rules):
        """Test running same rule multiple times."""
        shell_with_rules.do_run("build")
        shell_with_rules.do_run("build")
        shell_with_rules.do_run("build")
        
        assert shell_with_rules.rules_dict['build'].execute.call_count == 3


class TestOutputFormatting:
    """Tests for output formatting."""
    
    def test_list_output_alignment(self, shell_with_rules):
        """Test that list output is well-aligned."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_list("")
        
        result = output.getvalue()
        lines = result.split('\n')
        
        # Should have header, separator, and data lines
        assert len(lines) > 2
    
    def test_error_message_format(self, shell_with_rules):
        """Test error message formatting."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_run("nonexistent")
        
        result = output.getvalue()
        assert "not found" in result.lower() or "invalid" in result.lower()
    
    def test_vars_output_format(self, shell_with_rules):
        """Test variables output format."""
        output = io.StringIO()
        with redirect_stdout(output):
            shell_with_rules.do_vars("")
        
        result = output.getvalue()
        assert "Project Variables" in result
        assert "=" in result or ":" in result


class TestAttributesAndProperties:
    """Tests for class attributes and properties."""
    
    def test_project_attribute_set(self, shell_with_rules, mock_project):
        """Test that project attribute is properly set."""
        assert shell_with_rules.project == mock_project
    
    def test_rules_dict_attribute_set(self, shell_with_rules):
        """Test that rules_dict is properly initialized."""
        assert isinstance(shell_with_rules.rules_dict, dict)
        assert 'build' in shell_with_rules.rules_dict
    
    def test_prompt_attribute(self, shell_with_rules):
        """Test prompt attribute is correct."""
        assert isinstance(shell_with_rules.prompt, str)
        assert "builder" in shell_with_rules.prompt.lower()
    
    def test_intro_contains_welcome(self, shell_with_rules):
        """Test intro contains welcome message."""
        assert isinstance(shell_with_rules.intro, str)
        assert len(shell_with_rules.intro) > 0
