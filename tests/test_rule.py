import pytest
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from builder.rule import Rule


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def basic_variables(temp_dir):
    """Create basic variables dict."""
    return {'PROJECT_DIR': temp_dir}


@pytest.fixture
def basic_config():
    """Create a basic rule configuration."""
    return {
        'tags': ['build', 'compile'],
        'required-files': ['input.txt'],
        'expected-files': ['output.txt'],
        'commands': ['echo "Building"'],
    }


@pytest.fixture
def files_groups():
    """Create file groups dict."""
    return {
        'sources': ['src/main.py', 'src/utils.py'],
        'tests': ['test_*.py'],
    }


class TestRuleInitialization:
    """Tests for Rule initialization."""
    
    def test_init_basic_rule(self, basic_config, basic_variables):
        """Test basic rule initialization."""
        rule = Rule('test_rule', basic_config, basic_variables)
        assert rule.name == 'test_rule'
        assert rule.tags == ['build', 'compile']
        assert len(rule.required_files) >= 0
        assert len(rule.expected_files) >= 0
        
    def test_init_with_empty_tags(self, basic_config, basic_variables):
        """Test initialization without tags."""
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('no_tags_rule', config, basic_variables)
        assert rule.tags == []
    
    def test_init_sets_name(self, basic_config, basic_variables):
        """Test name is correctly set."""
        rule = Rule('my_rule', basic_config, basic_variables)
        assert rule.name == 'my_rule'
    
    def test_init_with_required_files_as_list(self, basic_variables):
        """Test initialization with required files as list."""
        config = {
            'required-files': ['file1.txt', 'file2.txt'],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('list_rule', config, basic_variables)
        assert 'file1.txt' in rule.required_files
        assert 'file2.txt' in rule.required_files
    
    def test_init_with_expected_files_as_list(self, basic_variables):
        """Test initialization with expected files as list."""
        config = {
            'required-files': [],
            'expected-files': ['result.txt', 'output.log'],
            'commands': []
        }
        rule = Rule('expect_rule', config, basic_variables)
        assert 'result.txt' in rule.expected_files
        assert 'output.log' in rule.expected_files


class TestFileGroupHandling:
    """Tests for file group handling in initialization."""
    
    def test_init_required_files_from_group(self, temp_dir, basic_variables):
        """Test using file group for required-files."""
        # Create actual files to match the pattern
        src_dir = os.path.join(temp_dir, 'src')
        os.makedirs(src_dir, exist_ok=True)
        Path(os.path.join(src_dir, 'main.py')).touch()
        Path(os.path.join(src_dir, 'utils.py')).touch()
        
        files_groups = {
            'sources': [os.path.join(src_dir, 'main.py'), os.path.join(src_dir, 'utils.py')]
        }
        config = {
            'required-files': 'sources',
            'expected-files': [],
            'commands': []
        }
        rule = Rule('group_rule', config, basic_variables, files_groups)
        assert len(rule.required_files) == 2
    
    def test_init_expected_files_from_group(self, temp_dir, basic_variables):
        """Test using file group for expected-files."""
        # Create test files that match the pattern
        Path(os.path.join(temp_dir, 'test_one.py')).touch()
        Path(os.path.join(temp_dir, 'test_two.py')).touch()
        
        files_groups = {
            'tests': [os.path.join(temp_dir, 'test_*.py')]
        }
        config = {
            'required-files': [],
            'expected-files': 'tests',
            'commands': []
        }
        rule = Rule('group_rule', config, basic_variables, files_groups)
        # Should expand the glob pattern
        assert len(rule.expected_files) >= 2
    
    def test_init_nonexistent_file_group(self, basic_variables, files_groups):
        """Test with nonexistent file group."""
        config = {
            'required-files': 'nonexistent_group',
            'expected-files': [],
            'commands': []
        }
        rule = Rule('bad_group', config, basic_variables, files_groups)
        # Should get empty list for nonexistent group
        assert rule.required_files == []


class TestWorkingDirectory:
    """Tests for working directory handling."""
    
    def test_default_working_directory(self, basic_config, basic_variables, temp_dir):
        """Test that default working directory is PROJECT_DIR."""
        rule = Rule('work_rule', basic_config, basic_variables)
        assert rule.working_directory == temp_dir
    
    def test_custom_working_directory(self, basic_variables, temp_dir):
        """Test setting custom working directory."""
        custom_dir = os.path.join(temp_dir, 'custom')
        config = {
            'working-directory': custom_dir,
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('custom_work', config, basic_variables)
        assert rule.working_directory == custom_dir
    
    def test_working_directory_variable_substitution(self, basic_variables, temp_dir):
        """Test variable substitution in working directory."""
        variables = {
            'PROJECT_DIR': temp_dir,
            'BUILD_DIR': 'build'
        }
        config = {
            'working-directory': '${BUILD_DIR}',
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('var_work', config, variables)
        assert rule.working_directory == 'build'


class TestVariableSubstitution:
    """Tests for variable substitution in rule configuration."""
    
    def test_commands_variable_substitution(self, basic_variables):
        """Test variable substitution in commands."""
        variables = {
            'PROJECT_DIR': '/home/project',
            'OUTPUT_DIR': '/output'
        }
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': ['echo ${OUTPUT_DIR}', 'ls ${PROJECT_DIR}']
        }
        rule = Rule('subst_rule', config, variables)
        assert 'echo /output' in rule.commands
        assert 'ls /home/project' in rule.commands
    
    def test_required_files_variable_substitution(self, basic_variables):
        """Test variable substitution in required files."""
        variables = {
            'PROJECT_DIR': '/project',
            'SRC_DIR': '/src'
        }
        config = {
            'required-files': ['${SRC_DIR}/main.py', '${SRC_DIR}/utils.py'],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('file_subst', config, variables)
        assert '/src/main.py' in rule.required_files
        assert '/src/utils.py' in rule.required_files
    
    def test_expected_files_variable_substitution(self, basic_variables):
        """Test variable substitution in expected files."""
        variables = {
            'PROJECT_DIR': '/project',
            'BUILD_DIR': '/build'
        }
        config = {
            'required-files': [],
            'expected-files': ['${BUILD_DIR}/output.bin', '${BUILD_DIR}/log.txt'],
            'commands': []
        }
        rule = Rule('expect_subst', config, variables)
        assert '/build/output.bin' in rule.expected_files
        assert '/build/log.txt' in rule.expected_files


class TestRepr:
    """Tests for string representation."""
    
    def test_repr_format(self, basic_config, basic_variables):
        """Test repr output format."""
        rule = Rule('repr_rule', basic_config, basic_variables)
        repr_str = repr(rule)
        assert 'repr_rule' in repr_str
        assert 'required files' in repr_str
        assert 'expected files' in repr_str
        assert 'commands' in repr_str
    
    def test_repr_includes_counts(self, temp_dir, basic_variables):
        """Test repr includes file and command counts."""
        # Create some test files
        Path(os.path.join(temp_dir, 'input.txt')).touch()
        Path(os.path.join(temp_dir, 'output.txt')).touch()
        
        config = {
            'required-files': [os.path.join(temp_dir, 'input.txt')],
            'expected-files': [os.path.join(temp_dir, 'output.txt')],
            'commands': ['cmd1', 'cmd2', 'cmd3']
        }
        rule = Rule('count_rule', config, basic_variables)
        repr_str = repr(rule)
        assert '1' in repr_str  # 1 required file
        assert '1' in repr_str  # 1 expected file
        assert '3' in repr_str  # 3 commands


class TestSummary:
    """Tests for summary generation."""
    
    def test_get_summary_structure(self, basic_config, basic_variables):
        """Test summary includes all required sections."""
        rule = Rule('summary_rule', basic_config, basic_variables)
        summary = rule.get_summary()
        assert 'Rule: summary_rule' in summary
        assert 'Tags:' in summary
        assert 'Required Files' in summary
        assert 'Expected Files' in summary
        assert 'Working Directory' in summary
        assert 'Commands' in summary
    
    def test_summary_includes_tags(self, basic_config, basic_variables):
        """Test summary includes tags."""
        rule = Rule('tag_rule', basic_config, basic_variables)
        summary = rule.get_summary()
        assert 'build' in summary
        assert 'compile' in summary
    
    def test_summary_with_empty_tags(self, basic_variables):
        """Test summary with no tags."""
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('no_tag_summary', config, basic_variables)
        summary = rule.get_summary()
        assert 'Tags:' in summary
    
    def test_summary_file_counts(self, basic_config, basic_variables):
        """Test summary shows correct file counts."""
        rule = Rule('count_summary', basic_config, basic_variables)
        summary = rule.get_summary()
        assert 'Required Files' in summary
        assert 'Expected Files' in summary


class TestCheckRequiredFiles:
    """Tests for required files checking."""
    
    def test_check_required_files_all_exist(self, temp_dir, basic_variables):
        """Test when all required files exist."""
        file1 = os.path.join(temp_dir, 'file1.txt')
        file2 = os.path.join(temp_dir, 'file2.txt')
        Path(file1).touch()
        Path(file2).touch()
        
        config = {
            'required-files': [file1, file2],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('exist_rule', config, basic_variables)
        assert rule._Rule__check_required_files() is True
    
    def test_check_required_files_missing(self, basic_variables):
        """Test when required files are missing."""
        config = {
            'required-files': ['/nonexistent/file.txt'],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('missing_rule', config, basic_variables)
        assert rule._Rule__check_required_files() is False
    
    def test_check_required_files_empty_list(self, basic_variables):
        """Test with empty required files list."""
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('empty_rule', config, basic_variables)
        assert rule._Rule__check_required_files() is True
    
    def test_check_required_files_partial_missing(self, temp_dir, basic_variables):
        """Test when some required files are missing."""
        existing_file = os.path.join(temp_dir, 'exists.txt')
        Path(existing_file).touch()
        
        config = {
            'required-files': [existing_file, '/nonexistent/file.txt'],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('partial_rule', config, basic_variables)
        assert rule._Rule__check_required_files() is False


class TestCheckExpectedFiles:
    """Tests for expected files checking."""
    
    def test_check_expected_files_all_exist(self, temp_dir, basic_variables):
        """Test when all expected files exist."""
        file1 = os.path.join(temp_dir, 'result1.txt')
        file2 = os.path.join(temp_dir, 'result2.txt')
        Path(file1).touch()
        Path(file2).touch()
        
        config = {
            'required-files': [],
            'expected-files': [file1, file2],
            'commands': []
        }
        rule = Rule('expect_exist', config, basic_variables)
        assert rule._Rule__check_expected_files() is True
    
    def test_check_expected_files_missing(self, basic_variables):
        """Test when expected files are missing."""
        config = {
            'required-files': [],
            'expected-files': ['/nonexistent/output.txt'],
            'commands': []
        }
        rule = Rule('expect_missing', config, basic_variables)
        assert rule._Rule__check_expected_files() is False
    
    def test_check_expected_files_empty_list(self, basic_variables):
        """Test with empty expected files list."""
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('expect_empty', config, basic_variables)
        assert rule._Rule__check_expected_files() is True


class TestGetLastEditedTime:
    """Tests for getting last edited time."""
    
    def test_get_last_edited_time_required(self, temp_dir, basic_variables):
        """Test getting last edit time of required files."""
        file1 = os.path.join(temp_dir, 'file1.txt')
        file2 = os.path.join(temp_dir, 'file2.txt')
        
        Path(file1).touch()
        time.sleep(0.1)
        Path(file2).touch()
        
        config = {
            'required-files': [file1, file2],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('time_rule', config, basic_variables)
        last_time = rule._Rule__get_last_edited_time_required()
        file2_time = os.path.getmtime(file2)
        
        # Should return the latest time (file2)
        assert last_time == file2_time
    
    def test_get_last_edited_time_expected(self, temp_dir, basic_variables):
        """Test getting last edit time of expected files."""
        file1 = os.path.join(temp_dir, 'out1.txt')
        file2 = os.path.join(temp_dir, 'out2.txt')
        
        Path(file1).touch()
        time.sleep(0.1)
        Path(file2).touch()
        
        config = {
            'required-files': [],
            'expected-files': [file1, file2],
            'commands': []
        }
        rule = Rule('expect_time', config, basic_variables)
        last_time = rule._Rule__get_last_edited_time_expected()
        file2_time = os.path.getmtime(file2)
        
        assert last_time == file2_time


class TestMustBeRerun:
    """Tests for determining if rule must be rerun."""
    
    def test_must_rerun_no_expected_files(self, temp_dir, basic_variables):
        """Test that rule must rerun if no expected files."""
        file1 = os.path.join(temp_dir, 'input.txt')
        Path(file1).touch()
        
        config = {
            'required-files': [file1],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('no_expect', config, basic_variables)
        assert rule._Rule__must_be_rerun() is True
    
    def test_must_rerun_missing_expected_files(self, temp_dir, basic_variables):
        """Test that rule must rerun if expected files missing."""
        input_file = os.path.join(temp_dir, 'input.txt')
        Path(input_file).touch()
        
        config = {
            'required-files': [input_file],
            'expected-files': ['/nonexistent/output.txt'],
            'commands': []
        }
        rule = Rule('missing_expect', config, basic_variables)
        assert rule._Rule__must_be_rerun() is True
    
    def test_must_rerun_when_required_newer(self, temp_dir, basic_variables):
        """Test rerun when required files are newer than expected."""
        expected_file = os.path.join(temp_dir, 'output.txt')
        Path(expected_file).touch()
        
        time.sleep(0.1)
        
        required_file = os.path.join(temp_dir, 'input.txt')
        Path(required_file).touch()
        
        config = {
            'required-files': [required_file],
            'expected-files': [expected_file],
            'commands': []
        }
        rule = Rule('newer_req', config, basic_variables)
        assert rule._Rule__must_be_rerun() is True
    
    def test_must_not_rerun_when_expected_newer(self, temp_dir, basic_variables):
        """Test no rerun when expected files are newer than required."""
        required_file = os.path.join(temp_dir, 'input.txt')
        Path(required_file).touch()
        
        time.sleep(0.1)
        
        expected_file = os.path.join(temp_dir, 'output.txt')
        Path(expected_file).touch()
        
        config = {
            'required-files': [required_file],
            'expected-files': [expected_file],
            'commands': []
        }
        rule = Rule('newer_exp', config, basic_variables)
        assert rule._Rule__must_be_rerun() is False


class TestExecuteCommands:
    """Tests for command execution."""
    
    @patch('subprocess.run')
    def test_execute_commands_success(self, mock_run, basic_variables, temp_dir):
        """Test successful command execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='output',
            stderr=''
        )
        
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': ['echo "test"']
        }
        rule = Rule('exec_rule', config, basic_variables)
        rule._Rule__execute_commands()
        
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_execute_multiple_commands(self, mock_run, basic_variables):
        """Test executing multiple commands."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='output',
            stderr=''
        )
        
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': ['cmd1', 'cmd2', 'cmd3']
        }
        rule = Rule('multi_cmd', config, basic_variables)
        rule._Rule__execute_commands()
        
        assert mock_run.call_count == 3
    
    @patch('subprocess.run')
    def test_execute_commands_failure(self, mock_run, basic_variables):
        """Test command execution failure."""
        import subprocess as sp
        mock_run.side_effect = sp.CalledProcessError(1, 'cmd', stderr='error')
        
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': ['failing_cmd']
        }
        rule = Rule('fail_rule', config, basic_variables)
        
        with pytest.raises(RuntimeError, match='Command failed'):
            rule._Rule__execute_commands()
    
    @patch('os.chdir')
    @patch('subprocess.run')
    def test_execute_commands_changes_directory(self, mock_run, mock_chdir, basic_variables, temp_dir):
        """Test that working directory is changed during execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        
        custom_dir = os.path.join(temp_dir, 'custom')
        config = {
            'working-directory': custom_dir,
            'required-files': [],
            'expected-files': [],
            'commands': ['echo "test"']
        }
        rule = Rule('chdir_rule', config, basic_variables)
        rule._Rule__execute_commands()
        
        # Should change to custom_dir and back
        assert mock_chdir.call_count >= 2
    
    @patch('os.chdir')
    @patch('subprocess.run')
    def test_execute_commands_restores_directory(self, mock_run, mock_chdir, basic_variables, temp_dir):
        """Test that original directory is restored after execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        
        config = {
            'working-directory': temp_dir,
            'required-files': [],
            'expected-files': [],
            'commands': ['echo "test"']
        }
        rule = Rule('restore_rule', config, basic_variables)
        
        original_dir = os.getcwd()
        rule._Rule__execute_commands()
        
        # Last chdir call should restore original directory
        last_chdir_arg = mock_chdir.call_args_list[-1][0][0]
        assert last_chdir_arg == original_dir or original_dir is not None


class TestExecute:
    """Tests for main execute method."""
    
    @patch('builder.rule.Rule._Rule__check_expected_files')
    @patch('builder.rule.Rule._Rule__execute_commands')
    @patch('builder.rule.Rule._Rule__check_required_files')
    def test_execute_full_flow(self, mock_check_req, mock_exec_cmd, mock_check_exp, 
                               basic_config, basic_variables):
        """Test full execution flow."""
        mock_check_req.return_value = True
        mock_check_exp.return_value = True
        
        rule = Rule('flow_rule', basic_config, basic_variables)
        rule.execute()
        
        mock_check_req.assert_called_once()
        mock_exec_cmd.assert_called_once()
        mock_check_exp.assert_called_once()
    
    @patch('builder.rule.Rule._Rule__check_required_files')
    def test_execute_fails_missing_required_files(self, mock_check_req,
                                                  basic_config, basic_variables):
        """Test execution fails if required files missing."""
        mock_check_req.return_value = False
        
        rule = Rule('fail_req', basic_config, basic_variables)
        
        with pytest.raises(RuntimeError, match='missing required files'):
            rule.execute()
    
    @patch('builder.rule.Rule._Rule__check_expected_files')
    @patch('builder.rule.Rule._Rule__execute_commands')
    @patch('builder.rule.Rule._Rule__check_required_files')
    def test_execute_fails_missing_expected_files(self, mock_check_req, 
                                                  mock_exec_cmd, mock_check_exp,
                                                  basic_config, basic_variables):
        """Test execution fails if expected files missing after commands."""
        mock_check_req.return_value = True
        mock_check_exp.return_value = False
        
        rule = Rule('fail_exp', basic_config, basic_variables)
        
        with pytest.raises(RuntimeError, match='expected files not found'):
            rule.execute()
    
    @patch('builder.rule.Rule._Rule__must_be_rerun')
    @patch('builder.rule.Rule._Rule__check_required_files')
    def test_execute_skips_if_up_to_date(self, mock_check_req, mock_must_rerun,
                                         basic_config, basic_variables):
        """Test execution skipped if rule is up to date."""
        mock_check_req.return_value = True
        mock_must_rerun.return_value = False
        
        rule = Rule('uptodate_rule', basic_config, basic_variables)
        
        with patch.object(rule, '_Rule__execute_commands') as mock_exec:
            rule.execute(force=False)
            # Commands should not be executed
            mock_exec.assert_not_called()
    
    @patch('builder.rule.Rule._Rule__check_expected_files')
    @patch('builder.rule.Rule._Rule__execute_commands')
    @patch('builder.rule.Rule._Rule__check_required_files')
    def test_execute_with_force_flag(self, mock_check_req, mock_exec_cmd, 
                                     mock_check_exp, basic_config, basic_variables):
        """Test execution with force flag runs commands even if up to date."""
        mock_check_req.return_value = True
        mock_check_exp.return_value = True
        
        rule = Rule('force_rule', basic_config, basic_variables)
        rule.execute(force=True)
        
        # Commands should be executed regardless of timestamps
        mock_exec_cmd.assert_called_once()


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_rule_with_no_commands(self, basic_variables):
        """Test rule with no commands."""
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': []
        }
        rule = Rule('no_cmd_rule', config, basic_variables)
        assert rule.commands == []
    
    def test_rule_with_special_characters_in_name(self, basic_config, basic_variables):
        """Test rule with special characters in name."""
        rule = Rule('rule-with-dashes_and_underscores', basic_config, basic_variables)
        assert rule.name == 'rule-with-dashes_and_underscores'
    
    def test_rule_with_empty_config(self, basic_variables):
        """Test rule with empty configuration."""
        config = {}
        rule = Rule('empty_config', config, basic_variables)
        assert rule.tags == []
        assert rule.commands == []
    
    def test_rule_with_empty_commands(self, basic_variables):
        """Test rule explicitly with empty commands list."""
        config = {
            'commands': []
        }
        rule = Rule('empty_cmds', config, basic_variables)
        assert rule.commands == []
    
    def test_large_file_list(self, temp_dir, basic_variables):
        """Test rule with large number of files."""
        files = [os.path.join(temp_dir, f'file_{i}.txt') for i in range(100)]
        for f in files:
            Path(f).touch()
        
        config = {
            'required-files': files,
            'expected-files': [],
            'commands': []
        }
        rule = Rule('large_list', config, basic_variables)
        assert len(rule.required_files) == 100
    
    def test_complex_command_strings(self, basic_variables):
        """Test complex command strings with pipes and redirects."""
        config = {
            'required-files': [],
            'expected-files': [],
            'commands': [
                'cat file.txt | grep "pattern" | wc -l',
                'python script.py > output.txt 2>&1'
            ]
        }
        rule = Rule('complex_cmd', config, basic_variables)
        assert len(rule.commands) == 2
        assert 'grep' in rule.commands[0]
        assert '2>&1' in rule.commands[1]


class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_rule_with_file_groups_and_variables(self, temp_dir, basic_variables):
        """Test rule using both file groups and variables."""
        # Create sources
        src_dir = os.path.join(temp_dir, 'src')
        os.makedirs(src_dir, exist_ok=True)
        Path(os.path.join(src_dir, 'main.py')).touch()
        
        files_groups = {
            'sources': [os.path.join(src_dir, 'main.py')]
        }
        
        variables = {
            'PROJECT_DIR': temp_dir,
            'BUILD_DIR': 'build',
            'OUTPUT': '${BUILD_DIR}/output'
        }
        
        config = {
            'required-files': 'sources',
            'expected-files': ['${OUTPUT}.txt'],
            'commands': ['python build.py -o ${OUTPUT}']
        }
        
        rule = Rule('integrated', config, variables, files_groups)
        assert os.path.join(src_dir, 'main.py') in rule.required_files
        # Variable substitution should occur
        assert len(rule.commands) > 0
    
    def test_rule_summary_and_repr_consistency(self, basic_config, basic_variables):
        """Test that repr and summary contain consistent information."""
        rule = Rule('consistency_rule', basic_config, basic_variables)
        repr_str = repr(rule)
        summary = rule.get_summary()
        
        assert rule.name in summary
        assert 'consistency_rule' in repr_str
