# src/wcag/analyzers/axe_analyzer.py

import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime, timezone
from playwright.async_api import async_playwright, Browser, Page, Error as PlaywrightError
from .base_analyzer import BaseToolAnalyzer

class AxeAnalyzer(BaseToolAnalyzer):
    """
    Analyzer für Axe Core Accessibility Tests.
    Verwendet Playwright für Browser-Automation und Axe Core für Tests.
    """
    
    def __init__(self, results_path: Path, logger: Optional[logging.Logger] = None):
        """
        Initialisiert den Axe Analyzer
        
        Args:
            results_path: Pfad für Ergebnisse
            logger: Optional logger instance
        """
        super().__init__(results_path, logger)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def setup(self) -> bool:
        """
        Initialisiert Playwright und injiziert Axe Core
        
        Returns:
            True wenn Setup erfolgreich, sonst False
        """
        try:
            # Starte Playwright
            playwright = await async_playwright().start()
            
            # Browser mit spezifischen Optionen starten
            self.browser = await playwright.chromium.launch(
                args=['--no-sandbox', '--disable-setuid-sandbox'],
                headless=True
            )
            
            # Neue Seite mit Desktop-Viewport erstellen
            self.page = await self.browser.new_page(
                viewport={'width': 1280, 'height': 720}
            )
            
            # Axe Core von CDN laden
            await self.page.add_script_tag(
                url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js"
            )
            
            # Warte bis Axe Core verfügbar ist
            await self.page.wait_for_function("window.axe !== undefined")
            
            self.logger.info("Axe Core setup completed successfully")
            return True
            
        except PlaywrightError as e:
            self.logger.error(f"Playwright error during setup: {str(e)}")
            await self.cleanup()
            return False
        except Exception as e:
            self.logger.error(f"Error setting up Axe Core: {str(e)}")
            await self.cleanup()
            return False

    async def analyze(self, url: str) -> Dict[str, Any]:
        """
        Führt Axe Core Tests auf der angegebenen URL aus
        
        Args:
            url: Zu testende URL
            
        Returns:
            Axe Core Testergebnisse
        """
        try:
            # Setup wenn noch nicht geschehen
            if not self.browser or not self.page:
                if not await self.setup():
                    return self.create_result(
                        "error",
                        url,
                        error="Failed to setup Axe Core"
                    )
            
            self.logger.info(f"Starting Axe analysis for URL: {url}")
            
            # Navigiere zur URL mit Timeout und Retry-Logik
            try:
                await self.page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=30000
                )
            except PlaywrightError as e:
                return self.create_result(
                    "error",
                    url,
                    error=f"Failed to load URL: {str(e)}"
                )
                
            # Warte auf vollständiges Laden der Seite
            await self.page.wait_for_load_state("domcontentloaded")
            
            # Führe Axe Tests aus mit spezifischer Konfiguration
            try:
                results = await self.page.evaluate("""() => {
                    return new Promise((resolve) => {
                        axe.run(document, {
                            resultTypes: ['violations', 'incomplete'],
                            runOnly: {
                                type: 'tag',
                                values: [
                                    'wcag2a',
                                    'wcag2aa',
                                    'wcag21a',
                                    'wcag21aa',
                                    'wcag22a',
                                    'wcag22aa',
                                    'best-practice'
                                ]
                            },
                            rules: {
                                'color-contrast': { enabled: true },
                                'frame-tested': { enabled: true },
                                'aria-allowed-attr': { enabled: true },
                                'aria-required-attr': { enabled: true },
                                'aria-required-children': { enabled: true },
                                'aria-required-parent': { enabled: true },
                                'aria-roles': { enabled: true },
                                'aria-valid-attr-value': { enabled: true },
                                'aria-valid-attr': { enabled: true }
                            }
                        }).then(results => resolve(results));
                    });
                }""")
                
                # Verarbeite die Ergebnisse
                processed_results = await self._process_axe_results(results, url)
                
                # Speichere die Ergebnisse
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                results_filename = f"axe_results_{timestamp}.json"
                await self.save_results(processed_results, results_filename)
                
                return self.create_result(
                    "success",
                    url,
                    data=processed_results
                )
                
            except Exception as e:
                return self.create_result(
                    "error",
                    url,
                    error=f"Error running Axe tests: {str(e)}"
                )
                
        except Exception as e:
            error_msg = f"Error in Axe analysis: {str(e)}"
            self.logger.error(error_msg)
            return self.create_result(
                "error",
                url,
                error=error_msg
            )
            
        finally:
            await self.cleanup()

    async def _process_axe_results(self, results: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Verarbeitet die Axe Core Ergebnisse in ein standardisiertes Format
        
        Args:
            results: Rohergebnisse von Axe Core
            url: Getestete URL
            
        Returns:
            Standardisierte Ergebnisse
        """
        processed = {
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "axe-core",
            "issues": [],
            "statistics": {
                "total": 0,
                "by_impact": {},
                "by_tags": {},
                "by_rule": {}
            }
        }
        
        # Verarbeite Violations (Fehler)
        violations = results.get("violations", [])
        for violation in violations:
            impact = violation.get("impact", "minor")
            tags = violation.get("tags", [])
            rule = violation.get("id", "unknown")
            
            # Aktualisiere Statistiken
            processed["statistics"]["by_impact"][impact] = \
                processed["statistics"]["by_impact"].get(impact, 0) + 1
                
            processed["statistics"]["by_rule"][rule] = \
                processed["statistics"]["by_rule"].get(rule, 0) + 1
            
            for tag in tags:
                processed["statistics"]["by_tags"][tag] = \
                    processed["statistics"]["by_tags"].get(tag, 0) + 1
            
            # Verarbeite jedes Problem einzeln
            for node in violation.get("nodes", []):
                issue = {
                    "type": "violation",
                    "impact": impact,
                    "rule": rule,
                    "message": violation.get("help", ""),
                    "description": violation.get("description", ""),
                    "wcag": [
                        tag for tag in tags 
                        if tag.startswith(("wcag2", "wcag21", "wcag22"))
                    ],
                    "selector": node.get("target", []),
                    "html": node.get("html", ""),
                    "help_url": violation.get("helpUrl", ""),
                    "failure_summary": node.get("failureSummary", "")
                }
                processed["issues"].append(issue)
                processed["statistics"]["total"] += 1
        
        # Verarbeite Incomplete (Warnungen)
        incomplete = results.get("incomplete", [])
        for item in incomplete:
            impact = item.get("impact", "minor")
            tags = item.get("tags", [])
            rule = item.get("id", "unknown")
            
            # Aktualisiere Statistiken
            processed["statistics"]["by_impact"][impact] = \
                processed["statistics"]["by_impact"].get(impact, 0) + 1
            
            processed["statistics"]["by_rule"][rule] = \
                processed["statistics"]["by_rule"].get(rule, 0) + 1
                
            for tag in tags:
                processed["statistics"]["by_tags"][tag] = \
                    processed["statistics"]["by_tags"].get(tag, 0) + 1
            
            # Verarbeite jede Warnung einzeln
            for node in item.get("nodes", []):
                issue = {
                    "type": "needs-review",
                    "impact": impact,
                    "rule": rule,
                    "message": item.get("help", ""),
                    "description": item.get("description", ""),
                    "wcag": [
                        tag for tag in tags 
                        if tag.startswith(("wcag2", "wcag21", "wcag22"))
                    ],
                    "selector": node.get("target", []),
                    "html": node.get("html", ""),
                    "help_url": item.get("helpUrl", ""),
                    "failure_summary": node.get("failureSummary", "")
                }
                processed["issues"].append(issue)
                processed["statistics"]["total"] += 1
        
        return processed

    async def cleanup(self) -> None:
        """Bereinigt Browser-Ressourcen"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
                
            if self.browser:
                await self.browser.close()
                self.browser = None
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")