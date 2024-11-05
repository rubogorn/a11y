from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from crewai import Agent, Crew, Process, Task
from src.logging_config import get_logger

class WCAGLevel(Enum):
    A = "A"
    AA = "AA"
    AAA = "AAA"

@dataclass
class WCAGCriterion:
    """Repräsentiert ein WCAG-Erfolgskriterium"""
    id: str
    level: WCAGLevel
    description: str
    url: str
    techniques: List[str]
    failures: List[str]

class WCAGMappingAgent:
    """
    Spezialisierter Agent für WCAG 2.2 Mapping und Analyse.
    Ersetzt die frühere JSON-basierte Implementation.
    """

    def __init__(self):
        """Initialisiert den WCAG Mapping Agent"""
        self.logger = get_logger('WCAGMappingAgent')
        
        # Agent initialisieren
        self.agent = Agent(
            role="WCAG 2.2 Criteria Mapping Specialist",
            goal="Map accessibility issues to WCAG 2.2 criteria and provide detailed analysis",
            backstory="""You are an expert in WCAG 2.2 guidelines with comprehensive knowledge of:
            1. All WCAG 2.2 Principles:
               - Perceivable (1.x)
               - Operable (2.x)
               - Understandable (3.x)
               - Robust (4.x)
               
            2. All Success Criteria:
               - Level A requirements
               - Level AA requirements
               - Level AAA requirements
               
            3. Implementation Techniques:
               - Sufficient techniques
               - Advisory techniques
               - Common failures
               
            4. Testing and Validation:
               - Testing procedures
               - Success metrics
               - Failure conditions""",
            verbose=True
        )
        
        # Analysekonfiguration
        self.analysis_config = {
            "min_confidence": 0.8,
            "detailed_analysis": True,
            "include_techniques": True
        }

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
                agent=self.agent,
                expected_output="Detailed WCAG 2.2 mapping analysis in JSON format"
            )
            
            # Analyse durchführen
            result = await analysis_task.execute()
            
            # Ergebnis verarbeiten und validieren
            processed_result = self._process_analysis_result(result, issue)
            
            return processed_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing accessibility issue: {str(e)}")
            return self._create_error_result(issue, str(e))

    async def batch_analyze_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analysiert mehrere Accessibility-Probleme im Batch
        
        Args:
            issues: Liste von Accessibility-Problemen
            
        Returns:
            Gesammelte WCAG-Mappings und Analysen
        """
        try:
            batch_results = {
                "mappings": [],
                "summary": {
                    "total_issues": len(issues),
                    "mapped_issues": 0,
                    "by_level": {
                        "A": 0,
                        "AA": 0,
                        "AAA": 0
                    },
                    "by_principle": {}
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Alle Issues analysieren
            for issue in issues:
                mapping = await self.analyze_accessibility_issue(issue)
                batch_results["mappings"].append(mapping)
                
                # Summary aktualisieren
                if "wcag_criterion" in mapping:
                    batch_results["summary"]["mapped_issues"] += 1
                    level = mapping["wcag_criterion"].get("level", "A")
                    batch_results["summary"]["by_level"][level] += 1
                    
                    # Nach Prinzip gruppieren
                    principle = mapping["wcag_criterion"]["id"].split(".")[0]
                    if principle not in batch_results["summary"]["by_principle"]:
                        batch_results["summary"]["by_principle"][principle] = {
                            "count": 0,
                            "issues": []
                        }
                    batch_results["summary"]["by_principle"][principle]["count"] += 1
                    batch_results["summary"]["by_principle"][principle]["issues"].append(
                        mapping["wcag_criterion"]["id"]
                    )
            
            return batch_results
            
        except Exception as e:
            self.logger.error(f"Error in batch analysis: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _process_analysis_result(self, result: Dict[str, Any], 
                               original_issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet und validiert das Analyseergebnis
        
        Args:
            result: Rohergebnis der Analyse
            original_issue: Ursprüngliches Issue
            
        Returns:
            Verarbeitetes und validiertes Ergebnis
        """
        try:
            # Grundstruktur erstellen
            processed = {
                "original_issue": original_issue,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": result.get("confidence", 0.0)
            }
            
            # WCAG-Kriterium extrahieren und validieren
            if "wcag_criterion" in result:
                criterion = result["wcag_criterion"]
                processed["wcag_criterion"] = {
                    "id": criterion.get("id", "unknown"),
                    "level": criterion.get("level", "A"),
                    "description": criterion.get("description", ""),
                    "techniques": criterion.get("techniques", []),
                    "failures": criterion.get("failures", [])
                }
                
                # Mapping-Begründung hinzufügen
                processed["mapping_rationale"] = result.get("rationale", "")
                
                # Implementierungsempfehlungen
                if "recommendations" in result:
                    processed["recommendations"] = result["recommendations"]
                
            return processed
            
        except Exception as e:
            self.logger.error(f"Error processing analysis result: {str(e)}")
            return self._create_error_result(original_issue, str(e))

    def _create_error_result(self, issue: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Erstellt ein Fehlerergebnis"""
        return {
            "error": error,
            "original_issue": issue,
            "timestamp": datetime.utcnow().isoformat()
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
                agent=self.agent,
                expected_output="Detailed remediation guidance in JSON format"
            )
            
            # Erstelle temporäre Crew für die Guidance-Generierung
            guidance_crew = Crew(
                agents=[self.agent],
                tasks=[guidance_task],
                process=Process.sequential,
                verbose=True
            )

            # Führe die Analyse durch
            result = await guidance_crew.kickoff_async(inputs={
                "issue": mapping.get('original_issue', {}),
                "wcag_criterion": mapping.get('wcag_criterion', {})
            })
            
            if isinstance(result, dict) and result.get('error'):
                raise Exception(f"Error in guidance generation: {result.get('error')}")
            
            # Verarbeite das Ergebnis
            if hasattr(result, 'raw_output'):
                guidance = result.raw_output
            else:
                guidance = str(result)
            
            return {
                "issue_id": mapping.get("original_issue", {}).get("id", "unknown"),
                "wcag_criterion": mapping.get("wcag_criterion", {}).get("id", "unknown"),
                "guidance": guidance,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating remediation guidance: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }