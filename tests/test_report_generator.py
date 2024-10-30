import pytest
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone

from src.report_generator import ReportGenerator

@pytest.fixture
def temp_output_dir():
    """Create temporary directory for test outputs"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_results() -> tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """Provide sample test results"""
    url = "http://example.com"
    
    normalized_results = [
        {
            "message": "Image missing alt text",
            "level": 1,
            "tools": ["axe"],
            "selector": "img.hero",
            "context": "<img class='hero' src='test.jpg'>",
            "type": "error"
        },
        {
            "message": "Color contrast could be improved",
            "level": 2,
            "tools": ["axe"],
            "selector": "p.text",
            "context": "<p class='text'>Test</p>",
            "type": "warning"
        },
        {
            "message": "Consider adding ARIA landmarks",
            "level": 3,
            "tools": ["axe"],
            "selector": "div.content",
            "context": "<div class='content'>Content</div>",
            "type": "notice"
        }
    ]
    
    crew_results = {
        "wcag_analysis": {
            "issues": [
                {
                    "message": "Image missing alt text",
                    "level": 1,
                    "tools": ["axe"],
                    "wcag_mapping": {
                        "criterion_id": "1.1.1",
                        "title": "Non-text Content",
                        "level": "A",
                        "description": "All non-text content has text alternative",
                        "documentation_links": {
                            "understanding": "https://example.com/understanding",
                            "how_to_meet": "https://example.com/how-to-meet"
                        }
                    }
                },
                {
                    "message": "Color contrast could be improved",
                    "level": 2,
                    "tools": ["axe"],
                    "wcag_mapping": {
                        "criterion_id": "1.4.3",
                        "title": "Contrast (Minimum)",
                        "level": "AA",
                        "description": "Visual presentation of text has sufficient contrast",
                        "documentation_links": {
                            "understanding": "https://example.com/understanding",
                            "how_to_meet": "https://example.com/how-to-meet"
                        }
                    }
                },
                {
                    "message": "Consider adding ARIA landmarks",
                    "level": 3,
                    "tools": ["axe"],
                    "wcag_mapping": {
                        "criterion_id": "4.1.1",
                        "title": "Parsing",
                        "level": "A",
                        "description": "Use of ARIA landmarks improves navigation",
                        "documentation_links": {
                            "understanding": "https://example.com/understanding",
                            "how_to_meet": "https://example.com/how-to-meet"
                        }
                    }
                }
            ],
            "summary": {
                "total_issues": 3,
                "by_level": {"A": 2, "AA": 1},
                "by_principle": {"1": 2, "4": 1},
                "coverage": ["1.1.1", "1.4.3", "4.1.1"]
            }
        }
    }
    
    return url, normalized_results, crew_results

@pytest.mark.asyncio
async def test_save_results_creates_all_files(
    temp_output_dir: Path,
    sample_results: tuple[str, List[Dict[str, Any]], Dict[str, Any]]
):
    """Test that save_results creates all expected output files"""
    url, normalized_results, crew_results = sample_results
    
    # Monkeypatch output directory in ReportGenerator
    report_generator = ReportGenerator()
    
    # Save results
    output_dir = await report_generator.save_results(
        url=url,
        normalized_results=normalized_results,
        crew_results=crew_results
    )
    
    # Check if output directory exists
    assert output_dir.exists()
    assert output_dir.is_dir()
    
    # Check for required files
    expected_files = [
        "normalized_results.json",
        "wcag_analysis.json",
        "crew_analysis.json",
        "report.html",
        "wcag_summary.json"
    ]
    
    for file_name in expected_files:
        file_path = output_dir / file_name
        assert file_path.exists(), f"Missing file: {file_name}"
        assert file_path.is_file(), f"Not a file: {file_name}"
        
    # Validate JSON content
    with open(output_dir / "normalized_results.json", 'r', encoding='utf-8') as f:
        saved_normalized = json.load(f)
        assert saved_normalized == normalized_results
        
    with open(output_dir / "crew_analysis.json", 'r', encoding='utf-8') as f:
        saved_crew = json.load(f)
        assert saved_crew == crew_results
        
    # Check HTML report content
    with open(output_dir / "report.html", 'r', encoding='utf-8') as f:
        html_content = f.read()
        assert "WCAG 2.2 Test Results" in html_content
        assert "Image missing alt text" in html_content
        assert "Non-text Content" in html_content

@pytest.mark.asyncio
async def test_save_results_error_case(
    temp_output_dir: Path,
    sample_results: tuple[str, List[Dict[str, Any]], Dict[str, Any]]
):
    """Test save_results handling of error cases"""
    url, normalized_results, _ = sample_results
    
    # Create error results
    error_results = {
        "error": "Test error message",
        "status": "error"
    }
    
    report_generator = ReportGenerator()
    
    # Save error results
    output_dir = await report_generator.save_results(
        url=url,
        normalized_results=normalized_results,
        crew_results=error_results
    )
    
    # Check if output directory exists
    assert output_dir.exists()
    assert output_dir.is_dir()
    
    # Check for required files in error case
    expected_files = [
        "normalized_results.json",
        "crew_analysis.json",
        "report.html"
    ]
    
    for file_name in expected_files:
        file_path = output_dir / file_name
        assert file_path.exists(), f"Missing file: {file_name}"
        
    # Validate error content
    with open(output_dir / "crew_analysis.json", 'r', encoding='utf-8') as f:
        saved_error = json.load(f)
        assert saved_error["error"] == "Test error message"
        assert saved_error["status"] == "error"

@pytest.mark.asyncio
async def test_save_results_automated_only(
    temp_output_dir: Path,
    sample_results: tuple[str, List[Dict[str, Any]], Dict[str, Any]]
):
    """Test save_results for automated testing only case"""
    url, normalized_results, _ = sample_results
    
    # Create automated-only results
    automated_results = {
        "status": "automated_only"
    }
    
    report_generator = ReportGenerator()
    
    # Save automated-only results
    output_dir = await report_generator.save_results(
        url=url,
        normalized_results=normalized_results,
        crew_results=automated_results
    )
    
    # Check if output directory exists
    assert output_dir.exists()
    assert output_dir.is_dir()
    
    # Check for required files
    expected_files = [
        "normalized_results.json",
        "crew_analysis.json",
        "report.html"
    ]
    
    for file_name in expected_files:
        file_path = output_dir / file_name
        assert file_path.exists(), f"Missing file: {file_name}"
        
    # Validate automated-only content
    with open(output_dir / "crew_analysis.json", 'r', encoding='utf-8') as f:
        saved_results = json.load(f)
        assert saved_results["status"] == "automated_only"

@pytest.mark.asyncio
async def test_save_results_file_content_validity(
    temp_output_dir: Path,
    sample_results: tuple[str, List[Dict[str, Any]], Dict[str, Any]]
):
    """Test the validity of saved file contents"""
    url, normalized_results, crew_results = sample_results
    
    report_generator = ReportGenerator()
    output_dir = await report_generator.save_results(
        url=url,
        normalized_results=normalized_results,
        crew_results=crew_results
    )
    
    # Check WCAG summary content
    if crew_results.get("wcag_analysis"):
        with open(output_dir / "wcag_summary.json", 'r', encoding='utf-8') as f:
            summary = json.load(f)
            assert "url" in summary
            assert "timestamp" in summary
            assert "wcag_summary" in summary
            assert "coverage" in summary
            
            # Validate timestamp format
            timestamp = datetime.fromisoformat(summary["timestamp"].replace('Z', '+00:00'))
            assert isinstance(timestamp, datetime)
            
            # Validate coverage structure
            coverage = summary["coverage"]
            assert "tested_criteria" in coverage
            assert "total_issues" in coverage
            assert "by_level" in coverage
            assert "by_principle" in coverage
    
    # Check HTML report structure
    with open(output_dir / "report.html", 'r', encoding='utf-8') as f:
        html_content = f.read()
        
        # Check basic HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "<html lang=\"de\">" in html_content
        assert "<head>" in html_content
        assert "<body>" in html_content
        
        # Check for required sections
        assert "WCAG 2.2 Test Results" in html_content
        assert "Zusammenfassung" in html_content
        assert "Detaillierte Ergebnisse" in html_content
        
        # Check for styling
        assert "<style>" in html_content
        assert "class=\"error\"" in html_content
        assert "class=\"warning\"" in html_content
        assert "class=\"notice\"" in html_content