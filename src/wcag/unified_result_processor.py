# src/wcag/unified_result_processor.py

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from pathlib import Path
import json

import aiofiles

class WCAGLevel(Enum):
    A = "A"
    AA = "AA"
    AAA = "AAA"

class IssueSeverity(Enum):
    CRITICAL = 1
    SERIOUS = 2
    MODERATE = 3
    MINOR = 4

@dataclass
class WCAGReference:
    """WCAG-Kriterium Referenz"""
    criterion_id: str
    level: WCAGLevel
    description: str
    url: Optional[str] = None
    techniques: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)

@dataclass
class AccessibilityIssue:
    """Einheitliches Format für Accessibility-Issues"""
    description: str
    type: str
    severity: IssueSeverity
    wcag_refs: List[WCAGReference]
    tools: List[str]
    context: Optional[str] = None
    selector: Optional[str] = None
    code: Optional[str] = None
    remediation_steps: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class UnifiedResultProcessor:
    """
    Konsolidierte Klasse für die Verarbeitung von Accessibility-Testergebnissen.
    Vereint die Funktionalitäten von StandardizedResult und WCAGAnalysisResult.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialisiert den UnifiedResultProcessor
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.issues: List[AccessibilityIssue] = []
        self.summary: Dict[str, Any] = self._create_empty_summary()
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self._covered_criteria: Set[str] = set()

    def _create_empty_summary(self) -> Dict[str, Any]:
        """Erstellt eine leere Zusammenfassungsstruktur"""
        return {
            "total_issues": 0,
            "by_level": {level.name: 0 for level in WCAGLevel},
            "by_severity": {severity.value: 0 for severity in IssueSeverity},
            "by_tool": {},
            "by_criterion": {},
            "by_principle": {},
            "total_criteria_covered": 0
        }

    def add_issue(self, raw_issue: Dict[str, Any]) -> None:
        """
        Fügt ein neues Issue hinzu und aktualisiert die Statistiken
        
        Args:
            raw_issue: Rohdaten des Issues
        """
        try:
            # Normalisiere und validiere das Issue
            processed_issue = self._process_raw_issue(raw_issue)
            
            # Füge das Issue zur Liste hinzu
            self.issues.append(processed_issue)
            
            # Aktualisiere Statistiken
            self._update_statistics(processed_issue)
            
            self.logger.debug(f"Successfully added issue: {processed_issue.description[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Error adding issue: {str(e)}")

    def _process_raw_issue(self, raw_issue: Dict[str, Any]) -> AccessibilityIssue:
        """
        Verarbeitet ein Roh-Issue in das standardisierte Format
        
        Args:
            raw_issue: Rohdaten des Issues
            
        Returns:
            Standardisiertes AccessibilityIssue
        """
        # Extrahiere WCAG-Referenzen
        wcag_refs = []
        for ref in raw_issue.get("wcag", []):
            if isinstance(ref, dict):
                wcag_refs.append(WCAGReference(
                    criterion_id=ref.get("id", "unknown"),
                    level=WCAGLevel[ref.get("level", "A")],
                    description=ref.get("description", ""),
                    techniques=ref.get("techniques", []),
                    failures=ref.get("failures", [])
                ))
            elif isinstance(ref, str):
                wcag_refs.append(WCAGReference(
                    criterion_id=ref,
                    level=WCAGLevel.A,
                    description=""
                ))

        # Erstelle standardisiertes Issue
        return AccessibilityIssue(
            description=raw_issue.get("message", raw_issue.get("description", "")),
            type=raw_issue.get("type", "unknown"),
            severity=self._normalize_severity(raw_issue.get("severity", 3)),
            wcag_refs=wcag_refs,
            tools=[raw_issue.get("tool", "unknown")],
            context=raw_issue.get("context"),
            selector=raw_issue.get("selector"),
            code=raw_issue.get("code"),
            remediation_steps=raw_issue.get("remediation_steps", [])
        )

    def _normalize_severity(self, severity: Any) -> IssueSeverity:
        """
        Normalisiert verschiedene Severity-Formate
        
        Args:
            severity: Roher Severity-Wert
            
        Returns:
            Normalisierter IssueSeverity-Wert
        """
        if isinstance(severity, IssueSeverity):
            return severity
            
        if isinstance(severity, int) and 1 <= severity <= 4:
            return IssueSeverity(severity)
            
        if isinstance(severity, str):
            severity_map = {
                "critical": IssueSeverity.CRITICAL,
                "serious": IssueSeverity.SERIOUS,
                "moderate": IssueSeverity.MODERATE,
                "minor": IssueSeverity.MINOR
            }
            return severity_map.get(severity.lower(), IssueSeverity.MODERATE)
            
        return IssueSeverity.MODERATE

    def _update_statistics(self, issue: AccessibilityIssue) -> None:
        """
        Aktualisiert die Zusammenfassungsstatistiken
        
        Args:
            issue: Verarbeitetes AccessibilityIssue
        """
        # Aktualisiere Gesamtzahl
        self.summary["total_issues"] += 1
        
        # Zähle nach WCAG-Level
        for ref in issue.wcag_refs:
            self.summary["by_level"][ref.level.name] += 1
            
            # Tracke das Kriterium
            if ref.criterion_id not in self._covered_criteria:
                self._covered_criteria.add(ref.criterion_id)
                self.summary["total_criteria_covered"] += 1
            
            # Gruppiere nach Prinzip (erstes Zeichen der Criterion ID)
            principle = ref.criterion_id[0]
            if principle not in self.summary["by_principle"]:
                self.summary["by_principle"][principle] = {
                    "count": 0,
                    "criteria": set()
                }
            self.summary["by_principle"][principle]["count"] += 1
            self.summary["by_principle"][principle]["criteria"].add(ref.criterion_id)
        
        # Zähle nach Severity
        self.summary["by_severity"][issue.severity.value] += 1
        
        # Zähle nach Tool
        for tool in issue.tools:
            if tool not in self.summary["by_tool"]:
                self.summary["by_tool"][tool] = 0
            self.summary["by_tool"][tool] += 1

    def get_issues(self, severity: Optional[IssueSeverity] = None, 
                  level: Optional[WCAGLevel] = None) -> List[AccessibilityIssue]:
        """
        Gibt gefilterte Issues zurück
        
        Args:
            severity: Optionaler Severity-Filter
            level: Optionaler WCAG-Level-Filter
            
        Returns:
            Gefilterte Liste von Issues
        """
        filtered_issues = self.issues

        if severity:
            filtered_issues = [i for i in filtered_issues if i.severity == severity]

        if level:
            filtered_issues = [
                i for i in filtered_issues 
                if any(ref.level == level for ref in i.wcag_refs)
            ]

        return filtered_issues

    def get_summary(self) -> Dict[str, Any]:
        """
        Gibt eine aktuelle Zusammenfassung zurück
        
        Returns:
            Dictionary mit Zusammenfassungsstatistiken
        """
        return {
            **self.summary,
            "timestamp": self.timestamp,
            "covered_criteria": sorted(list(self._covered_criteria))
        }

    async def save_results(self, output_dir: Path) -> None:
        """
        Speichert die Ergebnisse in Dateien
        
        Args:
            output_dir: Ausgabeverzeichnis
        """
        try:
            # Erstelle Ausgabeverzeichnis
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Speichere detaillierte Ergebnisse
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Speichere Issues
            issues_file = output_dir / f"accessibility_issues_{timestamp}.json"
            issues_data = [self._issue_to_dict(issue) for issue in self.issues]
            
            async with aiofiles.open(issues_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(issues_data, indent=2))
            
            # Speichere Zusammenfassung
            summary_file = output_dir / f"analysis_summary_{timestamp}.json"
            async with aiofiles.open(summary_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.get_summary(), indent=2))
                
            self.logger.info(f"Results saved to {output_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            raise

    def _issue_to_dict(self, issue: AccessibilityIssue) -> Dict[str, Any]:
        """
        Konvertiert ein Issue in ein serialisierbares Dictionary
        
        Args:
            issue: Zu konvertierendes Issue
            
        Returns:
            Serialisierbares Dictionary
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

    def clear(self) -> None:
        """Setzt alle Werte zurück"""
        self.issues.clear()
        self._covered_criteria.clear()
        self.summary = self._create_empty_summary()
        self.timestamp = datetime.now(timezone.utc).isoformat()