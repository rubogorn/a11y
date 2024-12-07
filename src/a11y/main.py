# src/main.py

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
import json
import aiofiles
from typing import Dict, Any
from dotenv import load_dotenv

from .crew import WCAGTestingCrew
from .logging_config import get_logger
from .utils import (
    _get_user_input,
    initialize_environment,
    _serialize_crew_output,
    _save_detailed_results,
    process_results
)

# Load environment variables from .env file
load_dotenv()

class WCAGTestingCLI:
    """Command Line Interface for WCAG Testing"""
    
    def __init__(self):
        # Initialize environment first (cleanup and directory creation)
        initialize_environment()
        
        # Initialize logger
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
            self.logger.info("All components initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            sys.exit(1)

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the complete WCAG 2.2 test process"""
        try:
            self.logger.info(f"Starting WCAG analysis for URL: {context.get('url')}")

            # Run the crew
            crew_instance = self.crew.testing_crew()
            results = await crew_instance.kickoff_async(inputs=context)
            
            # Process results
            final_results = await process_results(results, context)
            
            # Save detailed results
            await _save_detailed_results(final_results, self.crew.results_path)
            
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

        except Exception as e:
            self.logger.error(f"Test execution failed: {str(e)}")
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