# src/report_generator.py

from pathlib import Path
from datetime import datetime, timezone
import json
import asyncio
import shutil
from typing import List, Dict, Any, Optional, Union
import aiofiles
from .logging_config import get_logger
from .errors.exceptions import ReportGenerationError, DataValidationError, TemplateError

class ReportGenerator:
    """
    Generiert Berichte basierend auf den Ergebnissen der Crew und Agenten-Analyse.
    Fokussiert auf die Darstellung der Agent-basierten WCAG-Mappings.
    """
    
    def __init__(self):
        """Initialisiert den Report Generator mit Basis-Konfiguration"""
        self.logger = get_logger('ReportGenerator')
        
        # Verzeichnisstruktur initialisieren
        self.template_path = Path("templates")
        self.css_path = self.template_path / "report_styles.css"
        self.output_base_path = Path("output/results")
        
        try:
            self.output_base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create output directory: {e}")
            raise

    def validate_report_data(self, data: Dict[str, Any]) -> None:
        """Validiert die Eingabedaten für die Reportgenerierung"""
        # Minimale Validierung um sicherzustellen, dass wir ein Dictionary haben
        if not isinstance(data, dict):
            raise DataValidationError("Report data must be a dictionary")
            
        # Stelle sicher, dass mindestens ein Ergebnistyp vorhanden ist
        has_results = any([
            "accessibility_issues" in data,
            "wcag_analysis" in data,
            "issues" in data,
            "crew_analysis" in data,
            "pa11y" in data,
            "axe" in data,
            "lighthouse" in data
        ])
        
        if not has_results:
            self.logger.warning("No accessibility issues found in results")

    async def save_results(self, url: str, crew_results: Dict[str, Any]) -> Path:
        """
        Speichert Analyseergebnisse und generiert Berichte
        
        Args:
            url: Getestete URL
            crew_results: Ergebnisse der Crew-Analyse
            
        Returns:
            Pfad zum Ausgabeverzeichnis
        """
        try:
            # Validiere Eingabedaten
            self.validate_report_data(crew_results)
            
            # Erstelle zeitstempelbasierten Verzeichnisnamen
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            sanitized_url = self._sanitize_url_for_filename(url)
            output_dir = self.output_base_path / f"{timestamp}_{sanitized_url}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Speichere Rohergebnisse
            await self._save_json_file(
                output_dir / "crew_results.json",
                crew_results
            )
            
            # Kopiere CSS wenn vorhanden
            if self.css_path.exists():
                shutil.copy2(self.css_path, output_dir / "report_styles.css")
                self.logger.info("CSS styles copied successfully")
            else:
                self.logger.warning("CSS template file not found")
            
            # Generiere HTML Report
            await self.generate_html_report(crew_results, output_dir)
            
            # Erstelle README
            await self._create_readme(output_dir, url, crew_results)
            
            self.logger.info(f"Results saved to {output_dir}")
            return output_dir
            
        except Exception as e:
            error_msg = f"Failed to save results: {str(e)}"
            self.logger.error(error_msg)
            raise ReportGenerationError(error_msg)

    async def _create_readme(self, output_dir: Path, url: str, results: Dict[str, Any]) -> None:
        """Erstellt eine README-Datei mit Metadaten"""
        readme_content = f"""
            WCAG 2.2 Accessibility Report
            Generated: {datetime.now(timezone.utc).isoformat()}
            URL: {url}
            
            This directory contains:
            - crew_results.json: Raw analysis results
            - report_styles.css: Report styling
            - accessibility_report.html: Complete accessibility report
            
            Summary:
            - Total Issues: {results.get('summary', {}).get('total_issues', 0)}
            - Status: {results.get('status', 'unknown')}
        """.strip()
        
        readme_file = output_dir / "README.txt"
        async with aiofiles.open(readme_file, 'w') as f:
            await f.write(readme_content)

    def _sanitize_url_for_filename(self, url: str) -> str:
        """Konvertiert URL in sicheren Dateinamen"""
        url = url.split('://')[-1]
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            url = url.replace(char, '_')
        return url[:50]

    async def _save_json_file(self, filepath: Path, data: Dict[str, Any]) -> None:
        """Speichert Daten als JSON-Datei"""
        try:
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            self.logger.error(f"Error saving JSON file {filepath}: {e}")
            raise

    async def generate_html_report(self, results: Dict[str, Any], output_dir: Path) -> None:
        """Generiert einen HTML-Bericht aus den Analyseergebnissen"""
        try:
            # HTML-Teile zusammenstellen
            html_parts = [
                self._generate_html_header("WCAG 2.2 Accessibility Report"),
                self._generate_summary_section(results),
                self._generate_issues_section(results),
                self._generate_recommendations_section(results),
                self._generate_html_footer()
            ]
            
            # HTML-Datei speichern
            report_content = "\n".join(html_parts)
            report_file = output_dir / "accessibility_report.html"
            
            async with aiofiles.open(report_file, 'w', encoding='utf-8') as f:
                await f.write(report_content)
                
            self.logger.info(f"HTML report generated: {report_file}")
            
        except Exception as e:
            error_msg = f"Error generating HTML report: {str(e)}"
            self.logger.error(error_msg)
            raise TemplateError(error_msg)

    def _generate_html_header(self, title: str) -> str:
        """Generiert HTML-Header mit Metadaten"""
        return f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta name="description" content="WCAG 2.2 Accessibility Analysis Report">
                <title>{title}</title>
                <link rel="stylesheet" href="report_styles.css">
            </head>
            <body>
                <header class="report-header">
                    <h1>{title}</h1>
                </header>
                <main>
        """

    def _generate_summary_section(self, results: Dict[str, Any]) -> str:
        """Generiert die Zusammenfassungssektion"""
        self.logger.debug(f"Generating summary section with results keys: {results.keys()}")
        
        # Sammle alle Issues aus verschiedenen Quellen
        all_issues = []
        
        # Durchsuche verschiedene mögliche Quellen für Issues
        if "wcag_analysis" in results:
            wcag_data = results["wcag_analysis"]
            if isinstance(wcag_data, dict):
                if "accessibility_issues" in wcag_data:
                    all_issues.extend(wcag_data["accessibility_issues"])
                elif "issues" in wcag_data:
                    all_issues.extend(wcag_data["issues"])

        if "crew_analysis" in results and isinstance(results["crew_analysis"], dict):
            if "issues" in results["crew_analysis"]:
                all_issues.extend(results["crew_analysis"]["issues"])

        if "issues" in results:
            all_issues.extend(results["issues"])

        if "accessibility_issues" in results:
            all_issues.extend(results["accessibility_issues"])

        # Berechne Statistiken
        total_issues = len(all_issues)
        by_level = {"A": 0, "AA": 0, "AAA": 0}
        by_tool = {}

        for issue in all_issues:
            # Zähle nach Level
            level = issue.get("level", "").upper().replace(" ", "")
            if level in by_level:
                by_level[level] += 1

            # Zähle nach Tool
            tool = issue.get("tool", "unknown")
            by_tool[tool] = by_tool.get(tool, 0) + 1

        self.logger.info(f"Summary statistics: {total_issues} total issues, {by_level} by level, {by_tool} by tool")
        
        return f"""
            <section id="summary" class="report-section">
                <h2>Executive Summary</h2>
                
                <div class="summary-grid">
                    <div class="summary-card total-issues">
                        <h3>Total Issues Found</h3>
                        <div class="count">{total_issues}</div>
                    </div>
                    
                    <div class="summary-card level-breakdown">
                        <h3>Issues by WCAG Level</h3>
                        <ul class="stat-list">
                            <li>Level A: <span class="level-a badge">{by_level['A']}</span></li>
                            <li>Level AA: <span class="level-aa badge">{by_level['AA']}</span></li>
                            <li>Level AAA: <span class="level-aaa badge">{by_level['AAA']}</span></li>
                        </ul>
                    </div>
                    
                    <div class="summary-card tool-breakdown">
                        <h3>Issues by Tool</h3>
                        <ul class="stat-list">
                            {self._generate_tool_list(by_tool)}
                        </ul>
                    </div>
                </div>
            </section>
        """

    def _generate_issues_section(self, results: Dict[str, Any]) -> str:
        """Generiert die Sektion mit den gefundenen Problemen"""
        
        # Hole die Issues direkt aus dem results Dictionary
        issues = results.get("issues", [])
        self.logger.info(f"Processing {len(issues)} issues for report")
        
        if not issues:
            self.logger.warning("No issues found")
            return '<section class="report-section"><h2>Issues</h2><p>No issues found.</p></section>'
        
        issues_html = []
        for issue in issues:
            self.logger.debug(f"Processing issue: {issue.keys() if isinstance(issue, dict) else 'not a dict'}")
            
            # Extrahiere die relevanten Informationen
            description = issue.get("description", "No description provided")
            criterion_id = issue.get("criterion_id", "Unknown")
            level = issue.get("level", "Unknown")
            impact = issue.get("impact", "Unknown")
            severity = issue.get("severity", "moderate")
            remediation_steps = issue.get("remediation_steps", [])

            # Bestimme den Schweregrad für die CSS-Klasse
            if isinstance(severity, str):
                severity = {
                    "critical": 1,
                    "high": 2,
                    "medium": 3,
                    "low": 4
                }.get(severity.lower(), 3)
            
            severity_class = self._get_severity_class(severity)
            
            # Generiere das HTML für dieses Issue
            issues_html.append(f"""
                <div class="issue {severity_class}">
                    <h4>{description}</h4>
                    <div class="issue-details">
                        <p><strong>WCAG Criterion:</strong> {criterion_id}</p>
                        <p><strong>Level:</strong> {level}</p>
                        <p><strong>Impact:</strong> {impact}</p>
                    </div>
                    {self._generate_technical_details(issue)}
                    {self._generate_remediation_section({'remediation_steps': remediation_steps})}
                </div>
            """)
            
        return f"""
            <section id="issues" class="report-section">
                <h2>Detailed Findings ({len(issues)} issues)</h2>
                {''.join(issues_html)}
            </section>
        """
    
    def _generate_recommendations_section(self, results: Dict[str, Any]) -> str:
        """Generiert die Empfehlungssektion"""
        # Suche nach Empfehlungen in verschiedenen möglichen Stellen
        recommendations = []
        
        # Prüfe verschiedene mögliche Pfade für Empfehlungen
        if "remediation_guidance" in results:
            if isinstance(results["remediation_guidance"], dict):
                recommendations.append(results["remediation_guidance"])
            elif isinstance(results["remediation_guidance"], list):
                recommendations.extend(results["remediation_guidance"])
                
        if "wcag_analysis" in results and "recommendations" in results["wcag_analysis"]:
            recommendations.extend(results["wcag_analysis"]["recommendations"])
            
        if "crew_analysis" in results and "recommendations" in results["crew_analysis"]:
            recommendations.extend(results["crew_analysis"]["recommendations"])
            
        if not recommendations:
            return ""  # Keine Empfehlungen gefunden
            
        recommendations_html = []
        for rec in recommendations:
            if isinstance(rec, str):
                # Behandle einfache String-Empfehlungen
                recommendations_html.append(f"""
                    <div class="recommendation">
                        <p>{rec}</p>
                    </div>
                """)
            elif isinstance(rec, dict):
                # Behandle strukturierte Empfehlungen
                title = rec.get("title", "")
                description = rec.get("description", "")
                steps = rec.get("steps", [])
                guidance = rec.get("guidance", "")
                
                recommendations_html.append(f"""
                    <div class="recommendation">
                        {f'<h4>{title}</h4>' if title else ''}
                        {f'<p>{description}</p>' if description else ''}
                        {self._format_steps(steps) if steps else ''}
                        {f'<p class="guidance">{guidance}</p>' if guidance else ''}
                    </div>
                """)
        
        return f"""
            <section id="recommendations" class="report-section">
                <h2>Recommendations</h2>
                <div class="recommendations-container">
                    {''.join(recommendations_html)}
                </div>
            </section>
        """

    def _generate_technical_details(self, issue: Dict[str, Any]) -> str:
        """Generiert technische Details für ein Problem"""
        if not (issue.get("selector") or issue.get("context")):
            return ""
            
        details = []
        
        if issue.get("selector"):
            details.append(f"""
                <div class="selector">
                    <strong>Selector:</strong>
                    <code>{issue["selector"]}</code>
                </div>
            """)
            
        if issue.get("context"):
            details.append(f"""
                <div class="context">
                    <strong>Context:</strong>
                    <pre>{issue["context"]}</pre>
                </div>
            """)
            
        return f"""
            <div class="technical-details">
                {''.join(details)}
            </div>
        """

    def _format_steps(self, steps: List[str]) -> str:
        """Formatiert eine Liste von Schritten als HTML-Liste"""
        if not steps:
            return ""
            
        steps_html = []
        for step in steps:
            steps_html.append(f"<li>{step}</li>")
            
        return f"<ol class='steps'>{''.join(steps_html)}</ol>"

    def _generate_tool_list(self, tool_stats: Dict[str, int]) -> str:
        """Generiert eine formatierte Liste der Tool-Ergebnisse"""
        tool_items = []
        for tool, count in tool_stats.items():
            tool_items.append(
                f'<li>{tool}: <span class="tool-count">{count}</span></li>'
            )
        return '\n'.join(tool_items)

    def _generate_priority_recommendations(self, results: Dict[str, Any]) -> str:
        """Generiert priorisierte Empfehlungen"""
        if not results:
            return "<p>No recommendations available.</p>"
            
        issues = results.get("issues", [])
        critical_issues = [i for i in issues if i.get("severity", 3) == 1][:3]
        
        if not critical_issues:
            return "<p>No critical issues found.</p>"
            
        recommendations = ['<ul class="priority-list">']
        for issue in critical_issues:
            recommendations.append(f"""
                <li class="priority-item">
                    <h4>{issue.get('description', 'Unknown Issue')}</h4>
                    <p>WCAG Criterion: {issue.get('wcag_criterion', {}).get('id', 'Unknown')}</p>
                    {self._format_remediation_steps(issue.get('remediation_steps', []))}
                </li>
            """)
        recommendations.append('</ul>')
        
        return '\n'.join(recommendations)

    def _format_remediation_steps(self, steps: List[str]) -> str:
        """Formatiert Behebungsschritte"""
        if not steps:
            return ""
            
        steps_html = []
        for step in steps:
            steps_html.append(f"<li>{step}</li>")
            
        return f'<ol class="remediation-steps">{"".join(steps_html)}</ol>'

    def _get_severity_class(self, severity: int) -> str:
        """Bestimmt die CSS-Klasse basierend auf dem Schweregrad"""
        severity_classes = {
            1: "critical",
            2: "serious",
            3: "moderate",
            4: "minor"
        }
        return severity_classes.get(severity, "moderate")

    def _generate_html_footer(self) -> str:
        """Generiert HTML-Footer mit Zeitstempel"""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        return f"""
                </main>
                <footer class="report-footer">
                    <div class="footer-content">
                        <p>Report generated: {timestamp}</p>
                        <p>Generated by WCAG 2.2 Testing Tool</p>
                    </div>
                </footer>
            </body>
            </html>
        """