import pytest
import os
import subprocess as sp
from unittest.mock import Mock, patch

from builder.rule import Rule, is_pattern


class TestIsPattern:
    """Tests for the is_pattern helper function."""
    
    def test_asterisk_is_pattern(self):
        assert is_pattern("*.py") is True
        assert is_pattern("test_*.txt") is True
    
    def test_question_mark_is_pattern(self):
        assert is_pattern("file?.py") is True
    
    def test_bracket_is_pattern(self):
        assert is_pattern("file[123].py") is True
    
    def test_no_pattern(self):
        assert is_pattern("file.py") is False
        assert is_pattern("simple_filename.txt") is False
    
    def test_empty_string(self):
        assert is_pattern("") is False


class TestRuleInit:
    """Tests for Rule initialization."""
    
    def test_basic_initialization(self):
        config = {
            'tags': ['test'],
            'required-files': ['file1.txt'],
            'expected-files': ['output.txt'],
            'commands': ['echo "test"']
        }
        rule = Rule('test_rule', config)
        
        assert rule.name == 'test_rule'
        assert rule.tags == ['test']
        assert len(rule.commands) == 1
    
    def test_initialization_with_variables(self):
        config = {
            'required-files': ['${INPUT_FILE}'],
            'expected-files': ['${OUTPUT_FILE}'],
            'commands': ['process ${INPUT_FILE}']
        }
        variables = {
            'INPUT_FILE': 'input.txt',
            'OUTPUT_FILE': 'output.txt'
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config, variables)
        
        assert 'input.txt' in rule.required_files
        assert 'output.txt' in rule.expected_files
        assert rule.commands[0] == 'process input.txt'
    
    def test_initialization_with_files_groups(self):
        config = {
            'required-files': 'source_files',
            'expected-files': 'output_files',
            'commands': []
        }
        files_groups = {
            'source_files': ['src/file1.py', 'src/file2.py'],
            'output_files': ['dist/output.js']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config, files_groups=files_groups)
        
        assert 'src/file1.py' in rule.required_files
        assert 'src/file2.py' in rule.required_files
        assert 'dist/output.js' in rule.expected_files
    
    def test_initialization_with_pattern_expansion(self):
        config = {
            'required-files': ['src/*.py'],
            'expected-files': [],
            'commands': []
        }
        
        with patch('builder.rule.glob.glob', return_value=['src/file1.py', 'src/file2.py']):
            rule = Rule('test_rule', config)
        
        assert len(rule.required_files) == 2
        assert 'src/file1.py' in rule.required_files
        assert 'src/file2.py' in rule.required_files
    
    def test_default_tags_empty(self):
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        
        rule = Rule('test_rule', config)
        assert rule.tags == []


class TestRuleSummary:
    """Tests for Rule.get_summary method."""
    
    def test_summary_contains_rule_name(self):
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('my_rule', config)
        summary = rule.get_summary()
        
        assert 'my_rule' in summary
    
    def test_summary_contains_tags(self):
        config = {
            'tags': ['build', 'compile'],
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('my_rule', config)
        summary = rule.get_summary()
        
        assert 'build' in summary
        assert 'compile' in summary
    
    def test_summary_contains_files_and_commands(self):
        config = {
            'required-files': ['input.txt'],
            'expected-files': ['output.txt'],
            'commands': ['process input.txt']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('my_rule', config)
        
        summary = rule.get_summary()
        assert 'input.txt' in summary
        assert 'output.txt' in summary
        assert 'process input.txt' in summary


class TestRuleExecution:
    """Tests for Rule.execute method."""
    
    def test_execute_with_missing_required_files(self):
        config = {
            'required-files': ['nonexistent.txt'],
            'expected-files': [],
            'commands': ['echo "test"']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config)
        
        with pytest.raises(RuntimeError, match='missing required files'):
            rule.execute()
    
    def test_execute_skips_when_up_to_date(self, tmp_path):
        # Create temporary files
        required_file = tmp_path / "input.txt"
        expected_file = tmp_path / "output.txt"
        
        required_file.write_text("input")
        expected_file.write_text("output")
        
        # Make expected file newer
        os.utime(expected_file, (os.path.getatime(expected_file), 
                                  os.path.getmtime(required_file) + 10))
        
        config = {
            'required-files': [str(required_file)],
            'expected-files': [str(expected_file)],
            'commands': ['echo "should not run"']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config)
        
        with patch('builder.rule.sp.run') as mock_run:
            rule.execute()
            mock_run.assert_not_called()
    
    def test_execute_runs_when_required_files_newer(self, tmp_path):
        # Create temporary files
        required_file = tmp_path / "input.txt"
        expected_file = tmp_path / "output.txt"
        
        required_file.write_text("input")
        expected_file.write_text("output")
        
        # Make required file newer
        os.utime(required_file, (os.path.getatime(required_file), 
                                  os.path.getmtime(expected_file) + 10))
        
        config = {
            'required-files': [str(required_file)],
            'expected-files': [str(expected_file)],
            'commands': ['echo "test"']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config)
        
        mock_result = Mock()
        mock_result.stdout = "test"
        mock_result.stderr = ""
        
        with patch('builder.rule.sp.run', return_value=mock_result) as mock_run:
            rule.execute()
            mock_run.assert_called_once()
    
    def test_execute_runs_when_expected_files_missing(self, tmp_path):
        required_file = tmp_path / "input.txt"
        required_file.write_text("input")
        
        config = {
            'required-files': [str(required_file)],
            'expected-files': [str(tmp_path / "nonexistent.txt")],
            'commands': ['echo "test"']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config)
        
        mock_result = Mock()
        mock_result.stdout = "test"
        mock_result.stderr = ""
        
        with patch('builder.rule.sp.run', return_value=mock_result) as mock_run:
            with pytest.raises(RuntimeError, match='expected files not found'):
                rule.execute()
            mock_run.assert_called_once()
    
    def test_execute_command_failure(self, tmp_path):
        required_file = tmp_path / "input.txt"
        required_file.write_text("input")
        
        config = {
            'required-files': [str(required_file)],
            'expected-files': [],
            'commands': ['failing_command']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config)
        
        with patch('builder.rule.sp.run', side_effect=sp.CalledProcessError(1, 'failing_command', stderr='error')):
            with pytest.raises(RuntimeError, match='Command failed'):
                rule.execute()
    
    def test_execute_multiple_commands(self, tmp_path):
        required_file = tmp_path / "input.txt"
        expected_file = tmp_path / "output.txt"
        
        required_file.write_text("input")
        expected_file.write_text("output")
        
        # Make required file newer to trigger execution
        os.utime(required_file, (os.path.getatime(required_file), 
                                  os.path.getmtime(expected_file) + 10))
        
        config = {
            'required-files': [str(required_file)],
            'expected-files': [str(expected_file)],
            'commands': ['echo "cmd1"', 'echo "cmd2"', 'echo "cmd3"']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config)
        
        mock_result = Mock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        
        with patch('builder.rule.sp.run', return_value=mock_result) as mock_run:
            rule.execute()
            assert mock_run.call_count == 3
    
    def test_execute_with_no_expected_files(self, tmp_path):
        required_file = tmp_path / "input.txt"
        required_file.write_text("input")
        
        config = {
            'required-files': [str(required_file)],
            'expected-files': [],
            'commands': ['echo "test"']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config)
        
        mock_result = Mock()
        mock_result.stdout = "test"
        mock_result.stderr = ""
        
        with patch('builder.rule.sp.run', return_value=mock_result) as mock_run:
            rule.execute()
            mock_run.assert_called_once()


class TestRuleRepr:
    """Tests for Rule.__repr__ method."""
    
    def test_repr_format(self):
        config = {
            'required-files': ['file1.txt', 'file2.txt'],
            'expected-files': ['output.txt'],
            'commands': ['echo "test"', 'echo "test2"']
        }
        
        with patch('builder.rule.glob.glob', return_value=[]):
            rule = Rule('test_rule', config)
        
        repr_str = repr(rule)
        assert 'test_rule' in repr_str
        assert '2 required files' in repr_str
        assert '1 expected files' in repr_str
        assert '2 commands' in repr_str
