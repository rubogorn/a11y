# src/main.py

import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from http.server import HTTPServer

from .crew import WCAGTestingCrew
from .logging_config import get_logger, configure_root_logger
from .utils import (_get_input_choice, _is_valid_url, _create_file_server, 
                   _check_chromedriver_version, _get_user_input, _get_html_files,
                   initialize_environment)

# Load environment variables from .env file
load_dotenv()

# Initialize environment (cleanup and create directories)
initialize_environment()

# Initialize root logger after cleanup
configure_root_logger(log_dir='output/logs')

class WCAGTestingCLI:
    """Command Line Interface for WCAG Testing"""
    
    def __init__(self):
        # Initialize logger first
        self.logger = get_logger('WCAGTestingCLI', log_dir='output/logs')
        self.logger.info("Initializing WCAGTestingCLI")
        
        # Check ChromeDriver version
        try:
            _check_chromedriver_version()
        except Exception as e:
            self.logger.error(f"ChromeDriver check failed: {e}")
        
        # Initialize paths and core components
        self.test_content_path = Path("test-content")
        
        # Initialize components
        try:
            self.crew = WCAGTestingCrew()
            self.logger.info("WCAGTestingCrew initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            sys.exit(1)

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the complete WCAG 2.2 test process"""
        try:
            self.logger.info(f"Starting WCAG analysis for URL: {context.get('url')}")

            # Run the crew
            crew_instance = self.crew.testing_crew()
            self.logger.info("Testing crew created, starting analysis...")
            results = await crew_instance.kickoff_async(inputs=context)
            self.logger.info("Analysis completed")
            
            return {
                "status": "success",
                "url": context.get("url", ""),
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            error_msg = f"Error in run process: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "status": "failed",
                "url": context.get("url", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

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
            self.logger.debug(f"Test context created: {context}")

            # Run crew analysis
            crew_results = await self.run(context)
            
            if crew_results.get("error"):
                self.logger.error(f"Analysis failed: {crew_results['error']}")
                print(f"\nError in analysis: {crew_results['error']}")
                return

            self.logger.info("Tests completed successfully")

        except Exception as e:
            self.logger.error(f"Test execution failed: {str(e)}", exc_info=True)
            print(f"\nError running tests: {str(e)}")
            raise

    async def main(self):
        """Main entry point"""
        try:
            url, html_file, server = _get_user_input(self.test_content_path)
            
            try:
                await self.run_tests(url)
            finally:
                if server:
                    server.shutdown()
                    server.server_close()
                    self.logger.info("Local server stopped")
                
        except Exception as e:
            self.logger.error(f"Application error: {e}", exc_info=True)
            print(f"\nError running tests: {e}")
        
        self.logger.info("Application finished")
        print("\nDone! Press any key to exit...")
        input()

def main():
    """Entry point for the command line interface"""
    cli = WCAGTestingCLI()
    asyncio.run(cli.main())

if __name__ == "__main__":
    main()