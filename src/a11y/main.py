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

from .crew import WCAGTestingCrew
from .logging_config import get_logger
from .report_generator import ReportGenerator
from datetime import datetime, timezone
import json
import aiofiles
from typing import Dict, Any

class WCAGTestingCLI:
    """Command Line Interface for WCAG Testing"""
    
    def __init__(self):
        # Initialize logger first
        self.logger = get_logger('WCAGTestingCLI', log_dir='output/logs')
        self.logger.info("Initializing WCAGTestingCLI")

        # Initialize paths and core components
        self.test_content_path = Path("test-content")
        try:
            self.test_content_path.mkdir(exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create test-content directory: {e}")
            sys.exit(1)
        
        # Initialize components
        try:
            self.crew = WCAGTestingCrew()
            self.report_generator = ReportGenerator()
            self.logger.info("All components initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            sys.exit(1)

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

    def _create_file_server(self, html_file: Path) -> tuple[str, HTTPServer]:
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
        return server_url, server

    def _cleanup_logs(self) -> None:
        """Ask user if they want to clean up all output files"""
        cleanup_dirs = {
            "logs": Path("output/logs"),
            "results": Path("output/results"),
            "tool_results": Path("output/tool_results")
        }
        
        file_counts = {}
        total_files = 0
        
        for dir_name, dir_path in cleanup_dirs.items():
            if not dir_path.exists():
                continue
            
            files = list(dir_path.rglob("*"))
            files = [f for f in files if f.is_file()]
            file_counts[dir_name] = files
            total_files += len(files)
        
        if total_files == 0:
            return

        print("\nOutput Directory Cleanup")
        print("=======================")
        print("Found files in:")
        for dir_name, files in file_counts.items():
            if files:
                print(f"- {dir_name}: {len(files)} files")
        
        while True:
            response = input("\nDo you want to delete all output files? (y/n): ").strip().lower()
            if response == 'y':
                try:
                    deleted_count = 0
                    for dir_name, files in file_counts.items():
                        for file in files:
                            try:
                                file.unlink()
                                deleted_count += 1
                            except Exception as e:
                                self.logger.error(f"Error deleting {file}: {e}")
                        
                        # Remove empty directories
                        try:
                            for dir_path in sorted(cleanup_dirs[dir_name].rglob("*"), reverse=True):
                                if dir_path.is_dir():
                                    dir_path.rmdir()
                        except Exception as e:
                            self.logger.error(f"Error removing directory {dir_path}: {e}")
                    
                    self.logger.info(f"Deleted {deleted_count} files")
                    print(f"Successfully deleted {deleted_count} files")
                    
                    # Recreate directories
                    for dir_path in cleanup_dirs.values():
                        dir_path.mkdir(parents=True, exist_ok=True)
                    
                except Exception as e:
                    self.logger.error(f"Error during cleanup: {e}")
                    print(f"Error during cleanup: {e}")
                break
            elif response == 'n':
                break
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    def _get_input_choice(self) -> tuple[str, Optional[Path], Optional[HTTPServer]]:
        """Get user input for testing source"""
        server = None
        
        self._cleanup_logs()
        
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
                url = input("Enter URL to test (press Enter for default): ").strip()
                if not url:
                    url = "https://shapeofnew.de"
                    self.logger.info("Using default URL")
                if self._is_valid_url(url):
                    self.logger.info(f"User selected URL: {url}")
                    return url, None, None
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
                        url, server = self._create_file_server(selected_file)
                        return url, selected_file, server
                    self.logger.warning(f"Invalid file number selected: {file_choice}")
                    print("Invalid file number. Please try again.")
                except ValueError:
                    self.logger.warning("Invalid input: not a number")
                    print("Invalid input. Please enter a number.")
            
            else:
                self.logger.warning(f"Invalid choice entered: {choice}")
                print("Invalid choice. Please try again.")

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the complete WCAG 2.2 test process"""
        try:
            self.logger.info(f"Starting WCAG analysis for URL: {context.get('url')}")

            # Run the crew
            crew_instance = self.crew.testing_crew()
            results = await crew_instance.kickoff_async(inputs=context)
            
            # Process results
            final_results = await self.process_results(results, context)
            
            # Save detailed results
            await self._save_detailed_results(final_results)
            
            return final_results

        except Exception as e:
            error_msg = f"Error in run process: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "status": "failed",
                "url": context.get("url", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def process_results(self, crew_output: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the test results with WCAG integration"""
        try:
            # Extract results from crew output
            results = self._serialize_crew_output(crew_output)
            
            # Add context information
            results["url"] = context.get("url", "")
            results["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            return results

        except Exception as e:
            self.logger.error(f"Error processing results: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _serialize_crew_output(self, crew_output: Any) -> dict:
        """Convert CrewOutput to a serializable dictionary with error handling"""
        try:
            if hasattr(crew_output, 'raw_output'):
                if isinstance(crew_output.raw_output, str):
                    try:
                        return json.loads(crew_output.raw_output)
                    except json.JSONDecodeError:
                        return {"raw_output": crew_output.raw_output}
                elif isinstance(crew_output.raw_output, dict):
                    return crew_output.raw_output
            
            return {
                "status": "completed",
                "message": str(crew_output) if crew_output is not None else None,
                "issues": [],
                "summary": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error serializing crew output: {str(e)}")
            return {
                "status": "error",
                "message": f"Error serializing crew output: {str(e)}",
                "issues": [],
                "summary": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _save_detailed_results(self, results: Dict[str, Any]) -> None:
        """Save detailed analysis results"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_dir = self.crew.results_path / timestamp
            results_dir.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(results_dir / "results.json", 'w') as f:
                await f.write(json.dumps(results, indent=2))
                
            self.logger.info(f"Saved detailed results to {results_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving detailed results: {e}")

    async def run_tests(self, url: str) -> None:
        """Run accessibility tests"""
        self.logger.info(f"Starting tests for URL: {url}")
        print(f"\nRunning tests for: {url}")
        print("This may take a few minutes...\n")

        try:
            # Create test context
            context = {
                "url": url,
                "timestamp": datetime.now().isoformat()
            }

            # Run crew analysis
            crew_results = await self.run(context)
            
            if crew_results.get("error"):
                self.logger.error(f"Analysis failed: {crew_results['error']}")
                print(f"\nError in analysis: {crew_results['error']}")
                return

            # Generate and save final report
            output_dir = await self.report_generator.save_results(
                url=url,
                crew_results=crew_results
            )
            
            self.logger.info(f"All results saved to: {output_dir}")
            print(f"\nResults saved to: {output_dir}")

        except Exception as e:
            self.logger.error(f"Test execution failed: {str(e)}")
            print(f"\nError running tests: {str(e)}")
            raise

    async def main(self):
        """Main entry point"""
        try:
            url, html_file, server = self._get_input_choice()
            
            try:
                await self.run_tests(url)
            finally:
                if server:
                    server.shutdown()
                    server.server_close()
                    self.logger.info("Local server stopped")
            
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            print(f"\nError running tests: {e}")
        
        print("\nDone! Press any key to exit...")
        input()

def main():
    """Entry point for the command line interface"""
    cli = WCAGTestingCLI()
    asyncio.run(cli.main())

if __name__ == "__main__":
    main()