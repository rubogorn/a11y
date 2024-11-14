# src/wcag/wcag_analysis.py

from typing import Dict, List, Any, Optional
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

class WCAGReportGenerator:
    """
    Generiert detaillierte WCAG-Konformitätsberichte basierend auf 
    den Analyseergebnissen
    """

    def __init__(self, analysis_results: Dict[str, Any]):
        """
        Initialisiert den Report Generator
        
        Args:
            analysis_results: Ergebnisse der WCAG-Analyse
        """
        self.analysis = analysis_results
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
                "url": self.analysis.get("url"),
                "scan_date": self.analysis.get("timestamp"),
                "total_issues": len(self.analysis.get("issues", []))
            },
            "compliance_levels": self.analysis.get("summary", {}).get("by_level", {}),
            "severity_breakdown": self.analysis.get("summary", {}).get("by_severity", {}),
            "principles_affected": self.analysis.get("summary", {}).get("by_principle", {})
        }

    def generate_detailed_report(self) -> Dict[str, Any]:
        """Generiert einen detaillierten Bericht mit allen Problemen"""
        issues = self.analysis.get("issues", [])
        
        return {
            "metadata": {
                "url": self.analysis.get("url"),
                "timestamp": self.analysis.get("timestamp"),
                "total_issues": len(issues)
            },
            "issues": [
                {
                    "description": self._format_issue_description(issue),
                    "recommendation": self._format_recommendation(issue),
                    "details": {
                        "criterion": issue.get("wcag_references", [{}])[0].get("criterion_id"),
                        "level": issue.get("wcag_references", [{}])[0].get("level"),
                        "severity": issue.get("severity"),
                        "tools": issue.get("tools", []),
                        "technical": {
                            "context": issue.get("context"),
                            "selector": issue.get("selector")
                        }
                    }
                }
                for issue in issues
            ],
            "recommendations_summary": self.analysis.get("remediation_guidance", {}),
            "statistics": self.generate_summary_report()
        }

    def _format_issue_description(self, issue: Dict[str, Any]) -> str:
        """Formatiert die Problembeschreibung"""
        wcag_ref = issue.get("wcag_references", [{}])[0]
        return self.templates["issue_description"].format(
            criterion_id=wcag_ref.get("criterion_id", "unknown"),
            level=wcag_ref.get("level", "unknown"),
            description=issue.get("description", ""),
            severity=issue.get("severity", 3),
            tools=", ".join(issue.get("tools", [])),
            context=issue.get("context", "N/A"),
            selector=issue.get("selector", "N/A")
        )

    def _format_recommendation(self, issue: Dict[str, Any]) -> str:
        """Formatiert die Empfehlungen"""
        steps = issue.get("remediation_steps", [])
        if not steps:
            return "No specific remediation steps provided."
            
        wcag_ref = issue.get("wcag_references", [{}])[0]
        steps_text = "\n".join(
            f"  {i+1}. {step}" 
            for i, step in enumerate(steps)
        )
        
        return self.templates["recommendation"].format(
            steps=steps_text,
            criterion_id=wcag_ref.get("criterion_id", "unknown"),
            level=wcag_ref.get("level", "unknown")
        )

class WCAGComplianceTracker:
    """
    Verfolgt den WCAG-Konformitätsstatus über mehrere Tests hinweg
    und identifiziert Verbesserungen oder Verschlechterungen
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        
    def add_result(self, result: Dict[str, Any]) -> None:
        """
        Fügt ein neues Testergebnis zur Historie hinzu
        
        Args:
            result: Analyseergebnis
        """
        self.history.append({
            "timestamp": result.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "url": result.get("url"),
            "summary": result.get("summary", {})
        })
        
    def get_trend_analysis(self) -> Dict[str, Any]:
        """
        Analysiert Trends in der WCAG-Konformität
        
        Returns:
            Trend-Analyse der WCAG-Konformität
        """
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
                    latest["summary"].get("total_issues", 0),
                    previous["summary"].get("total_issues", 0)
                ),
                "by_level": {
                    level: calculate_change(
                        latest["summary"].get("by_level", {}).get(level, 0),
                        previous["summary"].get("by_level", {}).get(level, 0)
                    )
                    for level in ["A", "AA", "AAA"]
                },
                "by_severity": {
                    severity: calculate_change(
                        latest["summary"].get("by_severity", {}).get(str(severity), 0),
                        previous["summary"].get("by_severity", {}).get(str(severity), 0)
                    )
                    for severity in range(1, 5)
                }
            }
        }