import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from typing import List, Dict, Any, Optional

from src.report_generator import ReportGenerator

@pytest.fixture
def report_generator():
    """Create a ReportGenerator instance for testing"""
    return ReportGenerator()

@pytest.fixture
def sample_test_results():
    """Provide sample test results"""
    return {
        "normalized_results": [
            {
                "tool": "axe",
                "type": "error",
                "code": "WCAG2AA.1.1.1",
                "message": "Images must have alternate text",
                "context": "<img src='test.jpg'>",
                "selector": "img#test",
            }
        ]
    }

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)

class TestReportGenerator:
    
    def test_initialization(self, report_generator):
        """Test ReportGenerator initialization"""
        assert report_generator.logger is not None
        assert report_generator.wcag_mapper is not None
        assert report_generator.template_path == Path("templates")
        assert report_generator.css_path == Path("templates/report_styles.css")
        assert report_generator.output_base_path == Path("output/results")

    def test_generate_html_report(self, report_generator, sample_test_results):
        """Test HTML report generation includes error messages"""
        config = {"url": "http://test.com"}
        html = report_generator.generate_html_report(sample_test_results, config)
        assert 'Images must have alternate text' in html

    def test_display_results_summary(self, report_generator, sample_test_results):
        """Test results summary display"""
        with patch('builtins.print') as mock_print:
            report_generator.display_results_summary(sample_test_results["normalized_results"])
            mock_print.assert_any_call("Errors: 1")

    @pytest.mark.asyncio
    async def test_save_results(self, report_generator, sample_test_results, temp_dir):
        """Test saving results to files"""
        with patch.object(report_generator, 'output_base_path', temp_dir):
            url = "https://example.com"
            output_dir = await report_generator.save_results(
                url, 
                sample_test_results["normalized_results"]
            )
            
            # Check if files were created
            assert (output_dir / "normalized_results.json").exists()
            assert (output_dir / "report.html").exists()

    def test_sanitize_url_for_filename(self, report_generator):
        """Test URL sanitization for filenames"""
        url = "http://test.com/path?query=1"
        result = report_generator._sanitize_url_for_filename(url)
        assert result == "test.com_path_query_1"

    def test_get_status_class(self, report_generator):
        """Test status class determination"""
        assert report_generator._get_status_class("Pass") == "success"
        assert report_generator._get_status_class("Fail") == "error"
        assert report_generator._get_status_class("Not Applicable") == "notice"
        assert report_generator._get_status_class("Unknown") == "notice"

    def test_get_severity_class(self, report_generator):
        """Test severity class determination"""
        assert report_generator._get_severity_class(1) == "critical"
        assert report_generator._get_severity_class(2) == "serious"
        assert report_generator._get_severity_class(3) == "moderate"
        assert report_generator._get_severity_class(4) == "minor"
        assert report_generator._get_severity_class(5) == "moderate"  # fallback

    def test_error_handling(self, report_generator):
        """Test error handling in report generation"""
        invalid_results = {"invalid": "data"}
        config = {"url": "https://example.com"}
        
        html_report = report_generator.generate_html_report(invalid_results, config)
        assert "Error in Report Generation" in html_report
        assert "Please check the input data" in html_report

    @pytest.mark.asyncio
    async def test_save_results_error_handling(self, report_generator, temp_dir):
        """Test error handling when saving results"""
        with patch.object(report_generator, 'output_base_path', temp_dir):
            with pytest.raises(Exception):
                await report_generator.save_results(
                    "https://example.com",
                    None  # Invalid results
                )

    def test_css_loading(self, report_generator, temp_dir):
        """Test CSS loading functionality"""
        # Test with missing CSS file
        css = report_generator._get_css_styles()
        assert "body {" in css
        assert "font-family" in css
        
        # Test with custom CSS file
        test_css = "body { background: red; }"
        css_path = temp_dir / "report_styles.css"
        css_path.write_text(test_css)
        
        with patch.object(report_generator, 'css_path', css_path):
            loaded_css = report_generator._get_css_styles()
            assert test_css in loaded_css

    def test_generate_wcag_details(self, report_generator):
        """Test WCAG details generation"""
        test_results = {
            "results": {
                "1": {
                    "name": "Perceivable",
                    "criteria": {
                        "1.1.1": {
                            "title": "Non-text Content",
                            "level": "A",
                            "status": "Fail",
                            "description": "Test description",
                            "issues": [
                                {
                                    "description": "Missing alt text",
                                    "severity": 1,
                                    "selector": "img#test"
                                }
                            ]
                        }
                    },
                    "failed": 1,
                    "total_issues": 1
                }
            }
        }
        
        wcag_details = report_generator._generate_wcag_details(test_results)
        assert "Perceivable" in wcag_details
        assert "Non-text Content" in wcag_details
        assert "Missing alt text" in wcag_details
        assert "img#test" in wcag_details

    def _sanitize_url_for_filename(self, url: str) -> str:
        """Convert URL to safe filename string"""
        # Remove protocol
        url = url.split('://')[-1]
        # Replace unsafe characters
        unsafe_chars = '<>:"/\\|?*='
        for char in unsafe_chars:
            url = url.replace(char, '_')
        return url[:50]  # Limit length

    async def save_results(self, url: str, normalized_results: list) -> None:
        if not normalized_results:
            raise Exception("No results to save")
        # Implementation...

    def display_results_summary(self, normalized_results: list) -> None:
        if not normalized_results:
            print("\nNo results to display")
            return
        error_count = sum(1 for r in normalized_results if r.get("type") == "error")
        # Rest of implementation...

    @pytest.mark.asyncio
    async def test_save_results(self, report_generator, sample_test_results):
        """Test save_results method"""
        url = "http://test.com"
        with pytest.raises(Exception):
            await report_generator.save_results(url, sample_test_results["normalized_results"])

    @pytest.mark.asyncio
    async def test_save_results_error_handling(self, report_generator):
        """Test save_results error handling"""
        url = "http://test.com"
        with pytest.raises(Exception):
            await report_generator.save_results(url, [])