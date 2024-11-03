import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch
from src.wcag.wcag_reference_processor import WCAGReferenceProcessor

@pytest.fixture
def sample_wcag_data():
    return [
        {
            "id": "1.1.1",
            "title": "Non-text Content",
            "description": "All non-text content has a text alternative",
            "level": "A",
            "tool_codes": ["wcag111", "image-alt"],
            "understanding_url": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
            "how_to_meet_url": "https://www.w3.org/WAI/WCAG21/quickref/#non-text-content"
        },
        {
            "id": "1.2.1",
            "title": "Audio-only and Video-only",
            "description": "Prerecorded audio-only and video-only content has alternatives",
            "level": "A",
            "tool_codes": ["wcag121", "media-alt"],
            "understanding_url": "https://www.w3.org/WAI/WCAG21/Understanding/audio-only-and-video-only-prerecorded.html",
            "how_to_meet_url": "https://www.w3.org/WAI/WCAG21/quickref/#audio-only-and-video-only-prerecorded"
        }
    ]

@pytest.fixture
def wcag_processor(tmp_path, sample_wcag_data):
    # Create a temporary WCAG JSON file
    wcag_file = tmp_path / "wcag.json"
    wcag_file.write_text(json.dumps(sample_wcag_data))
    
    # Initialize processor with the temporary file
    processor = WCAGReferenceProcessor(wcag_json_path=wcag_file)
    return processor

@pytest.mark.asyncio
async def test_initialization(wcag_processor):
    """Test successful initialization of WCAGReferenceProcessor"""
    assert wcag_processor.wcag_data is not None
    assert len(wcag_processor.id_map) == 2
    assert len(wcag_processor.code_map) == 4  # Each criterion has 2 tool codes

def test_initialization_with_invalid_path():
    """Test initialization with non-existent file"""
    with pytest.raises(FileNotFoundError):
        WCAGReferenceProcessor(wcag_json_path="nonexistent/path/wcag.json")

def test_find_criterion_by_code(wcag_processor):
    """Test finding WCAG criterion by tool-specific code"""
    # Test with existing code
    criterion = wcag_processor.find_criterion_by_code("image-alt")
    assert criterion is not None
    assert criterion["id"] == "1.1.1"
    
    # Test with non-existent code
    criterion = wcag_processor.find_criterion_by_code("nonexistent-code")
    assert criterion is None

@pytest.mark.asyncio
async def test_search_by_description(wcag_processor, monkeypatch):
    """Test searching WCAG criteria by description"""
    mock_result = [{
        "id": "1.1.1",
        "title": "Non-text Content",
        "relevance_score": 0.95
    }]
    
    async def mock_query(*args, **kwargs):
        return mock_result
    
    # Mock the query method instead of run
    monkeypatch.setattr(wcag_processor.json_search, "query", mock_query)
    results = await wcag_processor.search_by_description("Image missing alt text")
    assert len(results) == 1
    assert results[0]["id"] == "1.1.1"

def test_get_criterion_details(wcag_processor):
    """Test getting detailed information for a specific WCAG criterion"""
    # Test with existing criterion
    details = wcag_processor.get_criterion_details("1.1.1")
    assert details["id"] == "1.1.1"
    assert details["title"] == "Non-text Content"
    assert "documentation_links" in details
    
    # Test with non-existent criterion
    details = wcag_processor.get_criterion_details("nonexistent")
    assert details == {}

@pytest.mark.asyncio
async def test_error_handling_in_search(wcag_processor, monkeypatch):
    """Test error handling during search"""
    async def mock_query(*args, **kwargs):
        raise Exception("Search failed")
    
    # Mock the query method instead of run
    monkeypatch.setattr(wcag_processor.json_search, "query", mock_query)
    results = await wcag_processor.search_by_description("test")
    assert results == []

def test_case_insensitive_code_lookup(wcag_processor):
    """Test that tool code lookup is case insensitive"""
    upper_case = wcag_processor.find_criterion_by_code("IMAGE-ALT")
    lower_case = wcag_processor.find_criterion_by_code("image-alt")
    assert upper_case == lower_case
    assert upper_case is not None 