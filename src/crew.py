# src/crew.py

from typing import TypedDict, List, Optional, Dict, Any
from crewai import Agent, Task, Crew, Process
from pathlib import Path
import json
import asyncio
from datetime import datetime, timezone

from .wcag.unified_result_processor import UnifiedResultProcessor
from .logging_config import get_logger
from .wcag.wcag_mapping_agent import WCAGMappingAgent
from .wcag.wcag_analyzers import (
    HTMLAnalyzer, 
    Pa11yAnalyzer, 
    AxeAnalyzer, 
    LighthouseAnalyzer
)

class CrewOutput(TypedDict, total=False):
    status: str  # 'completed', 'failed', 'error'
    message: Optional[str]
    issues: List[Dict[str, Any]]
    summary: Dict[str, Any]
    timestamp: str
    url: Optional[str]

class WCAGTestingCrew:
    """WCAG 2.2 Testing Crew mit integriertem WCAG-Manager"""

    def __init__(self):
        """Initialisiert die WCAG Testing Crew mit allen Komponenten"""
        # Basis-Initialisierung
        self.results_path = Path("output/results")
        self.results_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger('WCAGTestingCrew', log_dir='output/results/logs')
        
        # WCAG Integration Manager initialisieren
        self.wcag_agent = WCAGMappingAgent()
        
        # Agenten und Tasks initialisieren
        self._init_agents()
        self._init_tasks()

    def _init_agents(self):
        """Initialisiert alle benötigten Agenten mit spezifischen Rollen"""
        
        # WCAG Checkpoints Agent für Mapping und Analyse
        self.wcag_checkpoints = Agent(
            role="WCAG 2.2 Criteria Mapping Specialist",
            goal="Map accessibility issues to WCAG 2.2 criteria and provide detailed analysis",
            backstory="""You are an expert in WCAG 2.2 guidelines who specializes in analyzing 
            test results and mapping them to specific WCAG criteria. You know all WCAG principles,
            guidelines, success criteria, and techniques. You provide detailed, structured data 
            for report generation including:
            1. Accurate WCAG 2.2 criterion mappings
            2. Severity assessments
            3. Implementation recommendations
            4. Documentation references""",
            verbose=True,
            allow_delegation=False
        )

        # Accessibility Analyzer Agent
        self.accessibility_analyzer = Agent(
            role="Static Content and Structure Analyzer",
            goal="Analyze content and structure for WCAG 2.2 compliance",
            backstory="""You specialize in analyzing web content and structure for accessibility
            issues. You focus on HTML semantics, ARIA implementation, and content structure.
            You provide detailed feedback on:
            1. Document structure and heading hierarchy
            2. ARIA roles and properties
            3. Form accessibility
            4. Content relationships""",
            verbose=True
        )

        # Remediation Specialist Agent
        self.remediation_specialist = Agent(
            role="WCAG 2.2 Remediation Specialist",
            goal="Develop solution strategies for accessibility issues",
            backstory="""You are an expert in creating practical solutions for accessibility
            issues. You understand WCAG 2.2 requirements deeply and provide:
            1. Step-by-step remediation guidance
            2. Code examples and implementation tips
            3. Best practices recommendations
            4. Testing verification steps""",
            verbose=True
        )

        # Compliance Controller Agent
        self.compliance_controller = Agent(
            role="WCAG 2.2 Compliance Controller",
            goal="Oversee and validate the testing process and results",
            backstory="""You manage the overall accessibility testing process and ensure
            quality results. You are responsible for:
            1. Validating test completeness
            2. Verifying WCAG mappings
            3. Ensuring report accuracy
            4. Maintaining testing standards""",
            verbose=True
        )

        # Nach dem compliance_controller Agent hinzufügen:
        # Pa11y Analyzer Agent
        self.pa11y_analyzer = Agent(
            role="Pa11y Test Results Processor and Analyzer",
            goal="Execute Pa11y tests and process results for WCAG compliance analysis",
            backstory="""You are a specialized accessibility testing expert focusing on Pa11y automated testing.
            Your expertise covers automated testing of keyboard navigation, focus management,
            form controls and error messages.""",
            verbose=True,
            allow_delegation=False
        )

        # Axe Analyzer Agent
        self.axe_analyzer = Agent(
            role="Axe Core Test Results Processor and Analyzer",
            goal="Execute and analyze Axe Core tests for comprehensive accessibility assessment",
            backstory="""You are a specialized accessibility testing expert focusing on 
            Axe Core automated testing, especially for dynamic content and JavaScript interactions.""",
            verbose=True,
            allow_delegation=False
        )

        # Lighthouse Analyzer Agent
        self.lighthouse_analyzer = Agent(
            role="Lighthouse Accessibility Test Specialist",
            goal="Execute and analyze Lighthouse accessibility tests",
            backstory="""You are a specialized accessibility testing expert focusing on 
            Lighthouse testing, especially for performance impact and mobile accessibility.""",
            verbose=True,
            allow_delegation=False
        )

    def _init_tasks(self):
        """Initialisiert die Tasks mit WCAG-spezifischen Anforderungen"""
        
        # Task für initiale WCAG-Analyse
        self.analyze_wcag = Task(
            description="""Analyze accessibility issues and map to WCAG 2.2 criteria:
            
            Process each issue and provide:
            1. Specific WCAG 2.2 criterion mapping
            2. Conformance level (A, AA, AAA)
            3. Clear rationale for mapping
            4. Severity assessment
            5. Impact analysis
            
            Structure the response as detailed JSON with:
            - criterion_id
            - level
            - description
            - impact
            - remediation_steps""",
            agent=self.wcag_checkpoints,
            expected_output="""Structured JSON containing WCAG mappings and analysis"""
        )

        # Task für Barrierefreiheitsanalyse
        self.analyze_accessibility = Task(
            description="""Perform detailed accessibility analysis of the content:
            
            Evaluate:
            1. Document structure
            2. ARIA implementation
            3. Form accessibility
            4. Content relationships
            
            Provide detailed findings on:
            - Semantic structure
            - ARIA usage
            - Keyboard interaction
            - Content clarity""",
            agent=self.accessibility_analyzer,
            expected_output="""Detailed analysis of accessibility implementation"""
        )

        # Task für Lösungsentwicklung
        self.develop_solutions = Task(
            description="""Create detailed solutions for identified issues:
            
            For each issue provide:
            1. Step-by-step remediation steps
            2. Code examples
            3. Implementation guidance
            4. Testing steps
            
            Include:
            - Technical requirements
            - Best practices
            - Alternative approaches
            - Validation methods""",
            agent=self.remediation_specialist,
            expected_output="""Comprehensive remediation guidance""",
            context=[self.analyze_wcag]
        )

        # Task für Compliance-Prüfung
        self.validate_compliance = Task(
            description="""Review and validate all analysis results:
            
            Verify:
            1. WCAG mapping accuracy
            2. Severity assessments
            3. Solution completeness
            4. Documentation quality
            
            Ensure:
            - Complete coverage
            - Accurate classifications
            - Clear guidance
            - Proper documentation""",
            agent=self.compliance_controller,
            expected_output="""Validation report with quality assessment""",
            context=[self.analyze_wcag, self.develop_solutions]
        )

        # Task für Pa11y Tests
        self.run_pa11y = Task(
            description="""Execute and analyze Pa11y tests...""",  # Beschreibung aus tasks.yaml
            agent=self.pa11y_analyzer,
            expected_output="JSON report containing Pa11y findings"
        )

        # Task für Axe Tests
        self.run_axe = Task(
            description="""Execute and analyze Axe Core tests...""",  # Beschreibung aus tasks.yaml
            agent=self.axe_analyzer,
            expected_output="JSON report of Axe Core results"
        )

        # Task für Lighthouse Tests
        self.run_lighthouse = Task(
            description="""Execute and analyze Lighthouse tests...""",  # Beschreibung aus tasks.yaml
            agent=self.lighthouse_analyzer,
            expected_output="JSON report of Lighthouse results"
        )

    async def process_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet die Testergebnisse mit WCAG-Integration
        
        Args:
            context: Kontext mit Test-URL und Ergebnissen
            
        Returns:
            Verarbeitete WCAG-Analyseergebnisse
        """
        try:
            url = context.get("url", "")
            normalized_results = context.get("normalized_results", [])

            # Verarbeite die Ergebnisse vom WCAG Agent
            wcag_results = await self.wcag_agent.batch_analyze_issues(normalized_results)
            
            # Kombiniere die verschiedenen Analysen
            all_issues = []

            # Füge accessibility_issues hinzu
            if "accessibility_issues" in wcag_results:
                self.logger.debug("Found accessibility_issues in WCAG results")
                all_issues.extend(wcag_results["accessibility_issues"])
            
            # Füge axe, pa11y, lighthouse Ergebnisse hinzu
            for test_tool in ["axe-core-results", "pa11y", "lighthouse"]:
                if test_tool in wcag_results:
                    if isinstance(wcag_results[test_tool], dict) and "issues" in wcag_results[test_tool]:
                        self.logger.debug(f"Found issues in {test_tool}")
                        all_issues.extend(wcag_results[test_tool]["issues"])
            
            # Erstelle die finale Struktur
            final_results = {
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "total_issues": len(all_issues),
                "issues": all_issues,
                "summary": {
                    "total_issues": len(all_issues),
                    "by_level": {"A": 0, "AA": 0, "AAA": 0},
                    "by_tool": {}
                }
            }

            # Aktualisiere die Statistiken
            for issue in all_issues:
                # Zähle Level
                level = issue.get("level", "").upper()
                if level in final_results["summary"]["by_level"]:
                    final_results["summary"]["by_level"][level] += 1

                # Zähle Tool
                tool = issue.get("tool", "unknown")
                if tool not in final_results["summary"]["by_tool"]:
                    final_results["summary"]["by_tool"][tool] = 0
                final_results["summary"]["by_tool"][tool] += 1

            self.logger.info(f"Processed {len(all_issues)} issues")
            return final_results

        except Exception as e:
            self.logger.error(f"Error processing results: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _serialize_crew_output(self, crew_output: Any) -> dict:
        """Konvertiert CrewOutput in ein serialisierbares Dictionary mit Fehlerbehandlung"""
        try:
            from crewai.crews.crew_output import CrewOutput
            
            # Wenn crew_output ein CrewOutput Objekt ist
            if isinstance(crew_output, CrewOutput):
                output = {
                    "status": "completed",
                    "message": crew_output.raw_output if hasattr(crew_output, 'raw_output') else None,
                    "issues": crew_output.issues if hasattr(crew_output, 'issues') else [],
                    "summary": crew_output.summary if hasattr(crew_output, 'summary') else {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "url": crew_output.url if hasattr(crew_output, 'url') else None
                }
                return output
                
            # Wenn crew_output ein String ist (direkte Ausgabe), verpacke es
            if isinstance(crew_output, str):
                return {
                    "status": "completed",
                    "message": crew_output,
                    "issues": [],
                    "summary": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "url": None
                }

            # Wenn crew_output ein Dictionary ist
            if isinstance(crew_output, dict):
                # Stelle sicher, dass alle erforderlichen Felder vorhanden sind
                output = {
                    "status": crew_output.get("status", "completed"),
                    "message": crew_output.get("message"),
                    "issues": crew_output.get("issues", []),
                    "summary": crew_output.get("summary", {}),
                    "timestamp": crew_output.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "url": crew_output.get("url")
                }
                return output

            # Für andere Typen, erstelle ein Standard-Output
            self.logger.warning(f"Unexpected crew output type: {type(crew_output)}, using default values")
            return {
                "status": "completed",
                "message": str(crew_output) if crew_output is not None else None,
                "issues": [],
                "summary": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": None
            }

        except Exception as e:
            self.logger.error(f"Error serializing crew output: {str(e)}")
            return {
                "status": "error",
                "message": f"Error serializing crew output: {str(e)}",
                "issues": [],
                "summary": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": None
            }

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Führt den kompletten WCAG 2.2 Testprozess aus"""
        try:
            # WCAG-Analyse durchführen
            wcag_results = await self.process_results(context)
            
            # Crew für detaillierte Analyse erstellen
            crew = Crew(
                agents=[
                    self.wcag_checkpoints,
                    self.accessibility_analyzer,
                    self.remediation_specialist,
                    self.compliance_controller,
                    self.pa11y_analyzer,
                    self.axe_analyzer,
                    self.lighthouse_analyzer
                ],
                tasks=[
                    self.analyze_wcag,
                    self.analyze_accessibility,
                    self.run_pa11y,
                    self.run_axe,
                    self.run_lighthouse,
                    self.develop_solutions,
                    self.validate_compliance
                ],
                process=Process.sequential,
                verbose=True
            )
            
            # Crew ausführen und Ergebnisse verarbeiten
            crew_results = await crew.kickoff_async(inputs=context)
            
            # CrewOutput in Dictionary konvertieren
            serialized_crew_results = self._serialize_crew_output(crew_results)
            
            # Ergebnisse kombinieren
            final_results = {
                "wcag_analysis": wcag_results,
                "crew_analysis": serialized_crew_results,
                "status": "completed",  # Expliziter Status
                "url": context.get("url", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Statusbericht erstellen
            if not wcag_results.get("error"):
                remediation_guidance = await self.wcag_agent.generate_remediation_guidance(wcag_results)
                final_results["remediation_guidance"] = remediation_guidance
            
            return final_results

        except Exception as e:
            error_msg = f"Error in run process: {str(e)}"
            self.logger.error(error_msg)
            return {
                "error": error_msg,
                "status": "failed",
                "url": context.get("url", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }