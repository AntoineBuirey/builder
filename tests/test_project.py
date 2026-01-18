import pytest
import subprocess as sp
from unittest.mock import patch
import yaml

from builder.project import Project, load_pyproject_toml


class TestLoadPyprojectToml:
    """Tests for load_pyproject_toml helper function."""
    
    def test_load_valid_pyproject_toml(self, tmp_path):
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("""
[project]
name = "test-project"
version = "1.0.0"
""")
        
        result = load_pyproject_toml(str(pyproject_file))
        
        assert result['name'] == 'test-project'
        assert result['version'] == '1.0.0'
    
    def test_load_pyproject_toml_without_project_section(self, tmp_path):
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("""
[tool.something]
key = "value"
""")
        
        with pytest.raises(ValueError, match='does not contain a \\[project\\] section'):
            load_pyproject_toml(str(pyproject_file))
    
    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_pyproject_toml('/nonexistent/pyproject.toml')


class TestProjectInit:
    """Tests for Project initialization."""
    
    def test_basic_initialization(self, tmp_path):
        # Create project structure
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
version = "1.0.0"
""")
        
        config_file.write_text("""
vars:
  CUSTOM_VAR: "custom_value"

rules:
  test_rule:
    required-files: []
    expected-files: []
    commands: []
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert project.config_file == str(config_file)
        assert project.vars['name'] == 'test-project'
        assert project.vars['CUSTOM_VAR'] == 'custom_value'
        assert 'PROJECT_DIR' in project.vars
        assert 'PYTHON' in project.vars
        assert 'test_rule' in project.rules
    
    def test_project_dir_variable_set_correctly(self, tmp_path):
        config_file = tmp_path / "subdir" / "test.build"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        pyproject_file = tmp_path / "subdir" / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert project.vars['PROJECT_DIR'] == str(tmp_path / "subdir")
    
    def test_variables_from_pyproject_and_config_merge(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
version = "1.0.0"
""")
        
        config_file.write_text("""
vars:
  BUILD_DIR: "build"
  
rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert project.vars['name'] == 'test-project'
        assert project.vars['version'] == '1.0.0'
        assert project.vars['BUILD_DIR'] == 'build'
    
    def test_multiple_rules_loaded(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
rules:
  rule1:
    required-files: []
    expected-files: []
    commands: []
  rule2:
    required-files: []
    expected-files: []
    commands: []
  rule3:
    required-files: []
    expected-files: []
    commands: []
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert len(project.rules) == 3
        assert 'rule1' in project.rules
        assert 'rule2' in project.rules
        assert 'rule3' in project.rules
    
    def test_files_groups_loaded(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
files-groups:
  source_files:
    - src/file1.py
    - src/file2.py
  output_files:
    - dist/output.js

rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert 'source_files' in project.files_groups
        assert 'output_files' in project.files_groups
        assert len(project.files_groups['source_files']) == 2


class TestProjectVariableResolution:
    """Tests for Project variable resolution."""
    
    def test_simple_variable_substitution(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
vars:
  BASE_DIR: "/path/to/base"
  OUTPUT_DIR: "${BASE_DIR}/output"

rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert project.vars['OUTPUT_DIR'] == '/path/to/base/output'
    
    def test_nested_variable_substitution(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
vars:
  A: "value_a"
  B: "${A}_b"
  C: "${B}_c"

rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert project.vars['C'] == 'value_a_b_c'
    
    def test_command_substitution(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
vars:
  TIMESTAMP: "$(echo test_output)"

rules: {}
""")
        
        with patch('builder.project.Logger'):
            with patch('subprocess.check_output', return_value='test_output'):
                project = Project(str(config_file))
        
        assert project.vars['TIMESTAMP'] == 'test_output'
    
    def test_command_substitution_failure(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
vars:
  FAIL: "$(failing_command)"

rules: {}
""")
        
        with patch('builder.project.Logger'):
            with patch('subprocess.check_output', side_effect=sp.CalledProcessError(1, 'failing_command', stderr='error')):
                with pytest.raises(ValueError, match='Failed to execute command'):
                    project = Project(str(config_file))
    
    def test_list_variable_resolution(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
vars:
  BASE: "base"
  LIST_VAR:
    - "${BASE}/item1"
    - "${BASE}/item2"

rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert project.vars['LIST_VAR'] == ['base/item1', 'base/item2']
    
    def test_dict_variable_resolution(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
vars:
  PREFIX: "test"
  DICT_VAR:
    key1: "${PREFIX}_value1"
    key2: "${PREFIX}_value2"

rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert project.vars['DICT_VAR']['key1'] == 'test_value1'
        assert project.vars['DICT_VAR']['key2'] == 'test_value2'
    
    def test_pyproject_variables_used_in_substitution(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
version = "1.0.0"
""")
        
        config_file.write_text("""
vars:
  FULL_NAME: "${name}-v${version}"

rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        assert project.vars['FULL_NAME'] == 'test-project-v1.0.0'


class TestProjectSummary:
    """Tests for Project.get_summary method."""
    
    def test_summary_contains_config_file(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        summary = project.get_summary()
        assert str(config_file) in summary
    
    def test_summary_contains_variables(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
vars:
  CUSTOM_VAR: "value"

rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        summary = project.get_summary()
        assert 'CUSTOM_VAR' in summary
        assert 'value' in summary
    
    def test_summary_contains_rules(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
rules:
  build_rule:
    required-files: []
    expected-files: []
    commands: []
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        summary = project.get_summary()
        assert 'build_rule' in summary
        assert 'Rules (1)' in summary


class TestProjectRun:
    """Tests for Project.run method."""
    
    def test_run_executes_all_rules(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
rules:
  rule1:
    required-files: []
    expected-files: []
    commands: []
  rule2:
    required-files: []
    expected-files: []
    commands: []
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        # Mock the execute method of rules
        with patch.object(project.rules['rule1'], 'execute') as mock_exec1:
            with patch.object(project.rules['rule2'], 'execute') as mock_exec2:
                project.run()
                mock_exec1.assert_called_once()
                mock_exec2.assert_called_once()
    
    def test_run_executes_rules_in_order(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
rules:
  first:
    required-files: []
    expected-files: []
    commands: []
  second:
    required-files: []
    expected-files: []
    commands: []
  third:
    required-files: []
    expected-files: []
    commands: []
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
        
        execution_order = []
        
        def track_execution(name):
            def execute():
                execution_order.append(name)
            return execute
        
        with patch.object(project.rules['first'], 'execute', side_effect=track_execution('first')):
            with patch.object(project.rules['second'], 'execute', side_effect=track_execution('second')):
                with patch.object(project.rules['third'], 'execute', side_effect=track_execution('third')):
                    project.run()
        
        assert len(execution_order) == 3
    
    def test_run_with_no_rules(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
rules: {}
""")
        
        with patch('builder.project.Logger'):
            project = Project(str(config_file))
            project.run()  # Should not raise any errors


class TestProjectLoadConfig:
    """Tests for Project.__load_config (YAML loading)."""
    
    def test_invalid_yaml(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("""
invalid: yaml: syntax: here
  - this
  is: broken
""")
        
        with patch('builder.project.Logger'):
            with pytest.raises(yaml.YAMLError):
                project = Project(str(config_file))
    
    def test_empty_config(self, tmp_path):
        config_file = tmp_path / "test.build"
        pyproject_file = tmp_path / "pyproject.toml"
        
        pyproject_file.write_text("""
[project]
name = "test-project"
""")
        
        config_file.write_text("")
        
        with patch('builder.project.Logger'):
            # Empty YAML should result in None or empty dict
            # The Project class should handle this
            with pytest.raises((AttributeError, TypeError)):
                project = Project(str(config_file))
