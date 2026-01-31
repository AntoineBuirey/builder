import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, call
from io import StringIO

from builder.main import main


@pytest.fixture
def mock_args():
    """Create mock arguments."""
    args = Mock()
    args.config = 'build.yml'
    args.rules = []
    args.tag = None
    args.no_run = False
    args.variable = []
    args.force_reload = False
    args.interactive = False
    args.log_level = 'INFO'
    args.log_file = None
    return args


@pytest.fixture
def mock_project():
    """Create a mock Project instance."""
    project = Mock()
    project.select_rules = Mock(return_value={})
    project.run = Mock()
    project.get_all_rules = Mock(return_value={})
    project.get_all_vars = Mock(return_value={})
    return project


@pytest.fixture
def mock_rules():
    """Create mock rules."""
    rule1 = Mock()
    rule1.name = 'build'
    rule2 = Mock()
    rule2.name = 'test'
    return {'build': rule1, 'test': rule2}


class TestMainArgumentParsing:
    """Tests for argument parsing in main function."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.InteractiveShell')
    @patch('sys.exit')
    def test_default_config_file(self, mock_exit, mock_shell, mock_project_class, 
                                 mock_config_argparse, mock_config_logger, mock_argparser):
        """Test default config file is 'build.yml'."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        args.log_level = 'INFO'
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify ArgumentParser was created with proper description
        mock_argparser.assert_called_once()
        assert 'Build automation tool' in mock_argparser.call_args[1]['description']
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_parse_config_argument(self, mock_exit, mock_project_class, mock_config_argparse,
                                    mock_config_logger, mock_argparser):
        """Test config argument is parsed."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'custom/build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify Project was created with custom config
        mock_project_class.assert_called_once()
        assert 'custom/build.yml' in mock_project_class.call_args[0]
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_parse_rule_arguments(self, mock_exit, mock_project_class, mock_config_argparse,
                                   mock_config_logger, mock_argparser):
        """Test rule names are parsed."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = ['build', 'test']
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify select_rules was called with rule patterns
        project_instance.select_rules.assert_called_once_with(['build', 'test'], [])
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_parse_tag_arguments(self, mock_exit, mock_project_class, mock_config_argparse,
                                  mock_config_logger, mock_argparser):
        """Test tag arguments are parsed."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = ['build', 'release']
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify select_rules was called with tags
        project_instance.select_rules.assert_called_once_with([], ['build', 'release'])


class TestVariableParsing:
    """Tests for variable parsing from command line."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('sys.exit')
    def test_parse_variable_with_equals(self, mock_exit, mock_logger, mock_project_class,
                                        mock_config_argparse, mock_config_logger, mock_argparser):
        """Test parsing variable with NAME=VALUE format."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = ['BUILD_DIR=build', 'VERSION=1.0.0']
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify Project was called with parsed variables
        call_args = mock_project_class.call_args
        variables = call_args[0][1]
        assert variables['BUILD_DIR'] == 'build'
        assert variables['VERSION'] == '1.0.0'
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('builder.main.os.environ', {'PATH': '/usr/bin', 'HOME': '/root'})
    @patch('sys.exit')
    def test_parse_variable_from_environment(self, mock_exit, mock_logger, mock_project_class,
                                             mock_config_argparse, mock_config_logger, mock_argparser):
        """Test parsing variable from environment."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = ['PATH', 'HOME']
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify variables were read from environment
        call_args = mock_project_class.call_args
        variables = call_args[0][1]
        assert variables['PATH'] == '/usr/bin'
        assert variables['HOME'] == '/root'
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('builder.main.os.environ', {})
    @patch('sys.exit')
    def test_parse_variable_undefined_environment(self, mock_exit, mock_logger, mock_project_class,
                                                    mock_config_argparse, mock_config_logger, mock_argparser):
        """Test parsing variable from undefined environment."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = ['UNDEFINED_VAR']
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify undefined variable defaults to empty string
        call_args = mock_project_class.call_args
        variables = call_args[0][1]
        assert variables['UNDEFINED_VAR'] == ''


class TestProjectLoading:
    """Tests for project loading."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('sys.exit')
    def test_project_loading_success(self, mock_exit, mock_logger, mock_project_class,
                                     mock_config_argparse, mock_config_logger, mock_argparser):
        """Test successful project loading."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify Project was instantiated
        mock_project_class.assert_called_once()
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('sys.exit')
    def test_project_loading_failure(self, mock_exit, mock_logger, mock_project_class,
                                     mock_config_argparse, mock_config_logger, mock_argparser):
        """Test project loading failure."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        mock_project_class.side_effect = Exception("Config file not found")
        mock_exit.side_effect = SystemExit(1)
        
        with pytest.raises(SystemExit):
            main()
        
        # Verify exit was called with error code 1
        mock_exit.assert_called_with(1)
        mock_logger.fatal.assert_called()


class TestInteractiveMode:
    """Tests for interactive mode."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.InteractiveShell')
    @patch('sys.exit')
    def test_interactive_mode_enabled(self, mock_exit, mock_shell_class, mock_project_class,
                                      mock_config_argparse, mock_config_logger, mock_argparser):
        """Test interactive mode is enabled."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = True
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        mock_project_class.return_value = project_instance
        
        shell_instance = Mock()
        mock_shell_class.return_value = shell_instance
        mock_exit.side_effect = SystemExit(0)
        
        with pytest.raises(SystemExit):
            main()
        
        # Verify InteractiveShell was created and cmdloop was called
        mock_shell_class.assert_called_once_with(project_instance)
        shell_instance.cmdloop.assert_called_once()
        mock_exit.assert_called_with(0)
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.InteractiveShell')
    @patch('sys.exit')
    def test_interactive_mode_disabled(self, mock_exit, mock_shell_class, mock_project_class,
                                       mock_config_argparse, mock_config_logger, mock_argparser):
        """Test interactive mode is not enabled."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        shell_instance = Mock()
        mock_shell_class.return_value = shell_instance
        
        main()
        
        # Verify InteractiveShell was not used
        mock_shell_class.assert_not_called()


class TestNoRunMode:
    """Tests for no-run mode."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('sys.exit')
    def test_no_run_mode_enabled(self, mock_exit, mock_logger, mock_project_class,
                                 mock_config_argparse, mock_config_logger, mock_argparser):
        """Test no-run mode displays rules without executing them."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = True
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        rule1 = Mock()
        rule1.name = 'build'
        rule2 = Mock()
        rule2.name = 'test'
        project_instance.select_rules = Mock(return_value={'build': rule1, 'test': rule2})
        mock_project_class.return_value = project_instance
        mock_exit.side_effect = SystemExit(0)
        
        with pytest.raises(SystemExit):
            main()
        
        # Verify Logger.info was called with selected rules
        mock_logger.info.assert_called()
        # Verify project.run was NOT called
        project_instance.run.assert_not_called()
        # Verify exit with code 0
        mock_exit.assert_called_with(0)
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('sys.exit')
    def test_no_run_mode_disabled(self, mock_exit, mock_logger, mock_project_class,
                                  mock_config_argparse, mock_config_logger, mock_argparser):
        """Test rules are executed when no-run is disabled."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        project_instance.run = Mock()
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify project.run was called
        project_instance.run.assert_called_once()


class TestRuleExecution:
    """Tests for rule execution."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_run_selected_rules(self, mock_exit, mock_project_class,
                                mock_config_argparse, mock_config_logger, mock_argparser):
        """Test selected rules are executed."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = ['build', 'test']
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        rule1 = Mock()
        rule1.name = 'build'
        rule2 = Mock()
        rule2.name = 'test'
        selected_rules = {'build': rule1, 'test': rule2}
        project_instance.select_rules = Mock(return_value=selected_rules)
        project_instance.run = Mock()
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify project.run was called with selected rules
        project_instance.run.assert_called_once_with(selected_rules, force=False)
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_run_with_force_reload(self, mock_exit, mock_project_class,
                                   mock_config_argparse, mock_config_logger, mock_argparser):
        """Test force reload flag is passed to project.run."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = True
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        project_instance.run = Mock()
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify project.run was called with force=True
        project_instance.run.assert_called_once_with({}, force=True)
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('sys.exit')
    def test_run_execution_failure(self, mock_exit, mock_logger, mock_project_class,
                                   mock_config_argparse, mock_config_logger, mock_argparser):
        """Test error handling when rule execution fails."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        project_instance.run = Mock(side_effect=Exception("Build failed"))
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify exit was called with error code 1
        mock_exit.assert_called_with(1)
        mock_logger.fatal.assert_called()


class TestLogging:
    """Tests for logging configuration."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_config_logger_called(self, mock_exit, mock_project_class,
                                  mock_config_argparse, mock_config_logger, mock_argparser):
        """Test config_logger is called."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify config_logger was called with parsed arguments
        mock_config_logger.assert_called_once_with(args)
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_config_argparse_called(self, mock_exit, mock_project_class,
                                    mock_config_argparse, mock_config_logger, mock_argparser):
        """Test config_argparse is called."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify config_argparse was called
        mock_config_argparse.assert_called_once()


class TestEdgeCases:
    """Tests for edge cases."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_no_rules_provided(self, mock_exit, mock_project_class,
                               mock_config_argparse, mock_config_logger, mock_argparser):
        """Test behavior when no rules are provided."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        project_instance.run = Mock()
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify select_rules was called with empty lists
        project_instance.select_rules.assert_called_once_with([], [])
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_multiple_tags(self, mock_exit, mock_project_class,
                           mock_config_argparse, mock_config_logger, mock_argparser):
        """Test multiple tags provided."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = ['build', 'test', 'release']
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        project_instance.run = Mock()
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify select_rules was called with all tags
        project_instance.select_rules.assert_called_once_with([], ['build', 'test', 'release'])
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_multiple_variables(self, mock_exit, mock_project_class,
                                mock_config_argparse, mock_config_logger, mock_argparser):
        """Test multiple variables provided."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = ['VAR1=value1', 'VAR2=value2', 'VAR3=value3']
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        project_instance.run = Mock()
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify all variables were passed
        call_args = mock_project_class.call_args
        variables = call_args[0][1]
        assert len(variables) == 3
        assert variables['VAR1'] == 'value1'
        assert variables['VAR2'] == 'value2'
        assert variables['VAR3'] == 'value3'
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_variable_with_equals_in_value(self, mock_exit, mock_project_class,
                                           mock_config_argparse, mock_config_logger, mock_argparser):
        """Test variable with equals sign in the value."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = ['EQUATION=x=y+z']
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        project_instance.run = Mock()
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify variable with multiple equals was parsed correctly (splits on first = only)
        call_args = mock_project_class.call_args
        variables = call_args[0][1]
        assert variables['EQUATION'] == 'x=y+z'


class TestIntegration:
    """Integration tests for main function."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('sys.exit')
    def test_full_workflow_with_variables_and_rules(self, mock_exit, mock_logger, mock_project_class,
                                                     mock_config_argparse, mock_config_logger, mock_argparser):
        """Test full workflow with variables and rules."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = ['build', 'test']
        args.tag = ['release']
        args.no_run = False
        args.variable = ['VERSION=2.0.0', 'BUILD_DIR=build']
        args.force_reload = True
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        rule1 = Mock()
        rule2 = Mock()
        project_instance.select_rules = Mock(return_value={'build': rule1, 'test': rule2})
        project_instance.run = Mock()
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify all components were called correctly
        mock_config_argparse.assert_called_once()
        mock_config_logger.assert_called_once()
        mock_project_class.assert_called_once()
        project_instance.select_rules.assert_called_once_with(['build', 'test'], ['release'])
        project_instance.run.assert_called_once()


class TestArgumentParserSetup:
    """Tests for argument parser setup."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_parser_has_config_argument(self, mock_exit, mock_project_class,
                                        mock_config_argparse, mock_config_logger, mock_argparser):
        """Test parser has config argument."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify add_argument was called with config
        assert parser_instance.add_argument.called
        calls = [str(call) for call in parser_instance.add_argument.call_args_list]
        config_calls = [call for call in calls if 'config' in call.lower()]
        assert len(config_calls) > 0
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('sys.exit')
    def test_parser_has_rules_argument(self, mock_exit, mock_project_class,
                                       mock_config_argparse, mock_config_logger, mock_argparser):
        """Test parser has rules argument."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        mock_project_class.return_value = project_instance
        
        main()
        
        # Verify add_argument was called
        assert parser_instance.add_argument.called


class TestErrorMessages:
    """Tests for error message handling."""
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('sys.exit')
    def test_project_loading_error_message(self, mock_exit, mock_logger, mock_project_class,
                                           mock_config_argparse, mock_config_logger, mock_argparser):
        """Test error message when project loading fails."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        error_message = "Config file not found: build.yml"
        mock_project_class.side_effect = Exception(error_message)
        mock_exit.side_effect = SystemExit(1)
        
        with pytest.raises(SystemExit):
            main()
        
        # Verify error was logged
        mock_logger.fatal.assert_called()
        call_args = mock_logger.fatal.call_args[0][0]
        assert "Failed to load project" in call_args
    
    @patch('builder.main.argparse.ArgumentParser')
    @patch('builder.main.config_logger')
    @patch('builder.main.config_argparse')
    @patch('builder.main.Project')
    @patch('builder.main.Logger')
    @patch('sys.exit')
    def test_build_execution_error_message(self, mock_exit, mock_logger, mock_project_class,
                                           mock_config_argparse, mock_config_logger, mock_argparser):
        """Test error message when build execution fails."""
        parser_instance = Mock()
        mock_argparser.return_value = parser_instance
        args = Mock()
        args.config = 'build.yml'
        args.rules = []
        args.tag = None
        args.no_run = False
        args.variable = []
        args.force_reload = False
        args.interactive = False
        parser_instance.parse_args.return_value = args
        
        project_instance = Mock()
        project_instance.select_rules = Mock(return_value={})
        error_message = "Compilation failed"
        project_instance.run = Mock(side_effect = Exception(error_message))
        mock_project_class.return_value = project_instance
        mock_exit.side_effect = SystemExit(1)
        
        with pytest.raises(SystemExit):
            main()
        
        # Verify error was logged
        mock_logger.fatal.assert_called()
        call_args = mock_logger.fatal.call_args[0][0]
        assert "Build failed" in call_args
