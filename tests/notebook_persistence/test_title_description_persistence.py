"""
Test suite for notebook title and description persistence.

This test suite verifies that notebook title and description are properly:
1. Created with default or provided values
2. Updated via the API
3. Serialized to JSON files
4. Deserialized when loading notebooks
5. Persisted across save/load cycles
"""

import pytest
import json
from pathlib import Path
from uuid import uuid4
from backend.app.models.notebook import Notebook, NotebookCreateRequest, NotebookUpdateRequest
from backend.app.services.notebook_service import NotebookService


class TestNotebookTitleDescriptionPersistence:
    """Test title and description handling throughout the entire save/load pipeline."""

    @pytest.fixture
    def notebook_service(self, tmp_path):
        """Create a notebook service with a temporary notebooks directory."""
        notebooks_dir = tmp_path / "notebooks"
        notebooks_dir.mkdir()
        service = NotebookService()
        service.notebooks_dir = notebooks_dir
        service._notebooks = {}
        return service

    def test_create_notebook_with_default_values(self, notebook_service):
        """Test creating a notebook with default title and description."""
        request = NotebookCreateRequest()
        notebook = notebook_service.create_notebook(request)

        assert notebook.title == "Untitled Digital Article"
        assert notebook.description == ""
        assert notebook.id is not None

    def test_create_notebook_with_custom_values(self, notebook_service):
        """Test creating a notebook with custom title and description."""
        request = NotebookCreateRequest(
            title="My Research Analysis",
            description="Analysis of gene expression data from experiment XYZ"
        )
        notebook = notebook_service.create_notebook(request)

        assert notebook.title == "My Research Analysis"
        assert notebook.description == "Analysis of gene expression data from experiment XYZ"

    def test_update_notebook_title(self, notebook_service):
        """Test updating only the title."""
        # Create notebook
        request = NotebookCreateRequest(
            title="Original Title",
            description="Original Description"
        )
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Update title
        update_request = NotebookUpdateRequest(title="Updated Title")
        updated = notebook_service.update_notebook(notebook_id, update_request)

        assert updated.title == "Updated Title"
        assert updated.description == "Original Description"  # Should not change

    def test_update_notebook_description(self, notebook_service):
        """Test updating only the description."""
        # Create notebook
        request = NotebookCreateRequest(
            title="My Title",
            description="Original Description"
        )
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Update description
        update_request = NotebookUpdateRequest(
            description="This is a much longer description with multiple sentences. "
                        "It describes the purpose of the analysis in detail."
        )
        updated = notebook_service.update_notebook(notebook_id, update_request)

        assert updated.title == "My Title"  # Should not change
        assert "longer description" in updated.description

    def test_update_both_title_and_description(self, notebook_service):
        """Test updating both title and description simultaneously."""
        # Create notebook
        request = NotebookCreateRequest()
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Update both
        update_request = NotebookUpdateRequest(
            title="Final Title",
            description="Final Description"
        )
        updated = notebook_service.update_notebook(notebook_id, update_request)

        assert updated.title == "Final Title"
        assert updated.description == "Final Description"

    def test_serialization_to_json(self, notebook_service):
        """Test that title and description are properly serialized to JSON files."""
        # Create notebook with custom values
        request = NotebookCreateRequest(
            title="Test Notebook for Serialization",
            description="This description should appear in the JSON file"
        )
        notebook = notebook_service.create_notebook(request)

        # Read the JSON file directly
        notebook_file = notebook_service.notebooks_dir / f"{notebook.id}.json"
        assert notebook_file.exists()

        with open(notebook_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data['title'] == "Test Notebook for Serialization"
        assert data['description'] == "This description should appear in the JSON file"
        assert data['id'] == str(notebook.id)

    def test_deserialization_from_json(self, notebook_service):
        """Test that title and description are properly restored when loading from JSON."""
        # Create and save a notebook
        request = NotebookCreateRequest(
            title="Notebook to Load",
            description="Description to be restored"
        )
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Clear the in-memory cache
        notebook_service._notebooks = {}

        # Load from disk
        notebook_service._load_notebooks()

        # Retrieve the loaded notebook
        loaded = notebook_service.get_notebook(notebook_id)
        assert loaded is not None
        assert loaded.title == "Notebook to Load"
        assert loaded.description == "Description to be restored"

    def test_unicode_characters_in_title(self, notebook_service):
        """Test that Unicode characters are preserved in title."""
        request = NotebookCreateRequest(
            title="分析结果 - Analysis 🔬",
            description="测试 Unicode support"
        )
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Reload from disk
        notebook_service._notebooks = {}
        notebook_service._load_notebooks()

        loaded = notebook_service.get_notebook(notebook_id)
        assert loaded.title == "分析结果 - Analysis 🔬"
        assert loaded.description == "测试 Unicode support"

    def test_multiline_description(self, notebook_service):
        """Test that multiline descriptions are preserved."""
        multiline_desc = """This is a multiline description.

It has multiple paragraphs.

And should be preserved exactly."""

        request = NotebookCreateRequest(
            title="Multiline Test",
            description=multiline_desc
        )
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Reload from disk
        notebook_service._notebooks = {}
        notebook_service._load_notebooks()

        loaded = notebook_service.get_notebook(notebook_id)
        assert loaded.description == multiline_desc
        assert "\n\n" in loaded.description

    def test_empty_description_allowed(self, notebook_service):
        """Test that empty description is a valid state."""
        request = NotebookCreateRequest(
            title="Notebook with Empty Description",
            description=""
        )
        notebook = notebook_service.create_notebook(request)

        assert notebook.description == ""

        # Verify it persists
        notebook_id = str(notebook.id)
        notebook_service._notebooks = {}
        notebook_service._load_notebooks()

        loaded = notebook_service.get_notebook(notebook_id)
        assert loaded.description == ""

    def test_very_long_description(self, notebook_service):
        """Test that very long descriptions are handled properly."""
        long_description = "This is a very long description. " * 100  # ~3000 characters

        request = NotebookCreateRequest(
            title="Long Description Test",
            description=long_description
        )
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        assert len(notebook.description) > 2500

        # Reload and verify
        notebook_service._notebooks = {}
        notebook_service._load_notebooks()

        loaded = notebook_service.get_notebook(notebook_id)
        assert loaded.description == long_description

    def test_multiple_updates_preserve_latest(self, notebook_service):
        """Test that multiple rapid updates preserve the latest values."""
        request = NotebookCreateRequest()
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Multiple updates
        for i in range(5):
            update_request = NotebookUpdateRequest(
                title=f"Title Version {i}",
                description=f"Description Version {i}"
            )
            notebook_service.update_notebook(notebook_id, update_request)

        # Reload from disk
        notebook_service._notebooks = {}
        notebook_service._load_notebooks()

        loaded = notebook_service.get_notebook(notebook_id)
        assert loaded.title == "Title Version 4"
        assert loaded.description == "Description Version 4"

    def test_updated_at_timestamp_changes(self, notebook_service):
        """Test that updated_at timestamp changes when title/description are updated."""
        request = NotebookCreateRequest(
            title="Original",
            description="Original"
        )
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)
        original_updated_at = notebook.updated_at

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        # Update title
        update_request = NotebookUpdateRequest(title="Updated")
        updated = notebook_service.update_notebook(notebook_id, update_request)

        assert updated.updated_at > original_updated_at

    def test_title_and_description_in_notebook_list(self, notebook_service):
        """Test that title and description are available when listing all notebooks."""
        # Create multiple notebooks
        request1 = NotebookCreateRequest(
            title="Notebook 1",
            description="Description 1"
        )
        request2 = NotebookCreateRequest(
            title="Notebook 2",
            description="Description 2"
        )

        nb1 = notebook_service.create_notebook(request1)
        nb2 = notebook_service.create_notebook(request2)

        # List all notebooks
        all_notebooks = notebook_service.list_notebooks()

        assert len(all_notebooks) == 2
        titles = {nb.title for nb in all_notebooks}
        assert "Notebook 1" in titles
        assert "Notebook 2" in titles

    def test_special_characters_in_title(self, notebook_service):
        """Test that special characters are handled properly."""
        special_title = 'Title with "quotes" and \'apostrophes\' & <symbols>'

        request = NotebookCreateRequest(
            title=special_title,
            description="Description with special chars: \n\t\r"
        )
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Reload from disk
        notebook_service._notebooks = {}
        notebook_service._load_notebooks()

        loaded = notebook_service.get_notebook(notebook_id)
        assert loaded.title == special_title


class TestNotebookUpdateValidation:
    """Test validation and edge cases for notebook updates."""

    @pytest.fixture
    def notebook_service(self, tmp_path):
        """Create a notebook service with a temporary notebooks directory."""
        notebooks_dir = tmp_path / "notebooks"
        notebooks_dir.mkdir()
        service = NotebookService()
        service.notebooks_dir = notebooks_dir
        service._notebooks = {}
        return service

    def test_update_nonexistent_notebook(self, notebook_service):
        """Test updating a notebook that doesn't exist."""
        fake_id = str(uuid4())
        update_request = NotebookUpdateRequest(title="Should Fail")

        result = notebook_service.update_notebook(fake_id, update_request)
        assert result is None

    def test_partial_update_preserves_other_fields(self, notebook_service):
        """Test that partial updates don't affect other metadata fields."""
        request = NotebookCreateRequest(
            title="Original Title",
            description="Original Description",
            author="John Doe",
            llm_model="gpt-4",
            llm_provider="openai"
        )
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Update only title
        update_request = NotebookUpdateRequest(title="New Title")
        updated = notebook_service.update_notebook(notebook_id, update_request)

        # All other fields should remain unchanged
        assert updated.title == "New Title"
        assert updated.description == "Original Description"
        assert updated.author == "John Doe"
        assert updated.llm_model == "gpt-4"
        assert updated.llm_provider == "openai"

    def test_whitespace_only_title_handling(self, notebook_service):
        """Test how whitespace-only titles are handled."""
        request = NotebookCreateRequest()
        notebook = notebook_service.create_notebook(request)
        notebook_id = str(notebook.id)

        # Try to update with whitespace-only title
        # Note: The frontend trims, but backend should accept it
        update_request = NotebookUpdateRequest(title="   ")
        updated = notebook_service.update_notebook(notebook_id, update_request)

        # Backend accepts it as-is (frontend should trim before sending)
        assert updated.title == "   "


class TestJSONFileStructure:
    """Test the structure and integrity of JSON files."""

    @pytest.fixture
    def notebook_service(self, tmp_path):
        """Create a notebook service with a temporary notebooks directory."""
        notebooks_dir = tmp_path / "notebooks"
        notebooks_dir.mkdir()
        service = NotebookService()
        service.notebooks_dir = notebooks_dir
        service._notebooks = {}
        return service

    def test_json_file_contains_all_required_fields(self, notebook_service):
        """Test that JSON files contain all required fields."""
        request = NotebookCreateRequest(
            title="Complete Notebook",
            description="Complete Description"
        )
        notebook = notebook_service.create_notebook(request)

        # Read JSON file
        notebook_file = notebook_service.notebooks_dir / f"{notebook.id}.json"
        with open(notebook_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check all required fields are present
        required_fields = [
            'id', 'title', 'description', 'created_at', 'updated_at',
            'cells', 'author', 'version', 'tags', 'metadata',
            'llm_model', 'llm_provider'
        ]

        for field in required_fields:
            assert field in data, f"Field '{field}' missing from JSON"

    def test_json_file_uses_utf8_encoding(self, notebook_service):
        """Test that JSON files are saved with UTF-8 encoding."""
        request = NotebookCreateRequest(
            title="Тест Unicode 测试 🔬",
            description="Arabic: العربية, Hebrew: עברית, Emoji: 🧬🔬📊"
        )
        notebook = notebook_service.create_notebook(request)

        # Read raw bytes from file
        notebook_file = notebook_service.notebooks_dir / f"{notebook.id}.json"
        with open(notebook_file, 'rb') as f:
            raw_content = f.read()

        # Should be valid UTF-8
        content = raw_content.decode('utf-8')
        assert "Тест" in content
        assert "测试" in content
        assert "🔬" in content

    def test_json_file_is_properly_formatted(self, notebook_service):
        """Test that JSON files are properly indented and formatted."""
        request = NotebookCreateRequest(
            title="Formatted Notebook",
            description="Test formatting"
        )
        notebook = notebook_service.create_notebook(request)

        # Read raw file content
        notebook_file = notebook_service.notebooks_dir / f"{notebook.id}.json"
        with open(notebook_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have indentation (not minified)
        assert '\n' in content
        assert '  ' in content  # 2-space indentation
