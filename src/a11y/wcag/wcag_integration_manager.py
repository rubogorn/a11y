# src/wcag/wcag_integration_manager.py

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import logging
from pathlib import Path
import json
import asyncio
import aiofiles
from ..logging_config import get_logger
from .unified_result_processor import (
    UnifiedResultProcessor,
    AccessibilityIssue,
    WCAGReference,
    WCAGLevel,
    IssueSeverity
)
from .wcag_mapping_agent import WCAGMappingAgent
from .wcag_analyzers import HTMLAnalyzer, Pa11yAnalyzer, AxeAnalyzer, LighthouseAnalyzer

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
        self.wcag_agent = WCAGMappingAgent()
        self.result_processor = UnifiedResultProcessor(logger=self.logger)
        
        self.logger.info("WCAG Integration Manager initialized")

    async def analyze_url(self, url: str) -> Dict[str, Any]:
        """
        Führt eine vollständige WCAG-Analyse für eine URL durch
        
        Args:
            url: Zu analysierende URL
            
        Returns:
            Analyseergebnisse
        """
        try:
            self.logger.info(f"Starting analysis for URL: {url}")
            
            # Browser für JavaScript-basierte Tests initialisieren
            browser = await self._setup_browser()
            try:
                # Analyzer initialisieren
                analyzers = {
                    "html": HTMLAnalyzer(self.output_dir, self.logger),
                    "pa11y": Pa11yAnalyzer(self.output_dir, self.logger),
                    "axe": AxeAnalyzer(self.output_dir, self.logger, browser),
                    "lighthouse": LighthouseAnalyzer(self.output_dir, self.logger, browser)
                }

                # Alle Tests ausführen
                raw_results = await self._run_all_analyzers(analyzers, url)
                
                # Ergebnisse normalisieren und WCAG-Mapping durchführen
                processed_results = await self.process_results(raw_results, url)
                
                return processed_results
                
            finally:
                await self._cleanup_browser(browser)
                
        except Exception as e:
            error_msg = f"Error analyzing URL {url}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _run_all_analyzers(self, 
                                analyzers: Dict[str, Union[HTMLAnalyzer, Pa11yAnalyzer, AxeAnalyzer, LighthouseAnalyzer]], 
                                url: str) -> List[Dict[str, Any]]:
        """
        Führt alle Analyzer für eine URL aus
        
        Args:
            analyzers: Dictionary mit Analyzer-Instanzen
            url: Zu analysierende URL
            
        Returns:
            Kombinierte Testergebnisse
        """
        results = []
        for name, analyzer in analyzers.items():
            try:
                self.logger.info(f"Running {name} analyzer...")
                result = await analyzer.analyze(url)
                
                if not result.get("error"):
                    results.extend(self._normalize_analyzer_results(result, name))
                    self.logger.info(f"{name} analysis completed successfully")
                else:
                    self.logger.warning(f"{name} analysis failed: {result.get('error')}")
                    
            except Exception as e:
                self.logger.error(f"Error running {name} analyzer: {str(e)}")
                
        return results

    def _normalize_analyzer_results(self, 
                                  result: Dict[str, Any], 
                                  analyzer_name: str) -> List[Dict[str, Any]]:
        """
        Normalisiert die Ergebnisse eines Analyzers
        
        Args:
            result: Rohergebnisse des Analyzers
            analyzer_name: Name des Analyzers
            
        Returns:
            Normalisierte Ergebnisliste
        """
        normalized = []
        
        # Extrahiere Issues aus den Ergebnissen
        issues = result.get("issues", result.get("results", []))
        if not isinstance(issues, list):
            issues = [issues]
            
        for issue in issues:
            normalized_issue = {
                "message": issue.get("message", issue.get("description", "")),
                "type": issue.get("type", "unknown"),
                "severity": issue.get("severity", 3),
                "tool": analyzer_name,
                "context": issue.get("context"),
                "selector": issue.get("selector"),
                "code": issue.get("code"),
                "wcag": issue.get("wcag", []),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            normalized.append(normalized_issue)
            
        return normalized
    
    async def process_results(self, 
                                 raw_results: List[Dict[str, Any]], 
                                 url: str) -> Dict[str, Any]:
        """
        Verarbeitet und analysiert die Testergebnisse
        
        Args:
            raw_results: Liste der Rohergebnisse
            url: Analysierte URL
            
        Returns:
            Verarbeitete Analyseergebnisse
        """
        try:
            self.logger.info(f"Processing results for {url}")
            
            # WCAG-Mapping für jedes Issue durchführen
            for result in raw_results:
                try:
                    # WCAG-Mapping durch Agent
                    mapped_result = await self.wcag_agent.analyze_accessibility_issue(result)
                    
                    if not mapped_result.get("error"):
                        # Issue zum ResultProcessor hinzufügen
                        self.result_processor.add_issue(mapped_result)
                    else:
                        self.logger.warning(
                            f"WCAG mapping failed for issue: {result.get('message', '')[:50]}..."
                        )
                except Exception as e:
                    self.logger.error(f"Error processing issue: {str(e)}")
            
            # Generiere die finale Analyse
            analysis_result = {
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "issues": [
                    self._prepare_issue_for_output(issue) 
                    for issue in self.result_processor.issues
                ],
                "summary": self.result_processor.get_summary(),
                "remediation_guidance": await self._generate_remediation_guidance()
            }
            
            # Speichere die Ergebnisse
            await self._save_results(analysis_result)
            
            self.logger.info(f"Successfully processed {len(raw_results)} issues")
            return analysis_result
            
        except Exception as e:
            error_msg = f"Error processing results: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _generate_remediation_guidance(self) -> Dict[str, List[str]]:
        """
        Generiert Behebungsempfehlungen für alle Issues
        
        Returns:
            Dictionary mit Empfehlungen pro WCAG-Kriterium
        """
        guidance = {}
        
        for issue in self.result_processor.issues:
            for ref in issue.wcag_refs:
                if ref.criterion_id not in guidance:
                    try:
                        # Generiere Empfehlungen für das Kriterium
                        result = await self.wcag_agent.generate_remediation_guidance({
                            "criterion_id": ref.criterion_id,
                            "level": ref.level.name,
                            "description": ref.description
                        })
                        
                        if not result.get("error"):
                            guidance[ref.criterion_id] = result.get("guidance", [])
                            
                    except Exception as e:
                        self.logger.error(
                            f"Error generating guidance for {ref.criterion_id}: {str(e)}"
                        )
                        
        return guidance

    def _prepare_issue_for_output(self, issue: AccessibilityIssue) -> Dict[str, Any]:
        """
        Bereitet ein Issue für die Ausgabe vor
        
        Args:
            issue: Zu verarbeitendes Issue
            
        Returns:
            Ausgabebereites Issue-Dictionary
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

    async def _save_results(self, results: Dict[str, Any]) -> None:
        """
        Speichert die Analyseergebnisse
        
        Args:
            results: Zu speichernde Ergebnisse
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Hauptergebnisdatei
            results_file = self.output_dir / f"wcag_analysis_{timestamp}.json"
            async with aiofiles.open(results_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(results, indent=2, ensure_ascii=False))
            
            # Separate Zusammenfassungsdatei
            summary_file = self.output_dir / f"analysis_summary_{timestamp}.json"
            async with aiofiles.open(summary_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(results["summary"], indent=2))
            
            # Empfehlungsdatei, wenn vorhanden
            if "remediation_guidance" in results:
                guidance_file = self.output_dir / f"remediation_guidance_{timestamp}.json"
                async with aiofiles.open(guidance_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(results["remediation_guidance"], indent=2))
                    
            self.logger.info(f"Results saved to {self.output_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            raise

    async def _setup_browser(self):
        """Initialisiert den Browser für JavaScript-basierte Tests"""
        try:
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            return browser
        except Exception as e:
            self.logger.error(f"Error setting up browser: {str(e)}")
            raise

    async def _cleanup_browser(self, browser) -> None:
        """
        Bereinigt Browser-Ressourcen
        
        Args:
            browser: Zu bereinigender Browser
        """
        try:
            await browser.close()
            await browser.playwright.stop()
        except Exception as e:
            self.logger.error(f"Error cleaning up browser: {str(e)}")