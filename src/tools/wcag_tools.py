import asyncio
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging
from datetime import datetime, timezone
from typing_extensions import TypedDict
from playwright.async_api import async_playwright
import aiofiles
from src.logging_config import get_logger, ui_message 

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

class WCAGTestingTools:
    """
    Main class for WCAG testing tools integration.
    Coordinates different analyzers and processes results.
    """

    def __init__(self, output_dir: str = "output/tool_results"):
        """
        Initialize WCAG testing tools
        
        Args:
            output_dir: Directory for saving test results
        """
        # Erstelle die benötigten Verzeichnisse
        self.results_path = Path(output_dir)
        self.log_path = Path("output/results/logs")
        
        # Erstelle Verzeichnisse
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
        import traceback
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
                    timeout=30000  # 30 Sekunden Timeout
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
            "lighthouse": LighthouseAnalyzer(self.results_path, self.logger)
        }

    async def run_all_tools(self, url: str) -> Dict[str, Any]:
        """Run all implemented accessibility testing tools with enhanced output"""
        try:
            print("\n" + "="*80)
            print(f"Starting comprehensive accessibility tests for: {url}")
            print("="*80 + "\n")
            
            self.logger.info(f"Starting tests for URL: {url}")
            
            # Setup browser first
            print("🌐 Setting up browser...")
            await self.setup_browser()
            print("✅ Browser setup complete\n")
            
            # Create analyzers after browser is ready
            analyzers = {
                "html_structure": HTMLAnalyzer(self.results_path, self.logger),
                "pa11y": Pa11yAnalyzer(self.results_path, self.logger),
                "axe": AxeAnalyzer(self.results_path, self.logger, self.browser),
                "lighthouse": LighthouseAnalyzer(self.results_path, self.logger, self.browser)
            }

            print("🚀 Starting analysis with following tools:")
            for tool in analyzers.keys():
                print(f"  • {tool}")
            print("")

            results = {}
            
            # Run analyzers sequentially with retries
            for name, analyzer in analyzers.items():
                print(f"\n📊 Running {name} analysis...")
                self.logger.info(f"Starting {name} analysis")
                
                for attempt in range(3):
                    try:
                        result = await analyzer.analyze(url)
                        if not result.get("error"):
                            results[name] = result
                            success_msg = f"{name} analysis completed successfully"
                            print(f"✅ {success_msg}")
                            self.logger.info(success_msg)
                            
                            # Zeige Zusammenfassung der Ergebnisse
                            if isinstance(result.get("issues"), list):
                                issues_msg = f"Found {len(result['issues'])} issues"
                                print(f"   {issues_msg}")
                                self.logger.info(f"{name}: {issues_msg}")
                            break
                        else:
                            raise Exception(f"{name} returned error: {result.get('error')}")
                    except Exception as e:
                        if attempt == 2:
                            error_msg = f"{name} analysis failed after 3 attempts: {e}"
                            print(f"❌ {error_msg}")
                            self.logger.error(error_msg)
                            results[name] = {
                                "status": "error",
                                "message": str(e),
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        else:
                            warning_msg = f"{name} attempt {attempt + 1} failed: {e}"
                            print(f"⚠️  {warning_msg}")
                            self.logger.warning(warning_msg)
                            print(f"   Retrying in {2 * (attempt + 1)} seconds...")
                            await asyncio.sleep(2 * (attempt + 1))

            # Add metadata
            results.update({
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "implemented_tools": list(analyzers.keys())
            })

            print("\n🔄 Processing results...")
            self.logger.info("Processing and normalizing results")
            # Process results through result processor
            normalized_results = self.result_processor.merge_results(results)
            results["normalized_results"] = normalized_results

            # Generate and add summary
            print("📈 Generating summary statistics...")
            self.logger.info("Generating summary statistics")
            summary_stats = self.result_processor.get_summary_statistics(normalized_results)
            results["summary"] = summary_stats

            # Print summary
            print("\n" + "="*80)
            print("SUMMARY OF FINDINGS")
            print("="*80)
            
            summary_lines = [
                f"Total Issues: {summary_stats['total_issues']}",
                f"Errors: {summary_stats['by_level'].get('error', 0)}",
                f"Warnings: {summary_stats['by_level'].get('warning', 0)}",
                f"Notices: {summary_stats['by_level'].get('notice', 0)}"
            ]
            
            for line in summary_lines:
                print(line)
                self.logger.info(line)

            print("\nIssues by Tool:")
            for tool, count in summary_stats['by_tool'].items():
                tool_line = f"  • {tool}: {count}"
                print(tool_line)
                self.logger.info(tool_line)

            if summary_stats.get('wcag_criteria_coverage'):
                wcag_line = f"\nWCAG Criteria Covered: {len(summary_stats['wcag_criteria_coverage'])}"
                print(wcag_line)
                self.logger.info(wcag_line)

            # Save results
            print("\n💾 Saving results...")
            self.logger.info("Saving results to files")
            await self._save_results(results, url)
            print("✅ Results saved successfully")
            
            print("\n" + "="*80)
            print("TESTING COMPLETE")
            print("="*80 + "\n")

            # Validate results before returning
            if not self._validate_results_format(results):
                raise ValueError("Invalid results format")
            
            return results
                        
        except Exception as e:
            error_msg = f"Error in run_all_tools: {str(e)}"
            print(f"\n❌ {error_msg}")
            self.logger.error(error_msg)
            return {
                "error": error_msg,
                "status": "failed",
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        finally:
            print("\n🧹 Cleaning up browser resources...")
            await self.cleanup_browser()
            print("✅ Cleanup complete\n")

    async def _save_results(self, results: Dict[str, Any], url: str) -> None:
        """
        Save test results to separate files for each tool with enhanced output
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = Path(url).name or "local"
            
            print("\nSaving individual tool results:")
            self.logger.info("Starting to save individual tool results")
            
            # Speichere Ergebnisse für jeden Tool separat
            tool_results = {
                'html_structure': results.get('html_structure', {}),
                'pa11y': results.get('pa11y', {}),
                'axe': results.get('axe', {}),
                'lighthouse': results.get('lighthouse', {})
            }
            
            for tool_name, tool_data in tool_results.items():
                if tool_data:
                    file_name = f"{tool_name}_{base_name}_{timestamp}.json"
                    file_path = self.results_path / file_name
                    
                    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(tool_data, indent=2, ensure_ascii=False))
                    
                    success_msg = f"Saved {tool_name} results to {file_path}"
                    print(f"  ✓ {success_msg}")
                    self.logger.info(success_msg)
            
            # Speichere auch die kombinierten Ergebnisse
            combined_file = self.results_path / f"combined_results_{base_name}_{timestamp}.json"
            async with aiofiles.open(combined_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(results, indent=2, ensure_ascii=False))
            
            combined_msg = f"Combined results saved to: {combined_file}"
            print(f"\n📊 {combined_msg}")
            self.logger.info(combined_msg)
                
        except Exception as e:
            error_msg = f"Error saving results: {str(e)}"
            print(f"\n❌ {error_msg}")
            self.logger.error(error_msg)

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

    async def analyze_url(self, url: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Main entry point for URL analysis with retry logic
        
        Args:
            url: URL to analyze
            max_retries: Maximum number of retry attempts
            
        Returns:
            Complete analysis results or error details
        """
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Analysis attempt {attempt + 1} for URL: {url}")
                results = await self.run_all_tools(url)
                
                # Validate results format
                if self._validate_results_format(results):
                    self.logger.info(f"Analysis completed successfully for URL: {url}")
                    return results
                    
                raise ValueError("Invalid results format")
                
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == max_retries - 1:
                    error_result = {
                        "status": "error",
                        "message": f"All {max_retries} attempts failed",
                        "url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "last_error": str(e)
                    }
                    self.logger.error(f"Analysis failed after {max_retries} attempts: {str(e)}")
                    return error_result
                
                # Calculate exponential backoff wait time
                wait_time = 2 ** attempt
                self.logger.info(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
                
                # Log retry attempt
                self.logger.info(f"Retrying analysis for URL: {url} (Attempt {attempt + 2}/{max_retries})")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='WCAG Testing Tools')
    parser.add_argument('url', help='URL to test')
    parser.add_argument('--output', default='output/tool_results', 
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    wcag_tools = WCAGTestingTools(output_dir=args.output)
    asyncio.run(wcag_tools.analyze_url(args.url))