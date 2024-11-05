from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from enum import Enum

@dataclass
class WCAGIssue:
    """Repräsentiert ein einzelnes WCAG-bezogenes Problem"""
    description: str
    criterion_id: str
    level: str
    severity: int
    tools: List[str]
    context: Optional[str] = None
    selector: Optional[str] = None
    remediation_steps: Optional[List[str]] = None

class WCAGPrinciple(Enum):
    """Die vier WCAG-Grundprinzipien"""
    PERCEIVABLE = "1"
    OPERABLE = "2"
    UNDERSTANDABLE = "3"
    ROBUST = "4"

class WCAGAnalysisResult:
    """
    Strukturierte Analyse von WCAG-Problemen mit detaillierten Berichten
    und Empfehlungen
    """

    def __init__(self, url: str):
        self.url = url
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.issues: List[WCAGIssue] = []
        self.summary: Dict[str, Any] = {
            "total_issues": 0,
            "by_level": {"A": 0, "AA": 0, "AAA": 0},
            "by_principle": {},
            "by_severity": {1: 0, 2: 0, 3: 0, 4: 0}
        }
        self.recommendations: Dict[str, List[str]] = {}

    def add_issue(self, issue: WCAGIssue) -> None:
        """Fügt ein neues Problem hinzu und aktualisiert die Zusammenfassung"""
        self.issues.append(issue)
        self.summary["total_issues"] += 1
        self.summary["by_level"][issue.level] += 1
        self.summary["by_severity"][issue.severity] += 1
        
        # Gruppierung nach Prinzipien
        principle = issue.criterion_id.split(".")[0]
        if principle not in self.summary["by_principle"]:
            self.summary["by_principle"][principle] = {
                "count": 0,
                "issues": []
            }
        self.summary["by_principle"][principle]["count"] += 1
        self.summary["by_principle"][principle]["issues"].append(issue.criterion_id)

    def add_recommendation(self, criterion_id: str, steps: List[str]) -> None:
        """Fügt Empfehlungen für ein bestimmtes Kriterium hinzu"""
        if criterion_id not in self.recommendations:
            self.recommendations[criterion_id] = []
        self.recommendations[criterion_id].extend(steps)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert das Analyseergebnis in ein Dictionary"""
        return {
            "url": self.url,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "issues": [
                {
                    "description": issue.description,
                    "criterion_id": issue.criterion_id,
                    "level": issue.level,
                    "severity": issue.severity,
                    "tools": issue.tools,
                    "context": issue.context,
                    "selector": issue.selector,
                    "remediation_steps": issue.remediation_steps
                }
                for issue in self.issues
            ],
            "recommendations": self.recommendations
        }

class WCAGReportGenerator:
    """
    Generiert detaillierte WCAG-Konformitätsberichte basierend auf 
    den Analyseergebnissen
    """

    def __init__(self, analysis_result: WCAGAnalysisResult):
        self.analysis = analysis_result
        self._init_templates()

    def _init_templates(self) -> None:
        """Initialisiert Berichtsvorlagen basierend auf WCAG-Kriterien"""
        self.templates = {
            "issue_description": """
                WCAG {criterion_id} - {level}
                Description: {description}
                Impact: Severity Level {severity}
                Detected by: {tools}
                Location: {context}
                Selector: {selector}
            """.strip(),
            
            "recommendation": """
                To address this issue:
                {steps}
                
                Reference: WCAG {criterion_id}
                Success Criterion: {level}
            """.strip()
        }

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generiert einen Zusammenfassungsbericht"""
        return {
            "overview": {
                "url": self.analysis.url,
                "scan_date": self.analysis.timestamp,
                "total_issues": self.analysis.summary["total_issues"]
            },
            "compliance_levels": {
                level: count 
                for level, count in self.analysis.summary["by_level"].items()
            },
            "severity_breakdown": {
                f"level_{level}": count
                for level, count in self.analysis.summary["by_severity"].items()
            },
            "principles_affected": {
                principle: details
                for principle, details in self.analysis.summary["by_principle"].items()
            }
        }

    def generate_detailed_report(self) -> Dict[str, Any]:
        """Generiert einen detaillierten Bericht mit allen Problemen"""
        return {
            "metadata": {
                "url": self.analysis.url,
                "timestamp": self.analysis.timestamp,
                "total_issues": len(self.analysis.issues)
            },
            "issues": [
                {
                    "description": self._format_issue_description(issue),
                    "recommendation": self._format_recommendation(issue),
                    "details": {
                        "criterion": issue.criterion_id,
                        "level": issue.level,
                        "severity": issue.severity,
                        "tools": issue.tools,
                        "technical": {
                            "context": issue.context,
                            "selector": issue.selector
                        }
                    }
                }
                for issue in self.analysis.issues
            ],
            "recommendations_summary": self.analysis.recommendations,
            "statistics": self.generate_summary_report()
        }

    def _format_issue_description(self, issue: WCAGIssue) -> str:
        """Formatiert die Problembeschreibung"""
        return self.templates["issue_description"].format(
            criterion_id=issue.criterion_id,
            level=issue.level,
            description=issue.description,
            severity=issue.severity,
            tools=", ".join(issue.tools),
            context=issue.context or "N/A",
            selector=issue.selector or "N/A"
        )

    def _format_recommendation(self, issue: WCAGIssue) -> str:
        """Formatiert die Empfehlungen"""
        if not issue.remediation_steps:
            return "No specific remediation steps provided."
            
        steps_text = "\n".join(
            f"  {i+1}. {step}" 
            for i, step in enumerate(issue.remediation_steps)
        )
        
        return self.templates["recommendation"].format(
            steps=steps_text,
            criterion_id=issue.criterion_id,
            level=issue.level
        )

class WCAGComplianceTracker:
    """
    Verfolgt den WCAG-Konformitätsstatus über mehrere Tests hinweg
    und identifiziert Verbesserungen oder Verschlechterungen
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        
    def add_result(self, result: WCAGAnalysisResult) -> None:
        """Fügt ein neues Testergebnis zur Historie hinzu"""
        self.history.append({
            "timestamp": result.timestamp,
            "url": result.url,
            "summary": result.summary.copy()
        })
        
    def get_trend_analysis(self) -> Dict[str, Any]:
        """Analysiert Trends in der WCAG-Konformität"""
        if len(self.history) < 2:
            return {"status": "insufficient_data"}
            
        latest = self.history[-1]
        previous = self.history[-2]
        
        def calculate_change(current: int, past: int) -> Dict[str, Any]:
            diff = current - past
            percent = ((current - past) / past * 100) if past != 0 else 0
            return {
                "difference": diff,
                "percentage": round(percent, 2),
                "trend": "improved" if diff < 0 else "declined" if diff > 0 else "stable"
            }
            
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "period": {
                "from": previous["timestamp"],
                "to": latest["timestamp"]
            },
            "changes": {
                "total_issues": calculate_change(
                    latest["summary"]["total_issues"],
                    previous["summary"]["total_issues"]
                ),
                "by_level": {
                    level: calculate_change(
                        latest["summary"]["by_level"][level],
                        previous["summary"]["by_level"][level]
                    )
                    for level in ["A", "AA", "AAA"]
                },
                "by_severity": {
                    severity: calculate_change(
                        latest["summary"]["by_severity"][severity],
                        previous["summary"]["by_severity"][severity]
                    )
                    for severity in range(1, 5)
                }
            }
        }