from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import logging
from crewai import Agent, Task, Crew, Process

class WCAGLevel(Enum):
    A = "A"
    AA = "AA"
    AAA = "AAA"

@dataclass
class WCAGCriterion:
    id: str
    title: str
    level: WCAGLevel
    description: str
    principle: str
    guideline: str
    success_criteria: List[str]
    techniques: List[str]
    failures: List[str]

class AgentBasedWCAGMapper:
    """
    WCAG 2.2 Mapping durch den wcag_checkpoints Agenten.
    Ersetzt die JSON-basierte Implementierung durch Agenten-Intelligenz.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialisiert den Agent-basierten WCAG Mapper"""
        self.logger = logger or logging.getLogger(__name__)
        
        # Definiere den WCAG Checkpoints Agenten
        self.wcag_agent = Agent(
            role="WCAG 2.2 Criteria Mapping Specialist",
            goal="Map accessibility issues to WCAG 2.2 criteria and provide detailed guidance",
            backstory="""You are an expert in WCAG 2.2 guidelines who specializes in analyzing 
            test results and mapping them to specific WCAG criteria. You provide structured data 
            for report generation including criteria details, recommendations, and severity assessments.
            You have complete knowledge of all WCAG 2.2 success criteria, techniques, and failures.""",
            allow_delegation=False,
            verbose=True
        )

    async def analyze_and_map_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analysiert und mappt Accessibility-Issues auf WCAG 2.2 Kriterien
        
        Args:
            issues: Liste von gefundenen Accessibility-Problemen
            
        Returns:
            Dictionary mit WCAG-Mapping und Empfehlungen
        """
        try:
            # Erstelle Task für den WCAG-Agenten
            mapping_task = Task(
                description=f"""
                Analyze the following accessibility issues and map them to WCAG 2.2 criteria:
                
                Issues:
                {issues}
                
                For each issue:
                1. Identify the relevant WCAG 2.2 criterion/criteria
                2. Determine the conformance level (A, AA, AAA)
                3. Provide detailed success criteria descriptions
                4. Add specific techniques for remediation
                5. Include relevant failure conditions
                6. Assess the severity based on impact
                
                Structure the response as a detailed JSON with:
                - Criterion ID
                - Title
                - Level
                - Description
                - Mapping rationale
                - Remediation steps
                """,
                agent=self.wcag_agent
            )

            # Erstelle temporäre Crew für die Mapping-Aufgabe
            mapping_crew = Crew(
                agents=[self.wcag_agent],
                tasks=[mapping_task],
                process=Process.sequential
            )

            # Führe die Analyse durch
            results = await mapping_crew.kickoff()
            
            return self._process_agent_response(results)

        except Exception as e:
            self.logger.error(f"Fehler beim WCAG-Mapping: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _process_agent_response(self, agent_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet die Antwort des WCAG-Agenten in ein strukturiertes Format
        
        Args:
            agent_response: Rohantwort des Agenten
            
        Returns:
            Strukturiertes WCAG-Mapping
        """
        try:
            # Extrahiere die relevanten Informationen aus der Agenten-Antwort
            processed_results = {
                "mappings": [],
                "summary": {
                    "total_issues": 0,
                    "by_level": {
                        "A": 0,
                        "AA": 0,
                        "AAA": 0
                    },
                    "by_principle": {}
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Verarbeite die einzelnen Mappings
            if isinstance(agent_response, dict) and "mappings" in agent_response:
                for mapping in agent_response["mappings"]:
                    processed_mapping = {
                        "criterion": {
                            "id": mapping.get("criterion_id"),
                            "title": mapping.get("title"),
                            "level": mapping.get("level"),
                            "description": mapping.get("description")
                        },
                        "rationale": mapping.get("rationale"),
                        "remediation": mapping.get("remediation", []),
                        "severity": self._calculate_severity(
                            mapping.get("level"),
                            mapping.get("impact")
                        )
                    }
                    processed_results["mappings"].append(processed_mapping)
                    
                    # Aktualisiere die Zusammenfassung
                    processed_results["summary"]["total_issues"] += 1
                    processed_results["summary"]["by_level"][mapping.get("level", "A")] += 1
                    
                    # Gruppiere nach Prinzipien
                    principle = mapping.get("principle")
                    if principle:
                        if principle not in processed_results["summary"]["by_principle"]:
                            processed_results["summary"]["by_principle"][principle] = {
                                "count": 0,
                                "issues": []
                            }
                        processed_results["summary"]["by_principle"][principle]["count"] += 1
                        processed_results["summary"]["by_principle"][principle]["issues"].append(
                            mapping.get("criterion_id")
                        )

            return processed_results

        except Exception as e:
            self.logger.error(f"Fehler bei der Verarbeitung der Agenten-Antwort: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _calculate_severity(self, wcag_level: str, impact: Optional[str]) -> int:
        """
        Berechnet den Schweregrad basierend auf WCAG-Level und Auswirkung
        
        Args:
            wcag_level: WCAG-Konformitätslevel (A, AA, AAA)
            impact: Beschreibung der Auswirkung
            
        Returns:
            Schweregrad (1-4, wobei 1 am schwerwiegendsten ist)
        """
        # Basis-Schweregrad nach WCAG-Level
        base_severity = {
            "A": 1,     # Kritisch
            "AA": 2,    # Schwerwiegend
            "AAA": 3    # Moderat
        }.get(wcag_level, 3)
        
        # Anpassung basierend auf Auswirkung
        if impact:
            impact = impact.lower()
            if impact in ["critical", "severe", "serious"]:
                base_severity = max(1, base_severity - 1)
            elif impact in ["moderate"]:
                base_severity = min(3, base_severity)
            elif impact in ["minor", "cosmetic"]:
                base_severity = min(4, base_severity + 1)
                
        return base_severity