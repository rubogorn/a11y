# src/wcag/wcag_mapping_agent.py

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
import asyncio
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
                expected_output="Structured JSON containing WCAG criterion mapping, level assessment, and implementation details",
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
        

    async def batch_analyze_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analysiert mehrere Accessibility-Issues in einem Batch-Prozess
        
        Args:
            issues: Liste von Accessibility-Issues
            
        Returns:
            Dictionary mit WCAG-Mappings und Analysen
        """
        try:
            self.logger.info(f"Starting batch analysis of {len(issues)} issues")
            
            # Initialisiere das Ergebnis-Dictionary
            batch_results = {
                "accessibility_issues": [],
                "summary": {
                    "total_issues": 0,
                    "by_level": {"A": 0, "AA": 0, "AAA": 0},
                    "by_severity": {1: 0, 2: 0, 3: 0, 4: 0},
                    "by_principle": {}
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Verarbeite jedes Issue asynchron
            analysis_tasks = [
                self.analyze_accessibility_issue(issue)
                for issue in issues
            ]
            
            # Warte auf alle Analysen
            individual_results = await asyncio.gather(
                *analysis_tasks,
                return_exceptions=True
            )

            # Verarbeite die Ergebnisse
            for result in individual_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Error in batch processing: {str(result)}")
                    continue
                    
                if "error" in result:
                    self.logger.warning(f"Analysis error: {result['error']}")
                    continue
                    
                if not isinstance(result, dict):
                    self.logger.warning(f"Unexpected result type: {type(result)}")
                    continue

                # Füge das Issue zu den Ergebnissen hinzu
                batch_results["accessibility_issues"].append(result)
                
                # Aktualisiere die Zusammenfassung
                batch_results["summary"]["total_issues"] += 1
                
                # Zähle nach Level
                for ref in result.get("wcag_references", []):
                    level = ref.get("level", "A")
                    batch_results["summary"]["by_level"][level] += 1
                    
                    # Gruppiere nach Prinzip (erstes Zeichen der Criterion ID)
                    criterion_id = ref.get("criterion_id", "")
                    if criterion_id:
                        principle = criterion_id[0]
                        if principle not in batch_results["summary"]["by_principle"]:
                            batch_results["summary"]["by_principle"][principle] = {
                                "count": 0,
                                "criteria": set()
                            }
                        batch_results["summary"]["by_principle"][principle]["count"] += 1
                        batch_results["summary"]["by_principle"][principle]["criteria"].add(criterion_id)
                
                # Zähle nach Severity
                severity = result.get("severity", 3)
                batch_results["summary"]["by_severity"][severity] += 1

            # Konvertiere Criterion-Sets zu Listen für JSON-Serialisierung
            for principle in batch_results["summary"]["by_principle"].values():
                principle["criteria"] = sorted(list(principle["criteria"]))

            self.logger.info(
                f"Batch analysis completed: {batch_results['summary']['total_issues']} issues processed"
            )
            return batch_results

        except Exception as e:
            error_msg = f"Error in batch analysis: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
    

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

    async def generate_remediation_guidance(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generiert detaillierte Behebungsempfehlungen für ein WCAG-Issue
        
        Args:
            issue_data: Dictionary mit Issue-Informationen
                {
                    'criterion_id': str,
                    'level': str,
                    'description': str,
                    ...
                }
                
        Returns:
            Dictionary mit Behebungsempfehlungen
        """
        try:
            self.logger.info(f"Generating remediation guidance for criterion {issue_data.get('criterion_id')}")
            
            # Task für die Empfehlungsgenerierung erstellen
            guidance_task = Task(
                description=f"""
                Generate detailed remediation guidance for the following WCAG issue:

                WCAG Criterion: {issue_data.get('criterion_id')}
                Level: {issue_data.get('level')}
                Description: {issue_data.get('description')}
                
                Provide:
                1. Step-by-step solution steps
                2. Code examples where applicable
                3. Best practices and implementation guidelines
                4. Testing steps for validation
                5. Alternative approaches if relevant
                
                Structure the response as detailed JSON with:
                - steps: array of clear solution steps
                - code_examples: array of relevant code snippets
                - testing_procedures: array of validation steps
                - best_practices: array of recommended practices
                - references: array of useful resources
                """,
                expected_output="Structured JSON containing detailed remediation guidance including steps, code examples, and best practices",
                agent=self.agent
            )

            # Temporäre Crew für die Empfehlungsgenerierung
            guidance_crew = Crew(
                agents=[self.agent],
                tasks=[guidance_task],
                process=Process.sequential,
                verbose=True  # Aktiviere Logging für bessere Fehlerbehebung
            )

            # Führe die Analyse durch
            self.logger.debug("Starting guidance generation with crew")
            result = await guidance_crew.kickoff()
            self.logger.debug(f"Received guidance generation result: {result}")
            
            # Verarbeite und strukturiere die Ergebnisse
            processed_guidance = self._process_guidance_response(result, issue_data)
            
            return processed_guidance

        except Exception as e:
            error_msg = f"Error generating remediation guidance: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "criterion_id": issue_data.get("criterion_id", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
    def _process_guidance_response(self, response: Dict[str, Any], original_issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet die Antwort des Agenten zur Empfehlungsgenerierung
        
        Args:
            response: Antwort des Agenten
            original_issue: Ursprüngliches Issue
            
        Returns:
            Strukturierte Empfehlungen
        """
        try:
            self.logger.debug("Processing guidance response")
            
            # Initialisiere die Basisstruktur für die Empfehlungen
            guidance = {
                "criterion_id": original_issue.get("criterion_id", "unknown"),
                "level": original_issue.get("level", "A"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "remediation": {
                    "steps": [],
                    "code_examples": [],
                    "testing_procedures": [],
                    "best_practices": [],
                    "references": []
                }
            }

            # Verarbeite die Antwort des Agenten
            if isinstance(response, dict):
                self.logger.debug("Processing structured response")
                
                # Wenn die Antwort bereits in JSON/Dict-Format ist
                if 'raw_output' in response:
                    # Versuche, den String als JSON zu parsen
                    try:
                        import json
                        parsed_output = json.loads(response['raw_output'])
                        if isinstance(parsed_output, dict):
                            guidance["remediation"].update(parsed_output)
                    except (json.JSONDecodeError, TypeError):
                        # Wenn das Parsen fehlschlägt, verwende den Rohtext
                        guidance["remediation"]["steps"].append(str(response['raw_output']))
                else:
                    # Verwende die strukturierten Daten direkt
                    guidance["remediation"].update(response.get("remediation", {}))
                    
            elif isinstance(response, str):
                self.logger.debug("Processing string response")
                # Wenn die Antwort ein String ist, füge sie als einzelnen Schritt hinzu
                guidance["remediation"]["steps"].append(response)
                
            else:
                self.logger.warning(f"Unexpected response type: {type(response)}")
                guidance["remediation"]["steps"].append(
                    "Unexpected response format. Please check with technical support."
                )

            # Validiere und bereinige die Ausgabe
            for key in guidance["remediation"]:
                if not isinstance(guidance["remediation"][key], list):
                    guidance["remediation"][key] = []
                
                # Entferne leere oder None-Einträge
                guidance["remediation"][key] = [
                    item for item in guidance["remediation"][key]
                    if item and isinstance(item, (str, dict))
                ]

            # Füge Metadaten hinzu
            guidance.update({
                "issue_description": original_issue.get("description", ""),
                "context": original_issue.get("context"),
                "selector": original_issue.get("selector"),
                "generated_at": datetime.now(timezone.utc).isoformat()
            })

            self.logger.info(f"Successfully processed guidance for criterion {guidance['criterion_id']}")
            return guidance

        except Exception as e:
            error_msg = f"Error processing guidance response: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "criterion_id": original_issue.get("criterion_id", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
    async def batch_generate_remediation_guidance(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generiert Behebungsempfehlungen für mehrere Issues als Batch
        
        Args:
            issues: Liste von Issues für die Empfehlungen generiert werden sollen
            
        Returns:
            Dictionary mit Empfehlungen für alle Issues und Zusammenfassung
        """
        try:
            self.logger.info(f"Starting batch remediation guidance for {len(issues)} issues")
            
            # Vorbereite die Ergebnisstruktur
            batch_results = {
                "remediation_guidance": [],
                "summary": {
                    "total_issues": len(issues),
                    "successful_guidance": 0,
                    "failed_guidance": 0,
                    "by_level": {"A": 0, "AA": 0, "AAA": 0},
                    "by_criterion": {}
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Erstelle Tasks für alle Issues
            guidance_tasks = []
            for issue in issues:
                try:
                    task = self.generate_remediation_guidance(issue)
                    guidance_tasks.append(task)
                except Exception as e:
                    self.logger.error(f"Error creating task for issue: {str(e)}")
                    batch_results["summary"]["failed_guidance"] += 1
            
            if not guidance_tasks:
                self.logger.warning("No valid tasks created for batch processing")
                return batch_results
            
            # Führe alle Tasks parallel aus
            self.logger.debug(f"Executing {len(guidance_tasks)} guidance tasks")
            results = await asyncio.gather(*guidance_tasks, return_exceptions=True)
            
            # Verarbeite die Ergebnisse
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Task execution failed: {str(result)}")
                    batch_results["summary"]["failed_guidance"] += 1
                    continue
                    
                if isinstance(result, dict):
                    if "error" in result:
                        self.logger.warning(f"Guidance generation error: {result['error']}")
                        batch_results["summary"]["failed_guidance"] += 1
                        continue
                        
                    # Füge erfolgreiche Ergebnisse hinzu
                    batch_results["remediation_guidance"].append(result)
                    batch_results["summary"]["successful_guidance"] += 1
                    
                    # Aktualisiere Statistiken
                    criterion_id = result.get("criterion_id", "unknown")
                    level = result.get("level", "A")
                    
                    # Zähle nach Level
                    if level in batch_results["summary"]["by_level"]:
                        batch_results["summary"]["by_level"][level] += 1
                    
                    # Gruppiere nach Kriterium
                    if criterion_id not in batch_results["summary"]["by_criterion"]:
                        batch_results["summary"]["by_criterion"][criterion_id] = {
                            "count": 0,
                            "level": level,
                            "recommendations": set()
                        }
                        
                    criterion_stats = batch_results["summary"]["by_criterion"][criterion_id]
                    criterion_stats["count"] += 1
                    
                    # Sammle einzigartige Empfehlungen
                    if "remediation" in result:
                        for step in result["remediation"].get("steps", []):
                            criterion_stats["recommendations"].add(str(step))
                
                else:
                    self.logger.warning(f"Unexpected result type: {type(result)}")
                    batch_results["summary"]["failed_guidance"] += 1
            
            # Konvertiere Sets zu Listen für JSON-Serialisierung
            for criterion in batch_results["summary"]["by_criterion"].values():
                criterion["recommendations"] = sorted(list(criterion["recommendations"]))
            
            # Füge Erfolgsrate hinzu
            total = batch_results["summary"]["total_issues"]
            successful = batch_results["summary"]["successful_guidance"]
            batch_results["summary"]["success_rate"] = (
                round(successful / total * 100, 2) if total > 0 else 0
            )
            
            self.logger.info(
                f"Batch guidance generation completed: "
                f"{successful} successful, "
                f"{batch_results['summary']['failed_guidance']} failed"
            )
            
            return batch_results
            
        except Exception as e:
            error_msg = f"Error in batch remediation guidance: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "summary": {
                    "total_issues": len(issues),
                    "successful_guidance": 0,
                    "failed_guidance": len(issues)
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }