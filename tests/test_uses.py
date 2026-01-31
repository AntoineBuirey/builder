import pytest
import os
import json
import tempfile
from pathlib import Path

from builder.uses import (
    load_project_file,
    is_project_file,
    FilesLoaders,
)
import builder.uses as uses_module


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_pyproject(temp_dir):
    """Create a sample pyproject.toml file."""
    content = """
[project]
name = "test-project"
version = "1.0.0"
description = "A test project"
authors = [{name = "Test Author", email = "test@example.com"}]

[tool.poetry]
packages = [{include = "test_package"}]
"""
    file_path = os.path.join(temp_dir, 'pyproject.toml')
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path


@pytest.fixture
def sample_package_json(temp_dir):
    """Create a sample package.json file."""
    content = {
        "name": "test-project",
        "version": "1.0.0",
        "description": "A test project",
        "author": "Test Author",
        "license": "MIT"
    }
    file_path = os.path.join(temp_dir, 'package.json')
    with open(file_path, 'w') as f:
        json.dump(content, f)
    return file_path


@pytest.fixture
def complex_pyproject(temp_dir):
    """Create a complex pyproject.toml with multiple sections."""
    content = """
[project]
name = "complex-project"
version = "2.0.0"
description = "A complex project"
requires-python = ">=3.10"
keywords = ["test", "example"]
dependencies = [
    "requests>=2.28.0",
    "pydantic>=1.9.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "black>=22.0"]
docs = ["sphinx>=4.0"]

[project.urls]
Homepage = "https://example.com"
Repository = "https://github.com/example/repo"

[tool.poetry]
packages = [{include = "my_package"}]

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
"""
    file_path = os.path.join(temp_dir, 'pyproject.toml')
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path


@pytest.fixture
def complex_package_json(temp_dir):
    """Create a complex package.json."""
    content = {
        "name": "complex-project",
        "version": "2.0.0",
        "description": "A complex project",
        "author": {
            "name": "Test Author",
            "email": "test@example.com"
        },
        "license": "MIT",
        "main": "dist/index.js",
        "dependencies": {
            "express": "^4.18.0",
            "lodash": "^4.17.0"
        },
        "devDependencies": {
            "jest": "^29.0",
            "typescript": "^5.0"
        },
        "scripts": {
            "build": "tsc",
            "test": "jest"
        }
    }
    file_path = os.path.join(temp_dir, 'package.json')
    with open(file_path, 'w') as f:
        json.dump(content, f)
    return file_path


class TestIsProjectFile:
    """Tests for is_project_file function."""
    
    def test_pyproject_toml_is_project_file(self):
        """Test that pyproject.toml is recognized as project file."""
        assert is_project_file('/path/to/pyproject.toml') is True
    
    def test_package_json_is_project_file(self):
        """Test that package.json is recognized as project file."""
        assert is_project_file('/path/to/package.json') is True
    
    def test_non_project_file(self):
        """Test that non-project files are not recognized."""
        assert is_project_file('/path/to/readme.md') is False
        assert is_project_file('/path/to/setup.py') is False
    
    def test_pyproject_toml_with_path(self):
        """Test pyproject.toml with full path."""
        assert is_project_file('/home/user/projects/myapp/pyproject.toml') is True
    
    def test_package_json_with_path(self):
        """Test package.json with full path."""
        assert is_project_file('/home/user/projects/myapp/package.json') is True
    
    def test_case_sensitive(self):
        """Test that matching is case sensitive."""
        assert is_project_file('PYPROJECT.TOML') is False
        assert is_project_file('Package.json') is False
    
    def test_partial_filename_not_matched(self):
        """Test that partial filename matches are not accepted."""
        assert is_project_file('/path/to/myproject.toml') is False
        assert is_project_file('/path/to/package-lock.json') is False
    
    def test_empty_string(self):
        """Test with empty string."""
        assert is_project_file('') is False


class TestLoadProjectFile:
    """Tests for load_project_file function."""
    
    def test_load_pyproject_toml(self, sample_pyproject):
        """Test loading pyproject.toml file."""
        result = load_project_file(sample_pyproject)
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert result['name'] == 'test-project'
        assert result['version'] == '1.0.0'
    
    def test_load_package_json(self, sample_package_json):
        """Test loading package.json file."""
        result = load_project_file(sample_package_json)
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert result['name'] == 'test-project'
        assert result['version'] == '1.0.0'
    
    def test_load_complex_pyproject(self, complex_pyproject):
        """Test loading complex pyproject.toml."""
        result = load_project_file(complex_pyproject)
        
        assert result['name'] == 'complex-project'
        assert result['version'] == '2.0.0'
        assert 'requires-python' in result
        assert 'dependencies' in result
    
    def test_load_complex_package_json(self, complex_package_json):
        """Test loading complex package.json."""
        result = load_project_file(complex_package_json)
        
        assert result['name'] == 'complex-project'
        assert result['version'] == '2.0.0'
        assert 'dependencies' in result
        assert 'devDependencies' in result
    
    def test_unsupported_file_type(self, temp_dir):
        """Test error with unsupported file type."""
        unsupported_file = os.path.join(temp_dir, 'setup.py')
        Path(unsupported_file).touch()
        
        with pytest.raises(ValueError, match='Unsupported file type'):
            load_project_file(unsupported_file)
    
    def test_unsupported_file_extension(self, temp_dir):
        """Test error with unsupported extension."""
        unsupported_file = os.path.join(temp_dir, 'config.ini')
        Path(unsupported_file).touch()
        
        with pytest.raises(ValueError, match='Unsupported file type'):
            load_project_file(unsupported_file)


class TestLoadPyprojectToml:
    """Tests for pyproject.toml loading via load_project_file."""
    
    def test_load_valid_pyproject(self, sample_pyproject):
        """Test loading valid pyproject.toml."""
        result = load_project_file(sample_pyproject)
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert result['name'] == 'test-project'
    
    def test_load_complex_pyproject(self, complex_pyproject):
        """Test loading complex pyproject.toml."""
        result = load_project_file(complex_pyproject)
        
        assert result['name'] == 'complex-project'
        assert 'dependencies' in result
        assert 'requires-python' in result
    
    def test_missing_project_section(self, temp_dir):
        """Test error when [project] section is missing."""
        no_project_file = os.path.join(temp_dir, 'pyproject.toml')
        with open(no_project_file, 'w') as f:
            f.write('[tool.poetry]\nname = "test"\n')
        
        with pytest.raises(ValueError, match='does not contain a \\[project\\] section'):
            load_project_file(no_project_file)
    
    def test_empty_pyproject(self, temp_dir):
        """Test error with empty pyproject.toml."""
        empty_file = os.path.join(temp_dir, 'pyproject.toml')
        Path(empty_file).touch()
        
        # Empty TOML file raises ValueError for missing [project] section
        with pytest.raises(ValueError, match='does not contain a \\[project\\] section'):
            load_project_file(empty_file)
    
    def test_malformed_pyproject(self, temp_dir):
        """Test error with malformed TOML."""
        malformed_file = os.path.join(temp_dir, 'pyproject.toml')
        with open(malformed_file, 'w') as f:
            f.write('[project\nname = "test"\n')  # Missing closing bracket
        
        with pytest.raises(Exception):  # Should raise a parsing error
            load_project_file(malformed_file)
    
    def test_pyproject_file_not_found(self, temp_dir):
        """Test that unsupported file error is raised even for nonexistent files."""
        nonexistent = os.path.join(temp_dir, 'nonexistent.txt')
        
        with pytest.raises(ValueError, match='Unsupported file type'):
            load_project_file(nonexistent)


class TestLoadPackageJson:
    """Tests for package.json loading via load_project_file."""
    
    def test_load_valid_package_json(self, sample_package_json):
        """Test loading valid package.json."""
        result = load_project_file(sample_package_json)
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert result['name'] == 'test-project'
    
    def test_load_complex_package_json(self, complex_package_json):
        """Test loading complex package.json."""
        result = load_project_file(complex_package_json)
        
        assert result['name'] == 'complex-project'
        assert 'dependencies' in result
        assert 'devDependencies' in result
    
    def test_package_json_with_utf8_characters(self, temp_dir):
        """Test loading package.json with UTF-8 characters."""
        content = {
            "name": "test",
            "description": "Test with unicode: 你好 мир",
            "author": "José García"
        }
        json_file = os.path.join(temp_dir, 'package.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False)
        
        result = load_project_file(json_file)
        
        assert '你好' in result['description']
    
    def test_malformed_json(self, temp_dir):
        """Test error with malformed JSON."""
        malformed_file = os.path.join(temp_dir, 'package.json')
        with open(malformed_file, 'w') as f:
            f.write('{"name": "test", invalid json}')
        
        with pytest.raises(json.JSONDecodeError):
            load_project_file(malformed_file)
    
    def test_empty_json_file(self, temp_dir):
        """Test error with empty JSON file."""
        empty_file = os.path.join(temp_dir, 'package.json')
        Path(empty_file).touch()
        
        with pytest.raises(json.JSONDecodeError):
            load_project_file(empty_file)
    
    def test_json_array_instead_of_object(self, temp_dir):
        """Test loading JSON array (valid JSON but not standard package.json)."""
        array_file = os.path.join(temp_dir, 'package.json')
        with open(array_file, 'w') as f:
            json.dump(['item1', 'item2'], f)
        
        result = load_project_file(array_file)
        
        # Should load successfully but return a list
        assert isinstance(result, list)
    
    def test_package_json_file_not_found(self, temp_dir):
        """Test that pyproject/package.json files are checked before existence."""
        # Create a valid pyproject.toml file to test FileNotFoundError
        pyproject_file = os.path.join(temp_dir, 'pyproject.toml')
        with open(pyproject_file, 'w') as f:
            f.write('[project]\nname = "test"\n')
        
        # Now delete it to test file not found error
        os.remove(pyproject_file)
        
        with pytest.raises(FileNotFoundError):
            load_project_file(pyproject_file)


class TestFilesLoadersDict:
    """Tests for FilesLoaders dictionary."""
    
    def test_files_loaders_contains_expected_keys(self):
        """Test that FilesLoaders has expected keys."""
        assert 'pyproject.toml' in FilesLoaders
        assert 'package.json' in FilesLoaders
    
    def test_files_loaders_values_are_callable(self):
        """Test that all values in FilesLoaders are callable."""
        for loader in FilesLoaders.values():
            assert callable(loader)
    
    def test_files_loaders_correct_size(self):
        """Test that FilesLoaders has exactly 2 entries."""
        assert len(FilesLoaders) == 2


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_end_to_end_pyproject_workflow(self, sample_pyproject):
        """Test complete workflow with pyproject.toml."""
        # Check if it's a project file
        assert is_project_file(sample_pyproject) is True
        
        # Load the project file
        result = load_project_file(sample_pyproject)
        
        assert result['name'] == 'test-project'
    
    def test_end_to_end_package_workflow(self, sample_package_json):
        """Test complete workflow with package.json."""
        # Check if it's a project file
        assert is_project_file(sample_package_json) is True
        
        # Load the project file
        result = load_project_file(sample_package_json)
        
        assert result['name'] == 'test-project'
    
    def test_load_multiple_different_file_types(self, sample_pyproject, sample_package_json):
        """Test loading both file types."""
        pyproject_result = load_project_file(sample_pyproject)
        package_result = load_project_file(sample_package_json)
        
        assert pyproject_result['name'] == 'test-project'
        assert package_result['name'] == 'test-project'
        assert isinstance(pyproject_result, dict)
        assert isinstance(package_result, dict)
    
    def test_is_project_file_before_load(self, sample_pyproject):
        """Test checking if file is project file before loading."""
        if is_project_file(sample_pyproject):
            result = load_project_file(sample_pyproject)
            assert result is not None
        else:
            pytest.fail("Should be recognized as project file")


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_pyproject_with_only_project_section_empty(self, temp_dir):
        """Test pyproject.toml with empty [project] section."""
        empty_project_file = os.path.join(temp_dir, 'pyproject.toml')
        with open(empty_project_file, 'w') as f:
            f.write('[project]\n')
        
        result = load_project_file(empty_project_file)
        
        assert isinstance(result, dict)
        assert len(result) == 0
    
    def test_package_json_with_empty_object(self, temp_dir):
        """Test package.json with empty object."""
        empty_json_file = os.path.join(temp_dir, 'package.json')
        with open(empty_json_file, 'w') as f:
            json.dump({}, f)
        
        result = load_project_file(empty_json_file)
        
        assert isinstance(result, dict)
        assert len(result) == 0
    
    def test_filename_with_pyproject_in_path(self, temp_dir):
        """Test file where pyproject appears in path but not as filename."""
        sub_dir = os.path.join(temp_dir, 'pyproject_stuff')
        os.makedirs(sub_dir)
        file_path = os.path.join(sub_dir, 'config.txt')
        Path(file_path).touch()
        
        assert is_project_file(file_path) is False
    
    def test_filename_with_package_in_path(self, temp_dir):
        """Test file where package appears in path but not as filename."""
        sub_dir = os.path.join(temp_dir, 'package_dir')
        os.makedirs(sub_dir)
        file_path = os.path.join(sub_dir, 'config.txt')
        Path(file_path).touch()
        
        assert is_project_file(file_path) is False
    
    def test_pyproject_with_special_encoding(self, temp_dir):
        """Test pyproject.toml with special characters in values."""
        special_file = os.path.join(temp_dir, 'pyproject.toml')
        with open(special_file, 'w', encoding='utf-8') as f:
            f.write('[project]\nname = "test-ñ-project"\n')
        
        result = load_project_file(special_file)
        assert 'ñ' in result['name']


class TestErrorMessages:
    """Tests for error messages and diagnostics."""
    
    def test_unsupported_file_error_includes_filename(self, temp_dir):
        """Test that unsupported file error includes the filename."""
        unknown_file = os.path.join(temp_dir, 'unknown.xyz')
        Path(unknown_file).touch()
        
        with pytest.raises(ValueError) as excinfo:
            load_project_file(unknown_file)
        
        assert 'unknown.xyz' in str(excinfo.value)
    
    def test_missing_project_section_error(self, temp_dir):
        """Test error message for missing [project] section."""
        no_project_file = os.path.join(temp_dir, 'pyproject.toml')
        with open(no_project_file, 'w') as f:
            f.write('[tool]\n')
        
        with pytest.raises(ValueError) as excinfo:
            load_project_file(no_project_file)
        
        assert '[project]' in str(excinfo.value)
