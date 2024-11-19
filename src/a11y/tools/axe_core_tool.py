from crewai.tools import BaseTool
from typing import Optional
import json
import os
import subprocess
import datetime

class AxeCoreTool(BaseTool):
    name: str = "Axe Core Accessibility Tester"
    description: str = """
    Executes automated accessibility tests using Axe Core.
    This tool analyzes web pages for WCAG 2.0, 2.1, and 2.2 compliance
    at levels A, AA, and AAA, as well as best practices.
    """

    def _run(self, url: str) -> str:
        """Execute Axe Core accessibility tests."""
        script_path = "run_axe.js"
        try:
            # Create output directory if it doesn't exist
            output_dir = "output/tool_results"
            os.makedirs(output_dir, exist_ok=True)
            
            # Create output filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"axe_results_{timestamp}.json")
            
            # Create Node.js script for running axe-core
            script_content = f"""
            const axeCore = require('@axe-core/puppeteer');
            const puppeteer = require('puppeteer');

            async function runAxe() {{
                let browser;
                try {{
                    console.log('Launching browser...');
                    browser = await puppeteer.launch({{
                        headless: 'new',
                        args: ['--no-sandbox', '--disable-setuid-sandbox']
                    }});
                    
                    console.log('Creating new page...');
                    const page = await browser.newPage();
                    await page.setViewport({{ width: 1280, height: 1024 }});
                    
                    console.log('Navigating to {url}...');
                    await page.goto('{url}', {{
                        waitUntil: ['networkidle0', 'domcontentloaded'],
                        timeout: 60000
                    }});

                    console.log('Running Axe analysis...');
                    const results = await new axeCore.AxePuppeteer(page)
                        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
                        .analyze();

                    // Ensure we're outputting valid JSON
                    const jsonString = JSON.stringify(results, null, 2);
                    console.log('AXERESULTS' + jsonString + 'ENDAXERESULTS');
                    
                }} catch (error) {{
                    console.error('Error in runAxe:', error.message);
                    process.exit(1);
                }} finally {{
                    if (browser) {{
                        console.log('Closing browser...');
                        await browser.close();
                    }}
                }}
            }}
            
            runAxe().catch(error => {{
                console.error('Unhandled error:', error);
                process.exit(1);
            }});
            """
            
            # Save the script
            with open(script_path, "w") as f:
                f.write(script_content)
            
            # Install required Node.js packages if not already installed
            try:
                print("Installing Node.js dependencies...")
                subprocess.run(
                    ['npm', 'install', '@axe-core/puppeteer', 'puppeteer'],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                return f"Error installing Node.js dependencies: {e.stderr.decode()}"
            
            # Run the axe-core analysis
            print(f"Running Axe Core tests on {url}")
            result = subprocess.run(
                ['node', script_path],
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit
            )
            
            # Print debug information
            if result.stderr:
                print("Node.js stderr output:", result.stderr)
                
            if result.stdout:
                print("Node.js stdout output:", result.stdout)
            
            # Extract the JSON results using the markers
            stdout = result.stdout
            try:
                start_marker = 'AXERESULTS'
                end_marker = 'ENDAXERESULTS'
                start_idx = stdout.find(start_marker) + len(start_marker)
                end_idx = stdout.find(end_marker)
                
                if start_idx == -1 or end_idx == -1:
                    raise ValueError(f"Could not find JSON markers in output. Full output: {stdout}")
                
                json_str = stdout[start_idx:end_idx]
                axe_results = json.loads(json_str)
                
                # Save the full results to file
                with open(output_path, 'w') as f:
                    json.dump(axe_results, f, indent=2)
                
                # Create a summary
                violations = axe_results.get("violations", [])
                passes = axe_results.get("passes", [])
                incomplete = axe_results.get("incomplete", [])
                inapplicable = axe_results.get("inapplicable", [])
                
                summary = f"""Axe Core Test Results Summary:
URL Tested: {url}
Timestamp: {timestamp}

Results:
- Violations: {len(violations)}
- Passes: {len(passes)}
- Incomplete: {len(incomplete)}
- Inapplicable: {len(inapplicable)}

Violations Summary:
"""
                # Add details for each violation
                for violation in violations:
                    summary += f"""
Impact: {violation.get('impact', 'unknown')}
Rule: {violation.get('id')} - {violation.get('help')}
WCAG: {', '.join(violation.get('tags', []))}
Elements Affected: {len(violation.get('nodes', []))}
---"""
                
                summary += f"\n\nDetailed results saved to: {output_path}"
                
                return summary
                
            except ValueError as e:
                return f"Error parsing Axe results: {str(e)}"
            except json.JSONDecodeError as e:
                return f"Error decoding JSON: {str(e)}. Raw output: {stdout}"
            
        except Exception as e:
            return f"Error executing Axe Core test: {str(e)}"
        finally:
            # Clean up the temporary script
            if os.path.exists(script_path):
                os.remove(script_path)

    def _execute(self, *args, **kwargs):
        """Wrapper for _run to maintain compatibility with both methods."""
        return self._run(*args, **kwargs)