from pathlib import Path
from datetime import datetime, timezone
import json
from typing import List, Dict, Any
from src.logging_config import get_logger

class ReportGenerator:
    """Handles result reporting and file generation for WCAG testing"""
    
    def __init__(self):
        self.logger = get_logger('ReportGenerator', log_dir='output/results/logs')

    def display_results_summary(self, results: list) -> None:
        """Display summary of test results in the console"""
        if not results:
            self.logger.warning("No results found for summary display")
            print("\nNo issues found or error in processing results.")
            return

        error_count = sum(1 for r in results if r.get("level") == 1)
        warning_count = sum(1 for r in results if r.get("level") == 2)
        notice_count = sum(1 for r in results if r.get("level") == 3)
        
        self.logger.info(f"Summary - Errors: {error_count}, Warnings: {warning_count}, Notices: {notice_count}")
        
        print("\nTest Results Summary")
        print("===================")
        print(f"Errors: {error_count}")
        print(f"Warnings: {warning_count}")
        print(f"Notices: {notice_count}")
        
        if error_count > 0:
            print("\nTop Errors:")
            for result in [r for r in results if r.get("level") == 1][:5]:
                error_msg = result.get('message', 'Unknown error')
                print(f"- {error_msg}")
                self.logger.error(f"Critical issue found: {error_msg}")

        output_path = Path('output').absolute()
        self.logger.info(f"Results saved to: {output_path}")
        print(f"\nDetailed results saved to: {output_path}")

    async def save_results(self, url: str, normalized_results: list, crew_results: dict) -> Path:
        """
        Save detailed results and generate reports with WCAG analysis
        
        Args:
            url: URL that was tested
            normalized_results: List of normalized test results
            crew_results: Results from the crew including WCAG analysis
            
        Returns:
            Path to the output directory
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = Path(url).name or "local"
            output_dir = Path("output") / f"test_{base_name}_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Saving results to directory: {output_dir}")

            # Extract WCAG analysis if available
            wcag_analysis = crew_results.get("wcag_analysis", {})
            
            # Save normalized results
            normalized_file = output_dir / "normalized_results.json"
            with open(normalized_file, 'w', encoding='utf-8') as f:
                json.dump(normalized_results, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Normalized results saved to: {normalized_file}")

            # Save WCAG analysis separately if available
            if wcag_analysis:
                wcag_file = output_dir / "wcag_analysis.json"
                with open(wcag_file, 'w', encoding='utf-8') as f:
                    json.dump(wcag_analysis, f, indent=2, ensure_ascii=False)
                self.logger.debug(f"WCAG analysis saved to: {wcag_file}")

            # Save complete crew analysis
            crew_file = output_dir / "crew_analysis.json"
            with open(crew_file, 'w', encoding='utf-8') as f:
                json.dump(crew_results, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Crew analysis saved to: {crew_file}")

            # Generate HTML report with WCAG integration
            html_content = self.generate_report(url, normalized_results, wcag_analysis)
            report_file = output_dir / "report.html"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self.logger.info(f"HTML report generated at: {report_file}")

            # Generate WCAG-specific summary file if analysis is available
            if wcag_analysis and wcag_analysis.get("summary"):
                summary_file = output_dir / "wcag_summary.json"
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "wcag_summary": wcag_analysis["summary"],
                        "coverage": {
                            "tested_criteria": wcag_analysis["summary"].get("coverage", []),
                            "total_issues": wcag_analysis["summary"].get("total_issues", 0),
                            "by_level": wcag_analysis["summary"].get("by_level", {}),
                            "by_principle": wcag_analysis["summary"].get("by_principle", {})
                        }
                    }, f, indent=2, ensure_ascii=False)
                self.logger.info(f"WCAG summary saved to: {summary_file}")
            
            return output_dir
                
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            raise

    def _generate_html_report(self, output_dir: Path, url: str, 
                            normalized_results: list, crew_results: dict) -> None:
        """Generate enhanced HTML report"""
        html_content = self._generate_html_template(url, normalized_results)
        
        # Group issues by type
        for result in normalized_results:
            level_class = self._get_level_class(result.get('level', 3))
            html_content += self._generate_issue_html(result, level_class)
        
        html_content += """
        </body>
        </html>
        """
        
        report_file = output_dir / "report.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        self.logger.info(f"HTML report generated at: {report_file}")

    def _get_level_class(self, level: int) -> str:
        """Get CSS class for issue level"""
        return {1: "error", 2: "warning", 3: "notice"}.get(level, "notice")

    def _generate_html_template(self, url: str, normalized_results: list, wcag_analysis: dict = None) -> str:
        """Generate the HTML template with WCAG analysis integration
        
        Args:
            url: Tested URL
            normalized_results: List of normalized test results
            wcag_analysis: Dictionary containing WCAG analysis results
        
        Returns:
            HTML template string
        """
        # Base template start
        template = f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>WCAG 2.2 Test Results</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 2rem;
                    line-height: 1.6;
                }}
                .error {{ 
                    color: #d32f2f;
                    padding: 0.5rem;
                    margin: 0.5rem 0;
                    border-left: 4px solid #d32f2f;
                }}
                .warning {{ 
                    color: #f57c00;
                    padding: 0.5rem;
                    margin: 0.5rem 0;
                    border-left: 4px solid #f57c00;
                }}
                .notice {{ 
                    color: #0288d1;
                    padding: 0.5rem;
                    margin: 0.5rem 0;
                    border-left: 4px solid #0288d1;
                }}
                .issue-details {{
                    margin-left: 1rem;
                    font-size: 0.9em;
                    color: #666;
                }}
                .summary {{
                    background: #f5f5f5;
                    padding: 1rem;
                    margin: 1rem 0;
                    border-radius: 4px;
                }}
                .wcag-info {{
                    background: #e3f2fd;
                    padding: 1rem;
                    margin: 0.5rem 0;
                    border-radius: 4px;
                }}
                .wcag-links {{
                    margin-top: 0.5rem;
                    padding: 0.5rem;
                    background: #fff;
                    border-radius: 4px;
                }}
                .toc {{
                    background: #fff;
                    padding: 1rem;
                    margin: 1rem 0;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }}
                .principle-section {{
                    margin: 2rem 0;
                    padding: 1rem;
                    background: #fff;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }}
                .level-tag {{
                    display: inline-block;
                    padding: 0.2rem 0.5rem;
                    border-radius: 3px;
                    font-size: 0.8em;
                    font-weight: bold;
                    margin-left: 0.5rem;
                }}
                .level-a {{ background: #e8f5e9; color: #2e7d32; }}
                .level-aa {{ background: #fff3e0; color: #f57c00; }}
                .level-aaa {{ background: #e3f2fd; color: #1565c0; }}
            </style>
        </head>
        <body>
            <h1>WCAG 2.2 Test Results</h1>
            
            <div class="summary">
                <p>URL: {url}</p>
                <p>Test durchgeführt: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
                
                <h2>Zusammenfassung</h2>
                <ul>
                    <li>Errors: {sum(1 for r in normalized_results if r.get('level') == 1)}</li>
                    <li>Warnings: {sum(1 for r in normalized_results if r.get('level') == 2)}</li>
                    <li>Notices: {sum(1 for r in normalized_results if r.get('level') == 3)}</li>
                </ul>
        """
        
        # Add WCAG Analysis Summary if available
        if wcag_analysis and wcag_analysis.get('summary'):
            summary = wcag_analysis['summary']
            template += """
                <h3>WCAG Analysis</h3>
                <div class="wcag-info">
            """
            
            # Add level breakdown
            if 'by_level' in summary:
                template += "<h4>Issues by WCAG Level</h4><ul>"
                for level, count in summary['by_level'].items():
                    template += f"<li>Level {level}: {count}</li>"
                template += "</ul>"
                
            # Add principle breakdown
            if 'by_principle' in summary:
                template += "<h4>Issues by WCAG Principle</h4><ul>"
                for principle, count in summary['by_principle'].items():
                    template += f"<li>{principle}: {count}</li>"
                template += "</ul>"
                
            template += "</div>"
        
        # Add table of contents
        template += """
            </div>
            
            <div class="toc">
                <h2>Inhaltsverzeichnis</h2>
                <ul>
        """
        
        # Generate TOC based on WCAG principles if analysis available
        if wcag_analysis and wcag_analysis.get('issues'):
            principles = sorted(set(issue.get('wcag_mapping', {}).get('criterion_id', '').split('.')[0] 
                                for issue in wcag_analysis['issues'] if issue.get('wcag_mapping')))
            
            for principle in principles:
                template += f'<li><a href="#principle-{principle}">{principle}</a></li>'
        
        template += """
                </ul>
            </div>
            
            <h2>Detaillierte Ergebnisse</h2>
        """
        
        return template

    def _generate_issue_html(self, issue: Dict[str, Any], level_class: str) -> str:
        """Generate HTML for a single issue with WCAG information
        
        Args:
            issue: Dictionary containing issue details
            level_class: CSS class for issue level
        
        Returns:
            HTML string for the issue
        """
        wcag_mapping = issue.get('wcag_mapping', {})
        
        # Start issue container
        html = f'<div class="{level_class}">'
        
        # Add issue header with WCAG level if available
        html += f'<h3>{issue.get("message", "Unbekanntes Problem")}'
        if wcag_mapping.get('level'):
            html += f'<span class="level-tag level-{wcag_mapping["level"].lower()}">'
            html += f'WCAG {wcag_mapping["level"]}</span>'
        html += '</h3>'
        
        # Add issue details
        html += '<div class="issue-details">'
        html += f'<p>Gefunden durch: {", ".join(issue.get("tools", ["unknown"]))}</p>'
        html += f'<p>Typ: {issue.get("type", "unknown")}</p>'
        
        if issue.get('selector'):
            html += f'<p>Selector: <code>{issue["selector"]}</code></p>'
        
        if issue.get('context'):
            html += f'<p>Kontext: <pre>{issue["context"]}</pre></p>'
        
        # Add WCAG specific information if available
        if wcag_mapping:
            html += '<div class="wcag-info">'
            html += f'<h4>WCAG {wcag_mapping.get("criterion_id", "")}: '
            html += f'{wcag_mapping.get("title", "")}</h4>'
            
            if wcag_mapping.get('description'):
                html += f'<p>{wcag_mapping["description"]}</p>'
            
            if wcag_mapping.get('special_cases'):
                html += '<p><strong>Besondere Fälle:</strong></p><ul>'
                for case in wcag_mapping['special_cases']:
                    html += f'<li>{case}</li>'
                html += '</ul>'
            
            # Add documentation links
            docs = wcag_mapping.get('documentation_links', {})
            if docs:
                html += '<div class="wcag-links">'
                html += '<p><strong>Weiterführende Dokumentation:</strong></p><ul>'
                if docs.get('understanding'):
                    html += f'<li><a href="{docs["understanding"]}" target="_blank">'
                    html += 'Understanding WCAG Kriterium</a></li>'
                if docs.get('how_to_meet'):
                    html += f'<li><a href="{docs["how_to_meet"]}" target="_blank">'
                    html += 'How to Meet WCAG Kriterium</a></li>'
                html += '</ul></div>'
            
            html += '</div>'  # Close wcag-info
        
        html += '</div></div>'  # Close issue-details and issue container
        return html

    def _generate_principle_sections(self, wcag_analysis: dict) -> str:
        """Generate HTML sections for each WCAG principle
        
        Args:
            wcag_analysis: Dictionary containing WCAG analysis results
        
        Returns:
            HTML string containing principle sections
        """
        if not wcag_analysis or not wcag_analysis.get('issues'):
            return ""
            
        # Group issues by principle
        principles = {}
        for issue in wcag_analysis['issues']:
            wcag_mapping = issue.get('wcag_mapping', {})
            if not wcag_mapping:
                continue
                
            criterion_id = wcag_mapping.get('criterion_id', '')
            if not criterion_id:
                continue
                
            principle = criterion_id.split('.')[0]
            if principle not in principles:
                principles[principle] = []
            principles[principle].append(issue)
        
        # Generate sections
        html = ""
        for principle in sorted(principles.keys()):
            html += f'<div id="principle-{principle}" class="principle-section">'
            html += f'<h2>Principle {principle}</h2>'
            
            # Sort issues by criterion ID
            sorted_issues = sorted(
                principles[principle],
                key=lambda x: x.get('wcag_mapping', {}).get('criterion_id', '')
            )
            
            # Add issues
            for issue in sorted_issues:
                level = issue.get('level', 3)
                level_class = self._get_level_class(level)
                html += self._generate_issue_html(issue, level_class)
            
            html += '</div>'  # Close principle section
        
        return html

    def generate_report(self, url: str, normalized_results: list, wcag_analysis: dict = None) -> str:
        """Generate complete HTML report with WCAG analysis integration
        
        Args:
            url: Tested URL
            normalized_results: List of normalized test results
            wcag_analysis: Dictionary containing WCAG analysis results
        
        Returns:
            Complete HTML report as string
        """
        # Generate base template
        html_content = self._generate_html_template(url, normalized_results, wcag_analysis)
        
        if wcag_analysis and wcag_analysis.get('issues'):
            # Generate principle-based sections
            html_content += self._generate_principle_sections(wcag_analysis)
        else:
            # Fallback to original issue display if no WCAG analysis
            for result in normalized_results:
                level_class = self._get_level_class(result.get('level', 3))
                html_content += self._generate_issue_html(result, level_class)
        
        # Close HTML document
        html_content += """
            </body>
            </html>
        """
        
        return html_content


