from pathlib import Path
from datetime import datetime, timezone
import json
import asyncio
import shutil
import aiofiles
from typing import List, Dict, Any, Optional, Tuple
from src.logging_config import get_logger
from src.wcag.wcag_mapper import WCAGReportMapper

class ReportGenerator:
    """
    Handles result reporting and file generation for accessibility testing.
    Supports both standard and WCAG 2.2 report formats.
    """
    
    def __init__(self):
        self.logger = get_logger('ReportGenerator')
        
        # Initialize WCAG mapper
        self.wcag_mapper = WCAGReportMapper()
        
        # Template and Style Configuration
        self.template_path = Path("templates")
        self.css_path = self.template_path / "report_styles.css"
        
        # Output directory configuration
        self.output_base_path = Path("output/results")
        try:
            self.output_base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create output directory: {e}")
            raise

        # Style configurations
        self.level_styles = {
            "A": "level-a",
            "AA": "level-aa",
            "AAA": "level-aaa"
        }
        
        self.severity_classes = {
            1: "critical",
            2: "serious",
            3: "moderate",
            4: "minor"
        }

    def generate_html_report(self, test_results: Dict[str, Any], config: Dict[str, Any]) -> str:
        """
        Generate HTML report from test results
        
        Args:
            test_results: Dictionary containing test results
            config: Configuration dictionary
            
        Returns:
            HTML report as string
        """
        try:
            # Überprüfen Sie, ob normalized_results existiert und nicht None ist
            if "normalized_results" in test_results and test_results["normalized_results"]:
                mapped_data = self.wcag_mapper.generate_report_data(
                    test_results["normalized_results"],
                    config.get("url", "")
                )
                test_results.update(mapped_data)
            else:
                # Wenn keine normalisierten Ergebnisse vorhanden sind, erstellen Sie einen Fehlerbericht
                return self._generate_error_report("Keine normalisierten Testergebnisse verfügbar")
            
            html_parts = []
            
            # Generate report sections
            html_parts.append(self._generate_html_header("WCAG 2.2 Accessibility Report"))
            html_parts.append(self._generate_table_of_contents(test_results))
            html_parts.append(self._generate_audit_details(config))
            html_parts.append(self._generate_wcag_summary(test_results))
            html_parts.append(self._generate_wcag_details(test_results))
            html_parts.append(self._generate_html_footer())
            
            return "\n".join(html_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            error_template = """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <title>Error Report</title>
                </head>
                <body>
                    <h1>Error in Report Generation</h1>
                    <p>Please check the input data</p>
                    <p>Error: {}</p>
                </body>
                </html>
            """.format(str(e))
            return error_template
        
    def display_results_summary(self, normalized_results: list) -> None:
        """
        Display summary of test results in the console
        
        Args:
            normalized_results: List of normalized test results
        """
        if not normalized_results:
            self.logger.warning("No results found for summary display")
            print("\nNo issues found or error in processing results.")
            return

        error_count = sum(1 for r in normalized_results if r.get("level") == 1)
        warning_count = sum(1 for r in normalized_results if r.get("level") == 2)
        notice_count = sum(1 for r in normalized_results if r.get("level") == 3)
        
        self.logger.info(f"Summary - Errors: {error_count}, Warnings: {warning_count}, Notices: {notice_count}")
        
        print("\nTest Results Summary")
        print("===================")
        print(f"Errors: {error_count}")
        print(f"Warnings: {warning_count}")
        print(f"Notices: {notice_count}")
        
        if error_count > 0:
            print("\nTop Critical Issues:")
            for result in [r for r in normalized_results if r.get("level") == 1][:5]:
                error_msg = result.get('message', 'Unknown error')
                print(f"- {error_msg}")
                self.logger.error(f"Critical issue found: {error_msg}")

    def _get_css_styles(self) -> str:
        """Load CSS styles from file or return default styles"""
        try:
            if self.css_path.exists():
                with open(self.css_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning("CSS file not found, using default styles")
                return self._get_default_css_styles()
        except Exception as e:
            self.logger.error(f"Error loading CSS: {e}")
            return self._get_default_css_styles()
        
    def _generate_error_report(self, error_message: str) -> str:
        """Generate error report HTML"""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Error - Report Generation Failed</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    padding: 20px; 
                    max-width: 800px; 
                    margin: 0 auto;
                }}
                .error-message {{
                    color: #d32f2f;
                    padding: 1rem;
                    border: 1px solid #d32f2f;
                    border-radius: 4px;
                    margin: 1rem 0;
                    background: #fff5f5;
                }}
            </style>
        </head>
        <body>
            <h1>Error in Report Generation</h1>
            <div class="error-message">
                <h2>An error occurred:</h2>
                <p>{error_message}</p>
            </div>
            <p>Please check the input data and try again.</p>
            <p>Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </body>
        </html>
        """

    def _get_default_css_styles(self) -> str:
        """Return default CSS styles"""
        return """
            body { 
                font-family: Arial, sans-serif; 
                line-height: 1.6;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .error { 
                color: #d32f2f;
                padding: 0.5rem;
                border-left: 4px solid #d32f2f;
            }
            
            .warning { 
                color: #f57c00;
                padding: 0.5rem;
                border-left: 4px solid #f57c00;
            }
            
            .notice { 
                color: #0288d1;
                padding: 0.5rem;
                border-left: 4px solid #0288d1;
            }
            
            .summary {
                background: #f5f5f5;
                padding: 1rem;
                margin: 1rem 0;
                border-radius: 4px;
            }
            
            .level-a { background: #e8f5e9; }
            .level-aa { background: #fff3e0; }
            .level-aaa { background: #e3f2fd; }
            
            .issue-details {
                margin-left: 1rem;
                padding: 0.5rem;
                border-left: 3px solid #eee;
            }
            
            .criterion {
                margin: 1rem 0;
                padding: 1rem;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """

    async def save_results(self, url: str, normalized_results: list, 
                         crew_results: Optional[Dict[str, Any]] = None) -> Path:
        """
        Save test results and generate reports
        
        Args:
            url: Tested URL
            normalized_results: List of normalized test results
            crew_results: Optional AI analysis results
            
        Returns:
            Path to the output directory
        """
        try:
            # Create timestamp-based directory name
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            sanitized_url = self._sanitize_url_for_filename(url)
            output_dir = self.output_base_path / f"{timestamp}_{sanitized_url}"
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created output directory: {output_dir}")

            # Save normalized results
            await self._save_json_file(
                output_dir / "normalized_results.json",
                {
                    "url": url,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "results": normalized_results
                }
            )

            # Generate and save HTML report
            config = {"url": url}
            report = self.generate_html_report(
                {"normalized_results": normalized_results},
                config
            )
            await self._save_text_file(output_dir / "report.html", report)

            # Save AI analysis results if available
            if crew_results:
                await self._save_json_file(
                    output_dir / "crew_analysis.json", 
                    crew_results
                )
                
                # Generate and save AI-enhanced HTML report
                ai_report = self.generate_html_report(
                    {
                        "normalized_results": normalized_results,
                        "crew_analysis": crew_results
                    },
                    config
                )
                await self._save_text_file(output_dir / "ai_report.html", ai_report)

            # Copy CSS file if it exists
            if self.css_path.exists():
                shutil.copy2(self.css_path, output_dir / "report_styles.css")
            
            self.logger.info(f"Successfully saved all results to {output_dir}")
            return output_dir

        except Exception as e:
            error_msg = f"Failed to save results: {str(e)}"
            self.logger.error(error_msg)
            
            # Create error report directory
            error_dir = self.output_base_path / f"{timestamp}_error"
            error_dir.mkdir(parents=True, exist_ok=True)
            
            # Save error information
            await self._save_json_file(
                error_dir / "error_info.json",
                {
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "url": url
                }
            )
            raise

    async def _save_json_file(self, filepath: Path, data: Dict[str, Any]) -> None:
        """Save data as JSON file"""
        try:
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            self.logger.debug(f"Successfully saved JSON file: {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save JSON file {filepath}: {e}")
            raise

    async def _save_text_file(self, filepath: Path, content: str) -> None:
        """Save text content to file"""
        try:
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(content)
            self.logger.debug(f"Successfully saved text file: {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save text file {filepath}: {e}")
            raise

    def _sanitize_url_for_filename(self, url: str) -> str:
        """Convert URL to safe filename string"""
        # Remove protocol
        url = url.split('://')[-1]
        # Replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            url = url.replace(char, '_')
        # Limit length
        return url[:50]  # Limit length to prevent too long filenames

    def _get_status_class(self, status: str) -> str:
        """Determine the CSS class based on status"""
        status_classes = {
            "Pass": "success",
            "Fail": "error",
            "Not Applicable": "notice"
        }
        return status_classes.get(status, "notice")

    def _get_severity_class(self, severity: int) -> str:
        """Determine the CSS class based on severity"""
        return self.severity_classes.get(severity, "moderate")
    
    def _generate_html_header(self, title: str) -> str:
        """Generate the HTML header with improved meta tags and styles"""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta name="description" content="WCAG 2.2 Accessibility Report">
            <title>{title}</title>
            <style>
                {self._get_css_styles()}
            </style>
        </head>
        <body>
            <header>
                <h1>{title}</h1>
            </header>
            <main>
        """

    def _generate_table_of_contents(self, test_results: Dict[str, Any]) -> str:
        """Generate an enhanced table of contents with better structure"""
        toc = [
            '<nav class="toc" aria-label="Table of Contents">',
            '<h2>Table of Contents</h2>',
            '<ul>'
        ]
        
        # Standard sections
        standard_sections = [
            ("audit_details", "Audit Details"),
            ("summary", "Summary"),
            ("tools_overview", "Testing Tools Overview")
        ]
        
        for section_id, section_name in standard_sections:
            toc.append(f'<li><a href="#{section_id}">{section_name}</a></li>')
        
        # WCAG Principles and Criteria
        if "results" in test_results:
            toc.append('<li>WCAG 2.2 Results')
            toc.append('<ul>')
            
            principles = test_results.get("results", {})
            for principle_id, principle_data in principles.items():
                principle_name = principle_data.get("name", "")
                total_issues = principle_data.get("total_issues", 0)
                failed = principle_data.get("failed", 0)
                
                toc.append(
                    f'<li><a href="#principle-{principle_id}">'
                    f'Principle {principle_id}: {principle_name}'
                    f'<span class="issue-count">({failed}/{total_issues} issues)</span>'
                    f'</a></li>'
                )
            
            toc.append('</ul>')
            toc.append('</li>')
        
        toc.extend(['</ul>', '</nav>'])
        return '\n'.join(toc)

    def _generate_audit_details(self, config: Dict[str, Any]) -> str:
        """Generate enhanced audit details section"""
        timestamp = datetime.now(timezone.utc)
        return f"""
        <section id="audit_details">
            <h2>Audit Details</h2>
            <div class="summary">
                <div class="audit-info">
                    <h3>Test Information</h3>
                    <dl>
                        <dt>URL Tested:</dt>
                        <dd><a href="{config.get('url', '#')}" target="_blank">{config.get('url', 'N/A')}</a></dd>
                        
                        <dt>Test Date:</dt>
                        <dd>{timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC</dd>
                        
                        <dt>Report Generated:</dt>
                        <dd>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC</dd>
                    </dl>
                </div>
                
                <div class="test-scope">
                    <h3>Test Scope</h3>
                    <ul>
                        <li>WCAG Version: 2.2</li>
                        <li>Conformance Level: AA</li>
                        <li>Testing Scope: Single Page</li>
                    </ul>
                </div>
            </div>
        </section>
        """

    def _generate_wcag_summary(self, test_results: Dict[str, Any]) -> str:
        """Generate enhanced summary section with visual indicators"""
        summary = test_results.get("summary", {})
        total_issues = summary.get("total_criteria", 0)
        failed = summary.get("failed", 0)
        passed = summary.get("passed", 0)
        not_applicable = summary.get("not_applicable", 0)
        
        compliance_percentage = (passed / total_issues * 100) if total_issues > 0 else 0
        
        html_parts = [
            '<section id="summary">',
            '<h2>Summary</h2>',
            '<div class="summary">',
            
            # Overall Compliance
            '<div class="compliance-overview">',
            '<h3>Overall Compliance</h3>',
            f'<div class="compliance-meter" style="--percentage: {compliance_percentage}%">',
            f'<span class="percentage">{compliance_percentage:.1f}%</span>',
            '</div>',
            '</div>',
            
            # Detailed Statistics
            '<div class="detailed-stats">',
            '<h3>Testing Statistics</h3>',
            '<dl>',
            f'<dt>Total Criteria Tested:</dt><dd>{total_issues}</dd>',
            f'<dt>Passed:</dt><dd class="passed">{passed}</dd>',
            f'<dt>Failed:</dt><dd class="failed">{failed}</dd>',
            f'<dt>Not Applicable:</dt><dd class="na">{not_applicable}</dd>',
            '</dl>',
            '</div>'
        ]
        
        # WCAG Level Statistics
        by_level = summary.get("by_level", {})
        if by_level:
            html_parts.extend([
                '<div class="level-statistics">',
                '<h3>Results by WCAG Level</h3>',
                '<table>',
                '<thead><tr><th>Level</th><th>Failed</th><th>Total</th><th>Status</th></tr></thead>',
                '<tbody>'
            ])
            
            for level, data in by_level.items():
                status_class = "passed" if data["failed"] == 0 else "failed"
                html_parts.append(f"""
                    <tr>
                        <td>Level {level}</td>
                        <td>{data["failed"]}</td>
                        <td>{data["total"]}</td>
                        <td><span class="status-tag {status_class}">
                            {status_class.title()}
                        </span></td>
                    </tr>
                """)
                
            html_parts.extend(['</tbody>', '</table>', '</div>'])
        
        html_parts.extend(['</div>', '</section>'])
        return '\n'.join(html_parts)

    def _generate_wcag_details(self, test_results: Dict[str, Any]) -> str:
        """Generate enhanced WCAG details section"""
        html_parts = [
            '<section id="wcag-details">',
            '<h2>WCAG 2.2 Test Results</h2>'
        ]
        
        if "results" in test_results:
            wcag_results = test_results["results"]
            for principle_id, principle_data in wcag_results.items():
                html_parts.append(self._generate_principle_section(principle_id, principle_data))
        else:
            html_parts.append(
                '<div class="no-results">No WCAG results available for this test.</div>'
            )
        
        html_parts.append('</section>')
        return '\n'.join(html_parts)

    def _generate_principle_section(self, principle_id: str, principle_data: Dict[str, Any]) -> str:
        """Generate principle section with enhanced organization"""
        html_parts = [
            f'<section id="principle-{principle_id}" class="principle-section">',
            f'<h3>',
            f'Principle {principle_id}: {principle_data["name"]}',
            f'<span class="principle-summary">({principle_data["failed"]}/{principle_data["total_issues"]} issues)</span>',
            f'</h3>'
        ]
        
        if "criteria" in principle_data:
            # Group criteria by guideline
            guidelines = {}
            for criterion_id, criterion_data in principle_data["criteria"].items():
                guideline_id = '.'.join(criterion_id.split('.')[:2])
                if guideline_id not in guidelines:
                    guidelines[guideline_id] = []
                guidelines[guideline_id].append((criterion_id, criterion_data))
            
            # Generate sections for each guideline
            for guideline_id, criteria in guidelines.items():
                html_parts.append(f'<div class="guideline" id="guideline-{guideline_id}">')
                html_parts.append(f'<h4>Guideline {guideline_id}</h4>')
                
                for criterion_id, criterion_data in criteria:
                    if criterion_data["status"] != "Not Applicable":
                        html_parts.append(
                            self._generate_criterion_details(criterion_id, criterion_data)
                        )
                
                html_parts.append('</div>')
        
        html_parts.append('</section>')
        return '\n'.join(html_parts)

    def _generate_criterion_details(self, criterion_id: str, criterion_data: Dict[str, Any]) -> str:
        """Generate criterion details with enhanced organization"""
        status_class = self._get_status_class(criterion_data["status"])
        level_class = self.level_styles.get(criterion_data["level"], "")
        
        html_parts = [
            f'<div class="criterion {status_class}" id="criterion-{criterion_id}">',
            '<div class="criterion-header">',
            f'<h5>{criterion_id} {criterion_data["title"]}</h5>',
            '<div class="criterion-tags">',
            f'<span class="level-tag {level_class}">Level {criterion_data["level"]}</span>',
            f'<span class="status-tag {status_class}">{criterion_data["status"]}</span>',
            '</div>',
            '</div>'
        ]
        
        # Description
        html_parts.append(
            f'<div class="criterion-description">{criterion_data["description"]}</div>'
        )
        
        # Issues section
        if criterion_data["status"] == "Fail" and criterion_data.get("issues"):
            html_parts.append(self._generate_issues_section(criterion_data["issues"]))
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def _generate_issues_section(self, issues: List[Dict[str, Any]]) -> str:
        """Generate issues section with severity grouping"""
        html_parts = ['<div class="issues-section">', '<h6>Issues Found</h6>']
        
        # Group issues by severity
        severity_groups = {1: [], 2: [], 3: [], 4: []}
        for issue in issues:
            severity = issue.get("severity", 4)
            severity_groups[severity].append(issue)
        
        # Generate sections for each severity level with issues
        for severity, severity_issues in severity_groups.items():
            if severity_issues:
                severity_class = self.severity_classes.get(severity, "minor")
                severity_name = {1: "Critical", 2: "Serious", 3: "Moderate", 4: "Minor"}[severity]
                
                html_parts.extend([
                    f'<div class="severity-group {severity_class}">',
                    f'<h6>{severity_name} Issues ({len(severity_issues)})</h6>',
                    '<ul>'
                ])
                
                for issue in severity_issues:
                    html_parts.append(self._generate_issue_entry(issue))
                
                html_parts.extend(['</ul>', '</div>'])
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def _generate_issue_entry(self, issue: Dict[str, Any]) -> str:
        """Generate single issue entry with enhanced details"""
        html_parts = ['<li class="issue">']
        
        # Issue description
        html_parts.append(f'<div class="issue-description">{issue["description"]}</div>')
        
        # Technical details
        if issue.get("selector") or issue.get("context"):
            html_parts.append('<div class="issue-details">')
            if issue.get("selector"):
                html_parts.append(
                    f'<div class="selector"><strong>Selector:</strong> <code>{issue["selector"]}</code></div>'
                )
            if issue.get("context"):
                html_parts.append(
                    f'<div class="context"><strong>Context:</strong> <code>{issue["context"]}</code></div>'
                )
            html_parts.append('</div>')
        
        # Tools used
        if issue.get("tools"):
            tools_str = ", ".join(issue["tools"])
            html_parts.append(f'<div class="tools-used">Detected by: {tools_str}</div>')
        
        html_parts.append('</li>')
        return '\n'.join(html_parts)

    def _generate_html_footer(self) -> str:
        """Generate enhanced HTML footer"""
        return f"""
            </main>
            <footer>
                <div class="footer-content">
                    <p>Report generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p>Created by WCAG 2.2 Testing Tool</p>
                </div>
            </footer>
            </body>
            </html>
        """