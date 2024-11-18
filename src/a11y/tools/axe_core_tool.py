from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import subprocess
import json
import os

class AxeCoreInput(BaseModel):
    """Input schema for AxeCoreTool."""
    url: str = Field(..., description="URL to test for accessibility")
    output_path: str = Field(..., description="Path to save the test results")

class AxeCoreTool(BaseTool):
    name: str = "Axe Core Accessibility Tester"
    description: str = """
    Executes automated accessibility tests using Axe Core.
    This tool analyzes web pages for WCAG 2.0, 2.1, and 2.2 compliance
    at levels A, AA, and AAA, as well as best practices.
    It provides detailed reports of violations, passes, and incomplete tests.
    """
    args_schema: Type[BaseModel] = AxeCoreInput

    def _run(self, url: str, output_path: str) -> str:
        """
        Run Axe Core accessibility tests on the specified URL.
        
        Args:
            url: The URL to test
            output_path: Where to save the test results
            
        Returns:
            str: Summary of the test results
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create a Node.js script for running axe-core
            script_content = f"""
            const axe = require('@axe-core/cli');
            
            async function runAxe() {{
                try {{
                    const results = await axe.run('{url}', {{
                        rules: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'],
                        reporter: 'v2',
                        resultTypes: ['violations', 'incomplete', 'passes'],
                        showErrors: true
                    }});
                    
                    console.log(JSON.stringify(results));
                }} catch (error) {{
                    console.error(error);
                    process.exit(1);
                }}
            }}
            
            runAxe();
            """
            
            # Save the script
            script_path = "run_axe.js"
            with open(script_path, "w") as f:
                f.write(script_content)
            
            # Run the script
            result = subprocess.run(
                ['node', script_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse results
            axe_results = json.loads(result.stdout)
            
            # Save full results
            with open(output_path, 'w') as f:
                json.dump(axe_results, f, indent=2)
            
            # Create summary
            summary = {
                "violations_count": len(axe_results.get("violations", [])),
                "incomplete_count": len(axe_results.get("incomplete", [])),
                "passes_count": len(axe_results.get("passes", [])),
                "url": url,
                "timestamp": axe_results.get("timestamp"),
                "test_engine": axe_results.get("testEngine", {}).get("name")
            }
            
            # Return summary
            return f"""Axe Core Test Results Summary:
URL Tested: {summary['url']}
Test Engine: {summary['test_engine']}
Timestamp: {summary['timestamp']}
Results:
- Violations: {summary['violations_count']}
- Incomplete Tests: {summary['incomplete_count']}
- Passed Tests: {summary['passes_count']}

Detailed results have been saved to: {output_path}"""

        except subprocess.CalledProcessError as e:
            return f"Error running Axe Core tests: {e.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _validate_results_path(self, path: str) -> bool:
        """Validate that the results can be saved to the specified path."""
        try:
            directory = os.path.dirname(path)
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception:
            return False