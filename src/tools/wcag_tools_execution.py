import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import aiofiles
from typing import Dict, Any

from .wcag_tools_base import WCAGTestingToolsBase

class WCAGTestingTools(WCAGTestingToolsBase):
    """
    Main execution class for WCAG testing tools.
    Handles test execution, result processing and saving.
    """

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
                "html_structure": self._create_analyzers()["html"],
                "pa11y": self._create_analyzers()["pa11y"],
                "axe": self._create_analyzers()["axe"],
                "lighthouse": self._create_analyzers()["lighthouse"]
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
                            
                            # Show summary of results
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
            
            # Save results for each tool separately
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
            
            # Save combined results
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