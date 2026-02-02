# type: ignore[reportAttributeAccessIssue]import pytest

import pytest
import os
import sys
import tempfile
import yaml
from unittest.mock import patch

from builder.project import Project
from builder.rule import Rule


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def basic_config(temp_dir):
    """Create a basic build.yml configuration file."""
    config = {
        'vars': {
            'BUILD_DIR': 'build',
            'SOURCE_DIR': 'src',
        },
        'rules': {
            'compile': {
                'tags': ['build'],
                'required-files': ['src/main.py'],
                'expected-files': ['build/output.txt'],
                'commands': ['echo "compiling"'],
            },
            'test': {
                'tags': ['test'],
                'required-files': ['tests/test_*.py'],
                'expected-files': [],
                'commands': ['pytest'],
            }
        }
    }
    config_file = os.path.join(temp_dir, 'build.yml')
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    return config_file


@pytest.fixture
def config_with_imports(temp_dir):
    """Create a config file with imports."""
    # Create sub-project
    sub_dir = os.path.join(temp_dir, 'subproject')
    os.makedirs(sub_dir, exist_ok=True)
    
    sub_config = {
        'vars': {
            'SUB_VAR': 'sub_value',
        },
        'rules': {
            'sub_rule': {
                'tags': ['sub'],
                'required-files': [],
                'expected-files': [],
                'commands': ['echo "sub"'],
            }
        }
    }
    sub_config_file = os.path.join(sub_dir, 'build.yml')
    with open(sub_config_file, 'w') as f:
        yaml.dump(sub_config, f)
    
    # Create main config
    main_config = {
        'imports': [
            {'path': 'subproject/build.yml', 'as': 'sub'},
        ],
        'vars': {
            'MAIN_VAR': 'main_value',
        },
        'rules': {}
    }
    main_config_file = os.path.join(temp_dir, 'build.yml')
    with open(main_config_file, 'w') as f:
        yaml.dump(main_config, f)
    
    return main_config_file


@pytest.fixture
def config_with_variables(temp_dir):
    """Create a config with variable substitution."""
    config = {
        'vars': {
            'BASE': '/path/to',
            'NESTED': '${BASE}/nested',
        },
        'rules': {
            'build': {
                'tags': ['build'],
                'required-files': ['${BASE}/input.txt'],
                'expected-files': ['${NESTED}/output.txt'],
                'commands': ['echo "${NESTED}"'],
            }
        }
    }
    config_file = os.path.join(temp_dir, 'build.yml')
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    return config_file


@pytest.fixture
def config_with_file_groups(temp_dir):
    """Create a config with file groups."""
    config = {
        'files-groups': {
            'source_files': ['src/main.py', 'src/utils.py'],
            'test_files': ['tests/test_*.py'],
        },
        'rules': {
            'build': {
                'tags': ['build'],
                'required-files': 'source_files',
                'expected-files': ['build/app'],
                'commands': ['python -m py_compile ${BUILD_DIR}'],
            }
        },
        'vars': {
            'BUILD_DIR': 'build',
        }
    }
    config_file = os.path.join(temp_dir, 'build.yml')
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    return config_file


class TestProjectInitialization:
    """Tests for Project initialization."""
    
    def test_init_with_basic_config(self, basic_config):
        """Test basic project initialization."""
        project = Project(basic_config)
        assert project.config_file == os.path.abspath(basic_config)
        assert 'BUILD_DIR' in project.vars
        assert project.vars['BUILD_DIR'] == 'build'
        assert len(project.rules) == 2
        assert 'compile' in project.rules
        assert 'test' in project.rules
    
    def test_init_with_command_line_variables(self, basic_config):
        """Test initialization with command line variables."""
        cl_vars = {'BUILD_DIR': 'custom_build', 'DEBUG': 'true'}
        project = Project(basic_config, cl_vars)
        # Command line variables have highest priority
        assert project.vars['BUILD_DIR'] == 'custom_build'
        assert project.vars['DEBUG'] == 'true'
    
    def test_init_with_builtin_variables(self, basic_config):
        """Test that builtin variables are set."""
        project = Project(basic_config)
        assert 'PROJECT_DIR' in project.vars
        assert 'PYTHON' in project.vars
        assert project.vars['PYTHON'] == sys.executable
    
    def test_init_creates_rule_objects(self, basic_config):
        """Test that rules are properly instantiated."""
        project = Project(basic_config)
        for rule_name, rule in project.rules.items():
            assert isinstance(rule, Rule)
            assert rule.name == rule_name


class TestProjectConfigLoading:
    """Tests for config file loading."""
    
    def test_load_config_yaml(self, basic_config):
        """Test loading YAML configuration."""
        project = Project(basic_config)
        assert len(project.rules) > 0
    
    def test_load_config_file_not_found(self, temp_dir):
        """Test error when config file doesn't exist."""
        nonexistent_file = os.path.join(temp_dir, 'nonexistent.yml')
        with pytest.raises(FileNotFoundError):
            Project(nonexistent_file)
    
    def test_load_config_invalid_yaml(self, temp_dir):
        """Test error with invalid YAML."""
        invalid_config = os.path.join(temp_dir, 'invalid.yml')
        with open(invalid_config, 'w') as f:
            f.write("invalid: yaml: content: [")
        with pytest.raises(Exception):  # yaml.YAMLError
            Project(invalid_config)


class TestVariableResolution:
    """Tests for variable resolution and substitution."""
    
    def test_resolve_simple_variable(self, basic_config):
        """Test simple variable substitution."""
        project = Project(basic_config)
        project.vars['VAR1'] = 'value1'
        project.vars['VAR2'] = '${VAR1}_extended'
        project._Project__resolve_all_variables()
        assert project.vars['VAR2'] == 'value1_extended'
    
    def test_resolve_nested_variables(self, config_with_variables):
        """Test nested variable substitution."""
        project = Project(config_with_variables)
        assert project.vars['NESTED'] == '/path/to/nested'
    
    def test_resolve_command_execution(self, basic_config):
        """Test command execution in variable resolution."""
        project = Project(basic_config)
        project.vars['USER_NAME'] = '$(echo "testuser")'
        project._Project__resolve_all_variables()
        assert project.vars['USER_NAME'] == 'testuser'
    
    def test_resolve_command_with_error(self, basic_config):
        """Test handling of failed command execution."""
        project = Project(basic_config)
        project.vars['FAIL_CMD'] = '$(exit 1)'
        with pytest.raises(ValueError, match='Failed to execute command'):
            project._Project__resolve_all_variables()
    
    def test_resolve_list_variable(self, basic_config):
        """Test variable resolution with list values."""
        project = Project(basic_config)
        project.vars['LIST_VAR'] = ['item1', 'item2', 'item3']
        project._Project__resolve_all_variables()
        assert project.vars['LIST_VAR'] == ['item1', 'item2', 'item3']
    
    def test_resolve_dict_variable(self, basic_config):
        """Test variable resolution with dict values."""
        project = Project(basic_config)
        project.vars['DICT_VAR'] = {'key1': 'value1', 'key2': 'value2'}
        project._Project__resolve_all_variables()
        assert project.vars['DICT_VAR'] == {'key1': 'value1', 'key2': 'value2'}


class TestImports:
    """Tests for project imports."""
    
    def test_load_sub_project(self, config_with_imports):
        """Test loading a sub-project."""
        project = Project(config_with_imports)
        assert 'sub' in project.imports
        assert isinstance(project.imports['sub'], Project)
    
    def test_import_with_custom_alias(self, temp_dir):
        """Test imports with custom aliases."""
        sub_dir = os.path.join(temp_dir, 'subproject')
        os.makedirs(sub_dir, exist_ok=True)
        
        sub_config = {
            'vars': {'SUB_VAR': 'sub_value'},
            'rules': {}
        }
        with open(os.path.join(sub_dir, 'build.yml'), 'w') as f:
            yaml.dump(sub_config, f)
        
        main_config = {
            'imports': [
                {'path': 'subproject/build.yml', 'as': 'custom_alias'},
            ],
            'vars': {},
            'rules': {}
        }
        main_config_file = os.path.join(temp_dir, 'build.yml')
        with open(main_config_file, 'w') as f:
            yaml.dump(main_config, f)
        
        project = Project(main_config_file)
        assert 'custom_alias' in project.imports
        assert 'custom_alias' not in project.imports or 'build' not in project.imports
    
    def test_import_project_file_parsing(self, temp_dir):
        """Test loading project files like pyproject.toml."""
        # Create a pyproject.toml file
        pyproject_data = {
            'project': {
                'name': 'test_project',
                'version': '1.0.0',
            }
        }
        pyproject_file = os.path.join(temp_dir, 'pyproject.toml')
        with open(pyproject_file, 'w') as f:
            f.write('[project]\nname = "test_project"\nversion = "1.0.0"\n')
        
        main_config = {
            'imports': [
                {'path': 'pyproject.toml', 'as': 'project_info'},
            ],
            'vars': {},
            'rules': {}
        }
        main_config_file = os.path.join(temp_dir, 'build.yml')
        with open(main_config_file, 'w') as f:
            yaml.dump(main_config, f)
        
        project = Project(main_config_file)
        # Check that project file vars are loaded
        assert 'project_info.name' in project.vars


class TestFileGroups:
    """Tests for file groups handling."""
    
    def test_load_file_groups(self, config_with_file_groups):
        """Test loading file groups."""
        project = Project(config_with_file_groups)
        assert 'source_files' in project.files_groups
        assert 'test_files' in project.files_groups
    
    def test_file_groups_in_rules(self, config_with_file_groups):
        """Test that file groups are used in rules."""
        project = Project(config_with_file_groups)
        build_rule = project.rules['build']
        assert 'src/main.py' in build_rule.required_files


class TestSelectRules:
    """Tests for rule selection."""
    
    def test_select_rules_by_name(self, basic_config):
        """Test selecting rules by name."""
        project = Project(basic_config)
        selected = project.select_rules(['compile'], [])
        assert 'compile' in selected
        assert 'test' not in selected
    
    def test_select_rules_by_name_pattern(self, basic_config):
        """Test selecting rules by name pattern."""
        project = Project(basic_config)
        selected = project.select_rules(['test*'], [])
        assert 'test' in selected
        assert 'compile' not in selected
    
    def test_select_rules_by_tag(self, basic_config):
        """Test selecting rules by tag."""
        project = Project(basic_config)
        selected = project.select_rules([], ['build'])
        assert 'compile' in selected
        assert 'test' not in selected
    
    def test_select_rules_by_tag_and_name(self, basic_config):
        """Test selecting rules by both name and tag."""
        project = Project(basic_config)
        selected = project.select_rules(['compile'], ['build'])
        assert 'compile' in selected
    
    def test_select_rules_empty_criteria(self, basic_config):
        """Test selecting all rules when no criteria provided."""
        project = Project(basic_config)
        selected = project.select_rules([], [])
        assert len(selected) == len(project.rules)


class TestGetters:
    """Tests for getter methods."""
    
    def test_get_rule_by_name(self, basic_config):
        """Test getting a rule by name."""
        project = Project(basic_config)
        rule = project.get_rule('compile')
        assert isinstance(rule, Rule)
        assert rule.name == 'compile'
    
    def test_get_rule_not_found(self, basic_config):
        """Test error when rule not found."""
        project = Project(basic_config)
        with pytest.raises(KeyError):
            project.get_rule('nonexistent')
    
    def test_get_var_by_name(self, basic_config):
        """Test getting a variable by name."""
        project = Project(basic_config)
        var = project.get_var('BUILD_DIR')
        assert var == 'build'
    
    def test_get_var_not_found(self, basic_config):
        """Test error when variable not found."""
        project = Project(basic_config)
        with pytest.raises(KeyError):
            project.get_var('nonexistent_var')
    
    def test_get_method_returns_rule(self, basic_config):
        """Test get() method returns rule."""
        project = Project(basic_config)
        rule = project.get('compile')
        assert isinstance(rule, Rule)
    
    def test_get_method_returns_var(self, basic_config):
        """Test get() method returns variable."""
        project = Project(basic_config)
        var = project.get('BUILD_DIR')
        assert var == 'build'


class TestGettersWithImports:
    """Tests for getters with imported projects."""
    
    def test_get_imported_rule(self, config_with_imports):
        """Test getting a rule from imported project."""
        project = Project(config_with_imports)
        rule = project.get_rule('sub.sub_rule')
        assert isinstance(rule, Rule)
        assert rule.name == 'sub_rule'
    
    def test_get_imported_var(self, config_with_imports):
        """Test getting a variable from imported project."""
        project = Project(config_with_imports)
        var = project.get_var('sub.SUB_VAR')
        assert var == 'sub_value'
    
    def test_get_imported_rule_not_found(self, config_with_imports):
        """Test error when imported rule not found."""
        project = Project(config_with_imports)
        with pytest.raises(KeyError):
            project.get_rule('sub.nonexistent')
    
    def test_get_all_rules_includes_imports(self, config_with_imports):
        """Test that get_all_rules includes imported rules."""
        project = Project(config_with_imports)
        all_rules = project.get_all_rules()
        assert 'sub.sub_rule' in all_rules
    
    def test_get_all_vars_includes_imports(self, config_with_imports):
        """Test that get_all_vars includes imported variables."""
        project = Project(config_with_imports)
        all_vars = project.get_all_vars()
        assert 'sub.SUB_VAR' in all_vars


class TestSummary:
    """Tests for project summary generation."""
    
    def test_get_summary(self, basic_config):
        """Test getting project summary."""
        project = Project(basic_config)
        summary = project.get_summary()
        assert isinstance(summary, str)
        assert 'Project Configuration' in summary
        assert 'Variables' in summary
        assert 'Rules' in summary
        assert 'BUILD_DIR' in summary
    
    def test_summary_includes_rules(self, basic_config):
        """Test that summary includes all rules."""
        project = Project(basic_config)
        summary = project.get_summary()
        assert 'compile' in summary
        assert 'test' in summary
    
    def test_summary_with_imports(self, config_with_imports):
        """Test summary includes imported projects."""
        project = Project(config_with_imports)
        summary = project.get_summary()
        assert 'sub_rule' in summary


class TestVariablePriority:
    """Tests for variable priority levels."""
    
    def test_config_file_vars_override_defaults(self, basic_config):
        """Test that config file vars override defaults."""
        project = Project(basic_config)
        # PROJECT_DIR should be overridable via config
        assert 'BUILD_DIR' in project.vars
        assert project.vars['BUILD_DIR'] == 'build'
    
    def test_command_line_vars_have_highest_priority(self, basic_config):
        """Test that command line vars override everything."""
        cl_vars = {'BUILD_DIR': 'priority_build', 'PROJECT_DIR': '/override'}
        project = Project(basic_config, cl_vars)
        assert project.vars['BUILD_DIR'] == 'priority_build'
        # PROJECT_DIR is builtin, so it gets overridden
        assert project.vars['PROJECT_DIR'] == '/override'
    
    def test_builtin_vars_override_config_defaults(self, temp_dir):
        """Test that builtin vars have priority over config vars."""
        config = {
            'vars': {
                'PROJECT_DIR': '/wrong/path',
                'PYTHON': '/wrong/python',
            },
            'rules': {}
        }
        config_file = os.path.join(temp_dir, 'build.yml')
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        project = Project(config_file)
        # Builtin vars should override config vars
        assert project.vars['PROJECT_DIR'] == os.path.dirname(config_file)
        assert project.vars['PYTHON'] == sys.executable


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_empty_config(self, temp_dir):
        """Test loading minimal config."""
        config = {'rules': {}}
        config_file = os.path.join(temp_dir, 'build.yml')
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        project = Project(config_file)
        assert len(project.rules) == 0
        assert len(project.imports) == 0
    
    def test_import_directory_without_build_yml(self, temp_dir):
        """Test error when importing directory without build.yml."""
        sub_dir = os.path.join(temp_dir, 'subproject')
        os.makedirs(sub_dir, exist_ok=True)
        
        main_config = {
            'imports': [
                {'path': 'subproject'},
            ],
            'vars': {},
            'rules': {}
        }
        main_config_file = os.path.join(temp_dir, 'build.yml')
        with open(main_config_file, 'w') as f:
            yaml.dump(main_config, f)
        
        with pytest.raises(ValueError, match='Import path is a directory'):
            Project(main_config_file)
    
    def test_absolute_import_path(self, temp_dir):
        """Test importing with absolute path."""
        sub_dir = os.path.join(temp_dir, 'subproject')
        os.makedirs(sub_dir, exist_ok=True)
        
        sub_config = {'vars': {}, 'rules': {}}
        sub_config_file = os.path.join(sub_dir, 'build.yml')
        with open(sub_config_file, 'w') as f:
            yaml.dump(sub_config, f)
        
        main_config = {
            'imports': [
                {'path': sub_config_file},
            ],
            'vars': {},
            'rules': {}
        }
        main_config_file = os.path.join(temp_dir, 'build.yml')
        with open(main_config_file, 'w') as f:
            yaml.dump(main_config, f)
        
        project = Project(main_config_file)
        assert len(project.imports) > 0
    
    def test_variable_circular_reference(self, temp_dir):
        """Test handling of circular variable references."""
        config = {
            'vars': {
                'VAR1': '${VAR2}',
                'VAR2': '${VAR1}',
            },
            'rules': {}
        }
        config_file = os.path.join(temp_dir, 'build.yml')
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Should not hang or crash, variables will eventually stabilize
        project = Project(config_file)
        # After resolution loop, circular refs remain partially resolved
        assert project.vars['VAR1'] in ('${VAR2}', '${VAR1}')
        assert project.vars['VAR2'] in ('${VAR1}', '${VAR2}')
    
    def test_config_with_no_rules(self, temp_dir):
        """Test config without rules section."""
        config = {'vars': {'TEST_VAR': 'test_value'}}
        config_file = os.path.join(temp_dir, 'build.yml')
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        project = Project(config_file)
        assert len(project.rules) == 0
        assert project.get_var('TEST_VAR') == 'test_value'


class TestRun:
    """Tests for running rules."""
    
    @patch('builder.rule.Rule.execute')
    def test_run_rules(self, mock_execute, basic_config):
        """Test running selected rules."""
        project = Project(basic_config)
        rules_to_run = {'compile': project.rules['compile']}
        project.run(rules_to_run)
        mock_execute.assert_called_once()
    
    @patch('builder.rule.Rule.execute')
    def test_run_multiple_rules(self, mock_execute, basic_config):
        """Test running multiple rules."""
        project = Project(basic_config)
        rules_to_run = {
            'compile': project.rules['compile'],
            'test': project.rules['test']
        }
        project.run(rules_to_run)
        assert mock_execute.call_count == 2
    
    @patch('builder.rule.Rule.execute')
    def test_run_with_force_flag(self, mock_execute, basic_config):
        """Test running rules with force flag."""
        project = Project(basic_config)
        rules_to_run = {'compile': project.rules['compile']}
        project.run(rules_to_run, force=True)
        mock_execute.assert_called_once_with(True)
