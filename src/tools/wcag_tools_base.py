from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging
from datetime import datetime, timezone
from typing_extensions import TypedDict
from playwright.async_api import async_playwright
import json
import traceback

from src.logging_config import get_logger
from src.tools.wcag_analyzers import (
    HTMLAnalyzer, 
    Pa11yAnalyzer, 
    AxeAnalyzer, 
    LighthouseAnalyzer
)
from src.tools.result_processor import TestResultProcessor

class TestResult(TypedDict):
    status: str
    message: Optional[str]
    tool: str
    results: Union[List[Any], Dict[str, Any]]
    url: Optional[str]
    timestamp: str

class WCAGTestingToolsBase:
    """
    Base class for WCAG testing tools integration.
    Provides core functionality and initialization.
    """

    def __init__(self, output_dir: str = "output/tool_results"):
        """
        Initialize WCAG testing tools base
        
        Args:
            output_dir: Directory for saving test results
        """
        # Create required directories
        self.results_path = Path(output_dir)
        self.log_path = Path("output/results/logs")
        
        # Create directories
        for path in [self.results_path, self.log_path]:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Error creating directory {path}: {e}")
                raise

        # Initialize logger using the centralized logging configuration        
        self.logger = get_logger('WCAGTestingTools', log_dir=str(self.log_path))

        self.error_handler = self._setup_error_handler()
        self.result_processor = TestResultProcessor()

    def _setup_error_handler(self):
        """Setup enhanced error handling"""
        def handler(exctype, value, traceback):
            error_details = {
                "type": str(exctype.__name__),
                "message": str(value),
                "traceback": self._format_traceback(traceback),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            error_file = self.log_path / f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_details, f, indent=2, ensure_ascii=False)
            
            self.logger.error(f"Error occurred: {error_details['message']}")
            return error_details

        return handler

    def _format_traceback(self, tb):
        """Format traceback information"""
        return [
            {
                "filename": frame.filename,
                "line": frame.lineno,
                "function": frame.name,
                "code": frame.line
            }
            for frame in traceback.extract_tb(tb)
        ]

    def _validate_results_format(self, results: Dict[str, Any]) -> bool:
        """
        Validate the format of test results
        
        Args:
            results: Dictionary containing test results
            
        Returns:
            bool: True if results are valid, False otherwise
        """
        try:
            # Check if results is a dictionary
            if not isinstance(results, dict):
                self.logger.error("Results must be a dictionary")
                return False

            # Check for error case
            if "error" in results:
                # Error results should have status and timestamp
                required_error_fields = {"status", "timestamp"}
                if not all(field in results for field in required_error_fields):
                    self.logger.error("Error results missing required fields")
                    return False
                return True

            # For successful results, check required fields
            required_fields = {
                "html_structure", "pa11y", "axe", "lighthouse",
                "url", "timestamp", "implemented_tools", "normalized_results"
            }
            
            missing_fields = required_fields - set(results.keys())
            if missing_fields:
                self.logger.error(f"Missing required fields: {missing_fields}")
                return False

            # Validate normalized results structure
            normalized_results = results.get("normalized_results", [])
            if not isinstance(normalized_results, list):
                self.logger.error("Normalized results must be a list")
                return False

            # Validate each normalized result
            for result in normalized_results:
                if not isinstance(result, dict):
                    self.logger.error("Each normalized result must be a dictionary")
                    return False
                    
                required_result_fields = {
                    "message", "level", "type", "tools"
                }
                
                missing_result_fields = required_result_fields - set(result.keys())
                if missing_result_fields:
                    self.logger.error(f"Normalized result missing fields: {missing_result_fields}")
                    return False

                # Validate level is integer 1-3
                if not isinstance(result["level"], int) or result["level"] not in {1, 2, 3}:
                    self.logger.error("Level must be integer 1-3")
                    return False

                # Validate tools is a list
                if not isinstance(result["tools"], list):
                    self.logger.error("Tools must be a list")
                    return False

            self.logger.info("Results validation successful")
            return True

        except Exception as e:
            self.logger.error(f"Error validating results format: {str(e)}")
            return False

    async def setup_browser(self) -> None:
        """Initialize browser for JavaScript-based testing"""
        if not hasattr(self, 'browser'):
            try:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    args=['--no-sandbox', '--disable-setuid-sandbox'],
                    timeout=30000  # 30 seconds timeout
                )
                self.logger.info("Browser setup completed")
            except Exception as e:
                self.logger.error(f"Browser setup failed: {e}")
                raise
            
    async def cleanup_browser(self) -> None:
        """Clean up browser resources"""
        if hasattr(self, 'browser'):
            await self.browser.close()
            await self.playwright.stop()
            delattr(self, 'browser')
            self.logger.info("Browser resources cleaned up")

    def _create_analyzers(self) -> Dict[str, Any]:
        """
        Create instances of all analyzers
        
        Returns:
            Dictionary containing analyzer instances
        """
        return {
            "html": HTMLAnalyzer(self.results_path, self.logger),
            "pa11y": Pa11yAnalyzer(self.results_path, self.logger),
            "axe": AxeAnalyzer(self.results_path, self.logger, self.browser),
            "lighthouse": LighthouseAnalyzer(self.results_path, self.logger, self.browser)
        }

    def _handle_analyzer_result(self, result: Any, analyzer_name: str) -> Dict[str, Any]:
        """Handle potential exceptions from analyzers"""
        if isinstance(result, Exception):
            error_msg = f"Error in {analyzer_name}: {str(result)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "results": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        return result