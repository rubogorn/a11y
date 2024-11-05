from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
from pathlib import Path
import json
import asyncio
from dataclasses import asdict
import aiofiles
from src.logging_config import get_logger
from .wcag_analysis import (
    WCAGIssue,
    WCAGAnalysisResult,
    WCAGReportGenerator,
    WCAGComplianceTracker
)

class WCAGIntegrationManager:
    """
    Zentrale Integrationsklasse für WCAG-Analysen und Berichterstattung.
    Koordiniert die Zusammenarbeit zwischen Agenten, Analysewerkzeugen
    und Berichtsgenerierung.
    """

    def __init__(self, output_dir: str = "output/wcag_results"):
        """
        Initialisiert den WCAG Integration Manager
        
        Args:
            output_dir: Verzeichnis für die Ausgabedateien
        """
        # Logging Setup
        self.logger = get_logger('WCAGIntegration', log_dir='output/logs')
        
        # Ausgabeverzeichnis erstellen
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Komponenten initialisieren
        self.compliance_tracker = WCAGComplianceTracker()
        self.current_analysis: Optional[WCAGAnalysisResult] = None
        
        self.logger.info("WCAG Integration Manager initialized")

    async def process_test_results(self, 
                                 normalized_results: List[Dict[str, Any]], 
                                 url: str,
                                 agent_mappings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Verarbeitet die Testergebnisse und erstellt WCAG-Analysen
        
        Args:
            normalized_results: Normalisierte Testergebnisse
            url: URL der getesteten Seite
            agent_mappings: Optionale WCAG-Mappings vom Agent
            
        Returns:
            Verarbeitete WCAG-Analyseergebnisse
        """
        try:
            self.logger.info(f"Starting WCAG analysis for {url}")
            
            # Neue Analyse erstellen
            self.current_analysis = WCAGAnalysisResult(url)
            
            # Ergebnisse verarbeiten
            for result in normalized_results:
                issue = await self._create_wcag_issue(result, agent_mappings)
                if issue:
                    self.current_analysis.add_issue(issue)
                    
            # Empfehlungen vom Agent integrieren wenn vorhanden
            if agent_mappings and "recommendations" in agent_mappings:
                for criterion, steps in agent_mappings["recommendations"].items():
                    self.current_analysis.add_recommendation(criterion, steps)
                    
            # Report generieren
            report_gen = WCAGReportGenerator(self.current_analysis)
            detailed_report = report_gen.generate_detailed_report()
            
            # Analyse zur Compliance-Historie hinzufügen
            self.compliance_tracker.add_result(self.current_analysis)
            
            # Trend-Analyse hinzufügen wenn verfügbar
            trend_analysis = self.compliance_tracker.get_trend_analysis()
            if trend_analysis.get("status") != "insufficient_data":
                detailed_report["trend_analysis"] = trend_analysis
                
            # Ergebnisse speichern
            await self._save_results(detailed_report)
            
            self.logger.info("WCAG analysis completed successfully")
            return detailed_report
            
        except Exception as e:
            error_msg = f"Error processing WCAG test results: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _create_wcag_issue(self, 
                                result: Dict[str, Any], 
                                agent_mappings: Optional[Dict[str, Any]]) -> Optional[WCAGIssue]:
        """
        Erstellt ein WCAG-Issue aus einem Testergebnis
        
        Args:
            result: Einzelnes Testergebnis
            agent_mappings: WCAG-Mappings vom Agent
            
        Returns:
            WCAGIssue oder None bei Fehlern
        """
        try:
            # WCAG-Mapping vom Agent verwenden wenn vorhanden
            wcag_info = None
            if agent_mappings and "mappings" in agent_mappings:
                result_id = result.get("id") or result.get("message")
                wcag_info = agent_mappings["mappings"].get(result_id, {})
            
            return WCAGIssue(
                description=result.get("message", "No description provided"),
                criterion_id=wcag_info.get("criterion_id") if wcag_info else result.get("code", "unknown"),
                level=wcag_info.get("level", "A") if wcag_info else "A",
                severity=result.get("level", 3),
                tools=result.get("tools", []),
                context=result.get("context"),
                selector=result.get("selector"),
                remediation_steps=wcag_info.get("remediation_steps") if wcag_info else None
            )
            
        except Exception as e:
            self.logger.error(f"Error creating WCAG issue: {str(e)}")
            return None

    async def _save_results(self, results: Dict[str, Any]) -> None:
        """
        Speichert die Analyseergebnisse
        
        Args:
            results: Zu speichernde Ergebnisse
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Detaillierte Ergebnisse speichern
            detailed_file = self.output_dir / f"wcag_analysis_{timestamp}.json"
            async with aiofiles.open(detailed_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(results, indent=2, ensure_ascii=False))
            
            # Zusammenfassung speichern
            if self.current_analysis:
                summary_file = self.output_dir / f"wcag_summary_{timestamp}.json"
                summary = self.current_analysis.to_dict()
                async with aiofiles.open(summary_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(summary, indent=2, ensure_ascii=False))
                    
            self.logger.info(f"Results saved to {self.output_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            raise

    async def generate_status_report(self) -> Dict[str, Any]:
        """
        Generiert einen Statusbericht über alle WCAG-Analysen
        
        Returns:
            Statusbericht mit Trends und Statistiken
        """
        try:
            trend_analysis = self.compliance_tracker.get_trend_analysis()
            
            status_report = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_analyses": len(self.compliance_tracker.history),
                "latest_analysis": None,
                "trends": trend_analysis if trend_analysis.get("status") != "insufficient_data" else {},
                "overall_statistics": await self._calculate_overall_statistics()
            }
            
            # Aktuelle Analyse hinzufügen wenn vorhanden
            if self.current_analysis:
                status_report["latest_analysis"] = {
                    "url": self.current_analysis.url,
                    "timestamp": self.current_analysis.timestamp,
                    "summary": self.current_analysis.summary
                }
                
            return status_report
            
        except Exception as e:
            self.logger.error(f"Error generating status report: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _calculate_overall_statistics(self) -> Dict[str, Any]:
        """
        Berechnet Gesamtstatistiken über alle Analysen
        
        Returns:
            Gesamtstatistiken
        """
        try:
            total_issues = 0
            level_counts = {"A": 0, "AA": 0, "AAA": 0}
            severity_counts = {1: 0, 2: 0, 3: 0, 4: 0}
            
            for entry in self.compliance_tracker.history:
                summary = entry["summary"]
                total_issues += summary["total_issues"]
                
                # Level-Statistiken
                for level, count in summary["by_level"].items():
                    level_counts[level] += count
                    
                # Schweregrad-Statistiken
                for severity, count in summary["by_severity"].items():
                    severity_counts[severity] += count
                    
            return {
                "total_issues_found": total_issues,
                "average_issues_per_analysis": round(
                    total_issues / len(self.compliance_tracker.history)
                    if self.compliance_tracker.history else 0,
                    2
                ),
                "issues_by_level": level_counts,
                "issues_by_severity": severity_counts
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating overall statistics: {str(e)}")
            return {}