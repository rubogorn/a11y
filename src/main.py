# src/main.py

import asyncio
import sys
from pathlib import Path
from typing import Optional, List
import urllib.parse
from datetime import datetime
import tempfile
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import socket

from src.tools.wcag_tools_execution import WCAGTestingTools
from src.crew import WCAGTestingCrew
from src.logging_config import get_logger
from src.report_generator import ReportGenerator
from src.wcag.wcag_task_executor import WCAGTaskExecutor

class WCAGTestingCLI:
    """Command Line Interface for WCAG Testing"""
    
    def __init__(self):
        # Initialize logger first
        self.logger = get_logger('WCAGTestingCLI', log_dir='output/results/logs')
        self.logger.info("Initializing WCAGTestingCLI")

        # Initialize paths and core components
        self.test_content_path = Path("test-content")
        try:
            self.test_content_path.mkdir(exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create test-content directory: {e}")
            sys.exit(1)
        
        # Initialize components
        self.tools = WCAGTestingTools()
        self.crew = WCAGTestingCrew()
        self.report_generator = ReportGenerator()
        self.wcag_executor = WCAGTaskExecutor() # New: WCAG task executor
        self.logger.info("WCAGTestingCLI initialized successfully")

    def _is_valid_url(self, url: str) -> bool:
        """Validate if string is a valid URL"""
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            self.logger.warning(f"Invalid URL: {url}")
            return False

    def _get_html_files(self) -> List[Path]:
        """Get list of HTML files in test-content directory"""
        html_files = list(self.test_content_path.glob("*.html"))
        self.logger.info(f"Found {len(html_files)} HTML files in test-content directory")
        return html_files

    def _create_file_server(self, html_file: Path) -> str:
        """Create temporary server for local HTML file"""
        self.logger.info(f"Setting up temporary server for {html_file}")

        # Find an available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]

        # Create temporary directory and copy file
        temp_dir = Path(tempfile.mkdtemp())
        temp_file = temp_dir / "index.html"
        shutil.copy2(html_file, temp_file)
        self.logger.debug(f"Temporary file created at {temp_file}")

        # Configure and start server
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(temp_dir), **kwargs)

        server = HTTPServer(('localhost', port), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        server_url = f"http://localhost:{port}"
        self.logger.info(f"Local server started at {server_url}")
        return server_url

    def _get_input_choice(self) -> tuple[str, Optional[Path]]:
        """Get user input for testing source"""
        while True:
            print("\nWCAG 2.2 Testing Tool")
            print("====================")
            print("1. Test URL")
            print("2. Test local HTML file")
            print("q. Quit")
            
            choice = input("\nPlease select an option: ").strip().lower()
            
            if choice == 'q':
                self.logger.info("User chose to quit")
                sys.exit(0)
                
            elif choice == '1':
                url = input("Enter URL to test: ").strip()
                if self._is_valid_url(url):
                    self.logger.info(f"User selected URL: {url}")
                    return url, None
                print("Invalid URL format. Please try again.")
                
            elif choice == '2':
                self.logger.info("User selected local HTML file testing")
                html_files = self._get_html_files()
                if not html_files:
                    self.logger.warning("No HTML files found in test-content directory")
                    print("No HTML files found in test-content directory.")
                    print("Please add HTML files to test-content/ and try again.")
                    continue
                    
                print("\nAvailable HTML files:")
                for i, file in enumerate(html_files, 1):
                    print(f"{i}. {file.name}")
                    
                try:
                    file_choice = int(input("\nSelect file number: ").strip())
                    if 1 <= file_choice <= len(html_files):
                        selected_file = html_files[file_choice - 1]
                        self.logger.info(f"User selected file: {selected_file}")
                        return "", selected_file
                    self.logger.warning(f"Invalid file number selected: {file_choice}")
                    print("Invalid file number. Please try again.")
                except ValueError:
                    self.logger.warning("Invalid input: not a number")
                    print("Invalid input. Please enter a number.")
            
            else:
                self.logger.warning(f"Invalid choice entered: {choice}")
                print("Invalid choice. Please try again.")

    async def run_tests(self, url: str) -> None:
        """Run all accessibility tests"""
        self.logger.info(f"Starting tests for URL: {url}")
        print(f"\nRunning tests for: {url}")
        print("This may take a few minutes...\n")

        try:
            # Run tools analysis
            self.logger.info("Starting automated testing phase")
            results = await self.tools.analyze_url(url)
            
            if results.get("error"):
                self.logger.error(f"Tool analysis failed: {results['error']}")
                print(f"\nError in tool analysis: {results['error']}")
                return

            # Process results with WCAG mapping
            print("\nPhase 2: WCAG Analysis")
            print("-" * 50)
            print("Analyzing results against WCAG 2.2 criteria...")
            
            wcag_results = await self.wcag_executor.process_results(results)
            if wcag_results.get("error"):
                self.logger.error(f"WCAG analysis failed: {wcag_results['error']}")
                print(f"\nError in WCAG analysis: {wcag_results['error']}")
                # Continue with original results if WCAG analysis fails
            else:
                # Update results with WCAG mappings
                results["wcag_analysis"] = wcag_results
                
                # Print WCAG analysis summary
                summary = wcag_results.get("summary", {})
                print("\nWCAG Analysis Summary:")
                print(f"Total Issues Mapped: {summary.get('total_issues', 0)}")
                
                # Print issues by WCAG level
                if "by_level" in summary:
                    print("\nIssues by WCAG Level:")
                    for level, count in summary["by_level"].items():
                        print(f"  Level {level}: {count}")
                
                # Print issues by WCAG principle
                if "by_principle" in summary:
                    print("\nIssues by WCAG Principle:")
                    for principle, count in summary["by_principle"].items():
                        print(f"  {principle}: {count}")

            # Process normalized results as before
            normalized_results = results.get("normalized_results", [])
            if not normalized_results:
                self.logger.warning("No accessibility issues found or error in processing results")
                print("\nNo accessibility issues found or error in processing results.")
                return

            print("\nPhase 3: AI Analysis")
            print("-" * 50)
            print("The AI agents will now:")
            print("1. Analyze the collected data")
            print("2. Generate detailed recommendations")
            print("3. Create a comprehensive report")

            while True:
                response = input("\nDo you want to proceed with AI analysis? (y/n): ").strip().lower()
                if response == 'n':
                    self.logger.info("User chose to skip AI analysis")
                    print("\nSaving automated test results only...")
                    output_dir = await self.report_generator.save_results(url, normalized_results, {"status": "automated_only"})
                    self.logger.info(f"Automated results saved to: {output_dir}")
                    return
                elif response == 'y':
                    break
                else:
                    print("Please enter 'y' for yes or 'n' for no.")

            try:
                # Create crew configuration with WCAG results
                crew_config = {
                    "url": url,
                    "raw_results": results,
                    "normalized_results": normalized_results,
                    "wcag_analysis": wcag_results if not wcag_results.get("error") else None
                }

                # Run AI analysis with configuration
                self.logger.info("Starting AI analysis phase")
                crew_results = await self.crew.run(crew_config)

                # Display and save results using report generator
                self.report_generator.display_results_summary(normalized_results)
                output_dir = await self.report_generator.save_results(url, normalized_results, crew_results)
                self.logger.info(f"Results saved to: {output_dir}")
                
            except Exception as e:
                self.logger.error(f"AI analysis failed: {str(e)}")
                print(f"\nError in AI analysis: {str(e)}")
                # Still save the tool results even if AI analysis fails
                output_dir = await self.report_generator.save_results(url, normalized_results, {"error": str(e)})
                self.logger.info(f"Error results saved to: {output_dir}")
                    
        except Exception as e:
            self.logger.error(f"Test execution failed: {str(e)}")
            print(f"\nError running tests: {str(e)}")
            raise

    async def main(self):
        """Main entry point"""
        try:
            url, html_file = self._get_input_choice()
            
            if html_file:
                # Start local server for HTML file
                url = self._create_file_server(html_file)
                print(f"\nStarting local server for: {html_file.name}")
            
            await self.run_tests(url)
            
        except Exception as e:
            print(f"\nError running tests: {e}")
        
        print("\nDone! Press any key to exit...")
        input()

if __name__ == "__main__":
    cli = WCAGTestingCLI()
    asyncio.run(cli.main())