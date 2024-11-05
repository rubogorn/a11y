# src/wcag/wcag_mapping_agent.py

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
from crewai import Agent, Task, Crew, Process
from src.logging_config import get_logger
from .unified_result_processor import (
    UnifiedResultProcessor,
    AccessibilityIssue,
    WCAGReference,
    WCAGLevel,
    IssueSeverity
)

class WCAGMappingAgent:
    """
    WCAG 2.2 Mapping durch den wcag_checkpoints Agenten.
    Ersetzt die JSON-basierte Implementierung durch Agenten-Intelligenz.
    """

    def __init__(self):
        """Initialisiert den WCAGMappingAgent"""
        self.logger = get_logger('WCAGMappingAgent')
        
        # Agent initialisieren
        self.agent = Agent(
            role="WCAG 2.2 Criteria Mapping Specialist",
            goal="Map accessibility issues to WCAG 2.2 criteria and provide detailed guidance",
            backstory="""You are an expert in WCAG 2.2 guidelines who specializes in analyzing 
            test results and mapping them to specific WCAG criteria. You provide structured data 
            for report generation including criteria details, recommendations, and severity assessments.
            You have complete knowledge of all WCAG 2.2 success criteria, techniques, and failures.""",
            allow_delegation=False,
            verbose=True
        )

    async def analyze_accessibility_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analysiert ein einzelnes Accessibility-Problem und mappt es auf WCAG-Kriterien
        
        Args:
            issue: Das zu analysierende Accessibility-Problem
            
        Returns:
            WCAG-Mapping und Analyse
        """
        try:
            # Task für die Analyse erstellen
            analysis_task = Task(
                description=f"""
                Analyze the following accessibility issue and provide detailed WCAG 2.2 mapping:

                Issue Description: {issue.get('message', '')}
                Technical Context: {issue.get('context', '')}
                Element: {issue.get('selector', '')}
                
                Provide:
                1. Specific WCAG 2.2 criterion mapping
                2. Conformance level (A, AA, AAA)
                3. Detailed explanation of the mapping
                4. Relevant techniques and failures
                5. Implementation recommendations
                
                Format the response as structured data suitable for report generation.
                """,
                agent=self.agent
            )

            # Temporäre Crew für die Analyse erstellen
            analysis_crew = Crew(
                agents=[self.agent],
                tasks=[analysis_task],
                process=Process.sequential,
                verbose=True
            )

            # Analyse durchführen
            result = await analysis_crew.kickoff()
            
            # Ergebnis verarbeiten
            processed_result = await self._process_analysis_result(result, issue)
            
            return processed_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing accessibility issue: {str(e)}")
            return self._create_error_result(issue, str(e))

    async def _process_analysis_result(self, 
                                     result: Dict[str, Any], 
                                     original_issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet die Antwort des WCAG-Agenten
        
        Args:
            result: Analyse-Ergebnis des Agenten
            original_issue: Ursprüngliches Issue
            
        Returns:
            Verarbeitetes WCAG-Mapping
        """
        try:
            # Extrahiere WCAG-Kriterien
            wcag_refs = []
            if "wcag_criteria" in result:
                for criterion in result["wcag_criteria"]:
                    wcag_refs.append(WCAGReference(
                        criterion_id=criterion.get("id", "unknown"),
                        level=WCAGLevel[criterion.get("level", "A")],
                        description=criterion.get("description", ""),
                        techniques=criterion.get("techniques", []),
                        failures=criterion.get("failures", [])
                    ))
            
            # Erstelle AccessibilityIssue
            issue = AccessibilityIssue(
                description=original_issue.get("message", ""),
                type=original_issue.get("type", "unknown"),
                severity=self._map_severity(result.get("severity", 3)),
                wcag_refs=wcag_refs,
                tools=[original_issue.get("tool", "unknown")],
                context=original_issue.get("context"),
                selector=original_issue.get("selector"),
                code=original_issue.get("code"),
                remediation_steps=result.get("remediation_steps", [])
            )
            
            return self._issue_to_dict(issue)
            
        except Exception as e:
            self.logger.error(f"Error processing analysis result: {str(e)}")
            return self._create_error_result(original_issue, str(e))
        
        def _map_severity(self, severity: Any) -> IssueSeverity:
            """
            Mappt verschiedene Severity-Formate auf IssueSeverity
            
            Args:
                severity: Eingangs-Severity-Wert
                
            Returns:
                Gemappter IssueSeverity-Wert
            """
            if isinstance(severity, IssueSeverity):
                return severity
                
            if isinstance(severity, int):
                try:
                    return IssueSeverity(severity)
                except ValueError:
                    return IssueSeverity.MODERATE
                    
            if isinstance(severity, str):
                severity_map = {
                    "critical": IssueSeverity.CRITICAL,
                    "serious": IssueSeverity.SERIOUS,
                    "moderate": IssueSeverity.MODERATE,
                    "minor": IssueSeverity.MINOR
                }
                return severity_map.get(severity.lower(), IssueSeverity.MODERATE)
                
            return IssueSeverity.MODERATE

        def _issue_to_dict(self, issue: AccessibilityIssue) -> Dict[str, Any]:
            """
            Konvertiert ein AccessibilityIssue in ein Dictionary
            
            Args:
                issue: Zu konvertierendes Issue
                
            Returns:
                Dictionary-Repräsentation des Issues
            """
            return {
                "description": issue.description,
                "type": issue.type,
                "severity": issue.severity.value,
                "wcag_references": [
                    {
                        "criterion_id": ref.criterion_id,
                        "level": ref.level.name,
                        "description": ref.description,
                        "techniques": ref.techniques,
                        "failures": ref.failures
                    }
                    for ref in issue.wcag_refs
                ],
                "tools": issue.tools,
                "context": issue.context,
                "selector": issue.selector,
                "code": issue.code,
                "remediation_steps": issue.remediation_steps,
                "timestamp": issue.timestamp
            }

        def _create_error_result(self, issue: Dict[str, Any], error: str) -> Dict[str, Any]:
            """
            Erstellt ein standardisiertes Fehlerergebnis
            
            Args:
                issue: Ursprüngliches Issue
                error: Fehlermeldung
                
            Returns:
                Fehlerergebnis als Dictionary
            """
            return {
                "error": str(error),
                "original_issue": issue,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        async def generate_remediation_guidance(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
            """
            Generiert detaillierte Behebungsempfehlungen
            
            Args:
                mapping: WCAG-Mapping eines Issues
                
            Returns:
                Detaillierte Empfehlungen zur Problembehebung
            """
            try:
                # Task für Empfehlungsgenerierung erstellen
                guidance_task = Task(
                    description=f"""
                    Generate detailed remediation guidance for the following accessibility issue:

                    Issue: {mapping.get('original_issue', {}).get('message', '')}
                    WCAG Criterion: {mapping.get('wcag_criterion', {}).get('id', '')}
                    Level: {mapping.get('wcag_criterion', {}).get('level', '')}
                    
                    Provide:
                    1. Step-by-step solution
                    2. Code examples
                    3. Implementation guidelines
                    4. Testing procedures
                    5. Best practices
                    
                    Format the response as structured guidance suitable for developers.
                    """,
                    agent=self.agent
                )

                # Crew für die Guidance-Generierung
                guidance_crew = Crew(
                    agents=[self.agent],
                    tasks=[guidance_task],
                    process=Process.sequential
                )

                # Führe die Analyse durch
                result = await guidance_crew.kickoff_async(inputs={
                    "issue": mapping.get('original_issue', {}),
                    "wcag_criterion": mapping.get('wcag_criterion', {})
                })
                
                if isinstance(result, dict) and result.get('error'):
                    raise Exception(f"Error in guidance generation: {result.get('error')}")
                
                # Verarbeite das Ergebnis
                guidance = result.get('raw_output', str(result))
                
                return {
                    "issue_id": mapping.get("original_issue", {}).get("id", "unknown"),
                    "wcag_criterion": mapping.get("wcag_criterion", {}).get("id", "unknown"),
                    "guidance": guidance,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error generating remediation guidance: {str(e)}")
                return {
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }