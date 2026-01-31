import pytest
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from builder.utils import (
    get_max_edit_time,
    files_exists,
    is_pattern,
    apply_variables,
    expand_files,
    flatten,
    list2str
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for testing."""
    files = []
    for i in range(3):
        file_path = os.path.join(temp_dir, f'file_{i}.txt')
        Path(file_path).touch()
        files.append(file_path)
        time.sleep(0.01)  # Ensure different timestamps
    return files


class TestGetMaxEditTime:
    """Tests for get_max_edit_time function."""
    
    def test_single_file(self, temp_dir):
        """Test with a single file."""
        file_path = os.path.join(temp_dir, 'single.txt')
        Path(file_path).touch()
        
        max_time = get_max_edit_time([file_path])
        expected_time = os.path.getmtime(file_path)
        
        assert max_time == expected_time
    
    def test_multiple_files(self, sample_files):
        """Test with multiple files."""
        max_time = get_max_edit_time(sample_files)
        expected_time = os.path.getmtime(sample_files[-1])  # Last file is newest
        
        assert max_time == expected_time
    
    def test_returns_latest_time(self, temp_dir):
        """Test that the latest file time is returned."""
        file1 = os.path.join(temp_dir, 'file1.txt')
        file2 = os.path.join(temp_dir, 'file2.txt')
        
        Path(file1).touch()
        time.sleep(0.1)
        Path(file2).touch()
        
        max_time = get_max_edit_time([file1, file2])
        file2_time = os.path.getmtime(file2)
        
        assert max_time == file2_time
    
    def test_nonexistent_file_ignored(self, temp_dir):
        """Test that nonexistent files are ignored."""
        existing_file = os.path.join(temp_dir, 'exists.txt')
        nonexistent_file = os.path.join(temp_dir, 'nonexistent.txt')
        
        Path(existing_file).touch()
        
        # Should not raise and should return the existing file's time
        max_time = get_max_edit_time([existing_file, nonexistent_file])
        expected_time = os.path.getmtime(existing_file)
        
        assert max_time == expected_time
    
    def test_empty_list_raises_error(self):
        """Test with empty list."""
        with pytest.raises(ValueError):
            get_max_edit_time([])
    
    def test_all_nonexistent_files_raises_error(self, temp_dir):
        """Test when all files are nonexistent."""
        nonexistent_files = [
            os.path.join(temp_dir, 'missing1.txt'),
            os.path.join(temp_dir, 'missing2.txt')
        ]
        
        with pytest.raises(ValueError):
            get_max_edit_time(nonexistent_files)


class TestFilesExists:
    """Tests for files_exists function."""
    
    def test_all_files_exist(self, sample_files):
        """Test when all files exist."""
        assert files_exists(sample_files) is True
    
    def test_single_existing_file(self, temp_dir):
        """Test with single existing file."""
        file_path = os.path.join(temp_dir, 'exists.txt')
        Path(file_path).touch()
        
        assert files_exists([file_path]) is True
    
    def test_single_missing_file(self, temp_dir):
        """Test with single missing file."""
        file_path = os.path.join(temp_dir, 'missing.txt')
        
        assert files_exists([file_path]) is False
    
    def test_partial_missing_files(self, temp_dir):
        """Test when some files are missing."""
        existing = os.path.join(temp_dir, 'exists.txt')
        missing = os.path.join(temp_dir, 'missing.txt')
        
        Path(existing).touch()
        
        assert files_exists([existing, missing]) is False
    
    def test_empty_list(self):
        """Test with empty list."""
        assert files_exists([]) is True  # all() returns True for empty
    
    def test_multiple_existing_files(self, sample_files):
        """Test with multiple existing files."""
        assert files_exists(sample_files) is True
    
    def test_directories(self, temp_dir):
        """Test that directories are recognized as existing."""
        sub_dir = os.path.join(temp_dir, 'subdir')
        os.makedirs(sub_dir, exist_ok=True)
        
        assert files_exists([sub_dir]) is True


class TestIsPattern:
    """Tests for is_pattern function."""
    
    def test_asterisk_pattern(self):
        """Test pattern with asterisk."""
        assert is_pattern('*.txt') is True
    
    def test_question_mark_pattern(self):
        """Test pattern with question mark."""
        assert is_pattern('file_?.txt') is True
    
    def test_bracket_pattern(self):
        """Test pattern with brackets."""
        assert is_pattern('file_[0-9].txt') is True
    
    def test_multiple_wildcards(self):
        """Test pattern with multiple wildcards."""
        assert is_pattern('*.py') is True
        assert is_pattern('test_?*.py') is True
    
    def test_no_pattern(self):
        """Test non-pattern strings."""
        assert is_pattern('simple_file.txt') is False
        assert is_pattern('path/to/file.txt') is False
    
    def test_pattern_in_middle(self):
        """Test pattern in middle of string."""
        assert is_pattern('file_*.txt') is True
        assert is_pattern('dir/file_*.txt') is True
    
    def test_empty_string(self):
        """Test empty string."""
        assert is_pattern('') is False
    
    def test_only_special_chars(self):
        """Test strings with only special characters."""
        assert is_pattern('***') is True
        assert is_pattern('???') is True
        assert is_pattern('[')is True


class TestApplyVariables:
    """Tests for apply_variables function."""
    
    def test_simple_variable_substitution(self):
        """Test simple variable substitution."""
        value = 'Hello ${NAME}'
        variables = {'NAME': 'World'}
        
        result = apply_variables(value, variables)
        assert result == 'Hello World'
    
    def test_multiple_variables(self):
        """Test substitution with multiple variables."""
        value = '${PROJECT}/${BUILD}/output'
        variables = {'PROJECT': 'myapp', 'BUILD': 'debug'}
        
        result = apply_variables(value, variables)
        assert result == 'myapp/debug/output'
    
    def test_repeated_variable(self):
        """Test repeated variable in value."""
        value = '${DIR}/${FILE}/${DIR}/${FILE}'
        variables = {'DIR': 'src', 'FILE': 'main.py'}
        
        result = apply_variables(value, variables)
        assert result == 'src/main.py/src/main.py'
    
    def test_no_variables(self):
        """Test with no variables in value."""
        value = 'simple/path/file.txt'
        variables = {'VAR': 'value'}
        
        result = apply_variables(value, variables)
        assert result == 'simple/path/file.txt'
    
    def test_empty_variables_dict(self):
        """Test with empty variables dict."""
        value = 'Hello ${NAME}'
        
        result = apply_variables(value, {})
        assert result == 'Hello ${NAME}'
    
    def test_numeric_variable_value(self):
        """Test with numeric variable values."""
        value = 'Version ${MAJOR}${MINOR}'
        variables = {'MAJOR': 1, 'MINOR': 5}
        
        result = apply_variables(value, variables)
        assert result == 'Version 15'
    
    def test_variable_not_in_dict(self):
        """Test when variable is not in dict."""
        value = 'Path is ${MISSING_VAR}'
        variables = {'OTHER_VAR': 'value'}
        
        result = apply_variables(value, variables)
        assert result == 'Path is ${MISSING_VAR}'
    
    def test_empty_value(self):
        """Test with empty value string."""
        variables = {'VAR': 'value'}
        
        result = apply_variables('', variables)
        assert result == ''
    
    def test_variable_as_part_of_path(self):
        """Test variable substitution in file paths."""
        value = '${HOME}/projects/${PROJECT_NAME}/src'
        variables = {'HOME': '/home/user', 'PROJECT_NAME': 'myapp'}
        
        result = apply_variables(value, variables)
        assert result == '/home/user/projects/myapp/src'
    
    def test_special_characters_in_value(self):
        """Test with special characters in variable values."""
        value = 'Command: ${CMD}'
        variables = {'CMD': 'echo "Hello | World"'}
        
        result = apply_variables(value, variables)
        assert result == 'Command: echo "Hello | World"'


class TestExpandFiles:
    """Tests for expand_files function."""
    
    def test_expand_glob_pattern(self, temp_dir):
        """Test expanding glob pattern."""
        # Create test files
        for i in range(3):
            Path(os.path.join(temp_dir, f'file_{i}.txt')).touch()
        
        pattern = os.path.join(temp_dir, 'file_*.txt')
        result = expand_files([pattern])
        
        assert len(result) == 3
        assert all(f.endswith('.txt') for f in result)
    
    def test_no_pattern_preserves_path(self, temp_dir):
        """Test that non-pattern paths are preserved."""
        file_path = os.path.join(temp_dir, 'file.txt')
        Path(file_path).touch()
        
        result = expand_files([file_path])
        assert file_path in result
    
    def test_mixed_patterns_and_paths(self, temp_dir):
        """Test with mixed patterns and regular paths."""
        file1 = os.path.join(temp_dir, 'file1.txt')
        file2 = os.path.join(temp_dir, 'file2.txt')
        file3 = os.path.join(temp_dir, 'file3.txt')
        
        Path(file1).touch()
        Path(file2).touch()
        Path(file3).touch()
        
        pattern = os.path.join(temp_dir, 'file[23].txt')
        result = expand_files([pattern, file1])
        
        assert file1 in result
        assert len(result) >= 3  # file1 + file2 + file3
    
    def test_no_matches_for_pattern(self, temp_dir):
        """Test pattern with no matches."""
        pattern = os.path.join(temp_dir, 'nonexistent_*.txt')
        result = expand_files([pattern])
        
        assert result == []
    
    def test_recursive_glob_pattern(self, temp_dir):
        """Test recursive glob pattern."""
        # Create nested structure
        sub_dir = os.path.join(temp_dir, 'sub')
        os.makedirs(sub_dir)
        Path(os.path.join(temp_dir, 'file1.py')).touch()
        Path(os.path.join(sub_dir, 'file2.py')).touch()
        
        pattern = os.path.join(temp_dir, '**/*.py')
        result = expand_files([pattern])
        
        assert len(result) == 2
    
    def test_empty_list(self):
        """Test with empty list."""
        result = expand_files([])
        assert result == []
    
    def test_multiple_patterns(self, temp_dir):
        """Test with multiple patterns."""
        # Create test files
        for i in range(3):
            Path(os.path.join(temp_dir, f'test_{i}.py')).touch()
            Path(os.path.join(temp_dir, f'file_{i}.txt')).touch()
        
        pattern1 = os.path.join(temp_dir, 'test_*.py')
        pattern2 = os.path.join(temp_dir, 'file_*.txt')
        
        result = expand_files([pattern1, pattern2])
        
        assert len(result) == 6
    
    def test_bracket_pattern(self, temp_dir):
        """Test bracket pattern for character ranges."""
        Path(os.path.join(temp_dir, 'file_1.txt')).touch()
        Path(os.path.join(temp_dir, 'file_2.txt')).touch()
        Path(os.path.join(temp_dir, 'file_a.txt')).touch()
        
        pattern = os.path.join(temp_dir, 'file_[12].txt')
        result = expand_files([pattern])
        
        assert len(result) == 2


class TestFlatten:
    """Tests for flatten function."""
    
    def test_simple_dict(self):
        """Test flattening simple dict."""
        dic = {'a': 1, 'b': 2}
        result = flatten(dic)
        
        assert result == {'a': 1, 'b': 2}
    
    def test_nested_dict(self):
        """Test flattening nested dict."""
        dic = {
            'level1': {
                'level2': {
                    'value': 'test'
                }
            }
        }
        result = flatten(dic)
        
        assert result == {'level1.level2.value': 'test'}
    
    def test_mixed_nested_and_simple(self):
        """Test with mix of nested and simple values."""
        dic = {
            'simple': 'value',
            'nested': {
                'inner': 'data'
            }
        }
        result = flatten(dic)
        
        assert result == {
            'simple': 'value',
            'nested.inner': 'data'
        }
    
    def test_custom_separator(self):
        """Test with custom separator."""
        dic = {
            'level1': {
                'level2': 'value'
            }
        }
        result = flatten(dic, sep=':')
        
        assert result == {'level1:level2': 'value'}
    
    def test_deep_nesting(self):
        """Test deep nesting."""
        dic = {
            'a': {
                'b': {
                    'c': {
                        'd': 'value'
                    }
                }
            }
        }
        result = flatten(dic)
        
        assert result == {'a.b.c.d': 'value'}
    
    def test_empty_dict(self):
        """Test with empty dict."""
        result = flatten({})
        assert result == {}
    
    def test_list_values_not_flattened(self):
        """Test that list values are preserved."""
        dic = {
            'items': [1, 2, 3],
            'nested': {
                'list': ['a', 'b']
            }
        }
        result = flatten(dic)
        
        assert result['items'] == [1, 2, 3]
        assert result['nested.list'] == ['a', 'b']
    
    def test_multiple_keys_at_same_level(self):
        """Test multiple keys at same nesting level."""
        dic = {
            'parent': {
                'child1': 'value1',
                'child2': 'value2',
                'child3': 'value3'
            }
        }
        result = flatten(dic)
        
        assert result == {
            'parent.child1': 'value1',
            'parent.child2': 'value2',
            'parent.child3': 'value3'
        }
    
    def test_numeric_keys_and_values(self):
        """Test with numeric keys (converted to strings by Python)."""
        dic = {
            'config': {
                'version': 1,
                'timeout': 30
            }
        }
        result = flatten(dic)
        
        assert result == {
            'config.version': 1,
            'config.timeout': 30
        }


class TestList2Str:
    """Tests for list2str function."""
    
    def test_string_list(self):
        """Test with list of strings."""
        lst = ['apple', 'banana', 'cherry']
        result = list2str(lst)
        
        assert result == 'apple, banana, cherry'
    
    def test_single_element(self):
        """Test with single element."""
        lst = ['only']
        result = list2str(lst)
        
        assert result == 'only'
    
    def test_numeric_list(self):
        """Test with numeric list."""
        lst = [1, 2, 3]
        result = list2str(lst)
        
        assert result == '1, 2, 3'
    
    def test_mixed_types(self):
        """Test with mixed types."""
        lst = ['text', 42, 3.14, True]
        result = list2str(lst)
        
        assert result == 'text, 42, 3.14, True'
    
    def test_empty_list(self):
        """Test with empty list."""
        result = list2str([])
        assert result == ''
    
    def test_list_with_empty_strings(self):
        """Test list containing empty strings."""
        lst = ['', 'text', '']
        result = list2str(lst)
        
        assert result == ', text, '
    
    def test_list_with_special_characters(self):
        """Test list with special characters."""
        lst = ['echo "test"', 'pipe|command', 'file*.txt']
        result = list2str(lst)
        
        assert result == 'echo "test", pipe|command, file*.txt'
    
    def test_single_element_no_comma(self):
        """Test that single element doesn't have trailing comma."""
        result = list2str(['single'])
        assert result == 'single'
        assert ',' not in result
    
    def test_largelist(self):
        """Test with large list."""
        lst = list(range(100))
        result = list2str(lst)
        
        items = result.split(', ')
        assert len(items) == 100
    
    def test_none_values(self):
        """Test list with None values."""
        lst = ['a', None, 'b']
        result = list2str(lst)
        
        assert result == 'a, None, b'


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_expand_and_get_max_time(self, temp_dir):
        """Test expanding patterns and getting max edit time."""
        # Create files
        for i in range(3):
            Path(os.path.join(temp_dir, f'file_{i}.txt')).touch()
            time.sleep(0.01)
        
        pattern = os.path.join(temp_dir, 'file_*.txt')
        expanded = expand_files([pattern])
        
        assert len(expanded) == 3
        max_time = get_max_edit_time(expanded)
        assert max_time > 0
    
    def test_apply_variables_then_expand(self, temp_dir):
        """Test applying variables then expanding patterns."""
        # Create files
        Path(os.path.join(temp_dir, 'test_1.py')).touch()
        Path(os.path.join(temp_dir, 'test_2.py')).touch()
        
        pattern_template = '${DIR}/test_*.py'
        variables = {'DIR': temp_dir}
        
        pattern = apply_variables(pattern_template, variables)
        expanded = expand_files([pattern])
        
        assert len(expanded) == 2
    
    def test_flatten_and_list2str_values(self):
        """Test flattening dict and converting list values."""
        dic = {
            'config': {
                'files': ['a.txt', 'b.txt'],
                'tags': ['tag1', 'tag2', 'tag3']
            }
        }
        flattened = flatten(dic)
        
        files_str = list2str(flattened.get('config.files', []))
        assert files_str == 'a.txt, b.txt'
    
    def test_workflow_with_all_functions(self, temp_dir):
        """Test a realistic workflow using multiple functions."""
        # Create test files
        for i in range(2):
            Path(os.path.join(temp_dir, f'input_{i}.txt')).touch()
        
        # Apply variables to template
        template = '${BASE_DIR}/input_*.txt'
        variables = {'BASE_DIR': temp_dir}
        pattern = apply_variables(template, variables)
        
        # Expand pattern
        files = expand_files([pattern])
        
        # Check files exist
        assert files_exists(files) is True
        
        # Get max edit time
        max_time = get_max_edit_time(files)
        assert max_time > 0


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_apply_variables_with_malformed_reference(self):
        """Test variable reference without closing brace."""
        value = 'Path is ${INCOMPLETE'
        variables = {'INCOMPLETE': 'value'}
        
        result = apply_variables(value, variables)
        # Should not substitute malformed reference
        assert result == 'Path is ${INCOMPLETE'
    
    def test_expand_files_with_special_directory_names(self, temp_dir):
        """Test expanding patterns in directories with special names."""
        special_dir = os.path.join(temp_dir, 'dir-with-dashes_and_underscores')
        os.makedirs(special_dir)
        Path(os.path.join(special_dir, 'file.txt')).touch()
        
        pattern = os.path.join(special_dir, '*.txt')
        result = expand_files([pattern])
        
        assert len(result) == 1
    
    def test_flatten_with_empty_nested_dict(self):
        """Test flattening dict with empty nested dict."""
        dic = {
            'outer': {
                'inner': {}
            }
        }
        result = flatten(dic)
        
        assert result == {}
    
    def test_list2str_with_unicode(self):
        """Test list2str with unicode strings."""
        lst = ['hello', '世界', 'мир']
        result = list2str(lst)
        
        assert '世界' in result
        assert 'мир' in result
