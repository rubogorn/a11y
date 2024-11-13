# src/wcag/analyzers/pa11y_analyzer.py

import json
from typing import Dict, Any, Optional
import shutil
from datetime import datetime, timezone
import re
from .base_analyzer import BaseToolAnalyzer

class Pa11yAnalyzer(BaseToolAnalyzer):
    """Analyzer für Pa11y Accessibility Tests"""

    def __init__(self, results_path, logger=None):
        """
        Initialisiert den Pa11y Analyzer
        
        Args:
            results_path: Pfad für Ergebnisse
            logger: Optional logger instance
        """
        super().__init__(results_path, logger)
        self.name = "pa11y"
        print("rubrub: Pa11yAnalyzer initialized")
        self.logger.info("Pa11yAnalyzer initialized")
        self.args_schema = {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "URL to analyze"
                }
            },
            "required": ["url"]
        }

    async def setup(self) -> bool:
        """
        Prüft ob Pa11y installiert und verfügbar ist
        
        Returns:
            True wenn Pa11y verfügbar ist, sonst False
        """

        print("rubrub: Pa11y setup started")
        self.logger.info("Starting Pa11y setup")

        try:
            # Suche Pa11y in PATH
            pa11y_path = shutil.which('pa11y')
            if not pa11y_path:
                self.logger.error("Pa11y is not installed. Please install it using: npm install -g pa11y")
                return False
                
            # Prüfe Version
            returncode, stdout, stderr = await self.run_command(['pa11y', '--version'])
            if returncode != 0:
                self.logger.error(f"Error checking Pa11y version: {stderr}")
                return False
                
            self.logger.info(f"Pa11y version {stdout.strip()} found at {pa11y_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up Pa11y: {str(e)}")
            return False

    async def analyze(self, url: str) -> Dict[str, Any]:
        """
        Führt Pa11y Tests für die angegebene URL aus
        
        Args:
            url: Zu testende URL
            
        Returns:
            Pa11y Testergebnisse
        """

        print(f"rubrub: Pa11y analyze started for URL: {url}")
        self.logger.info(f"Starting Pa11y analysis for URL: {url}")
        
        try:
            # Prüfe Setup
            if not await self.setup():
                self.logger.error("Setup failed")
                return self.create_result(
                    "error",
                    url,
                    error="Pa11y is not available"
                )
            
            # Führe Pa11y aus mit erweiterten Optionen
            cmd = [
                'pa11y',
                '--reporter', 'json',
                '--standard', 'WCAG2AA',
                '--include-notices',
                '--include-warnings',
                '--timeout', '60000',  # 60 Sekunden Timeout
                '--wait', '1000',      # 1 Sekunde warten nach Laden
                '--ignore', 'notice',  # Ignoriere nur notices
                '--viewport', '1280x720',
                url
            ]
            
            self.logger.debug(f"Executing Pa11y command: {' '.join(cmd)}")
            
            returncode, stdout, stderr = await self.run_command(cmd, timeout=120)
            self.logger.debug(f"Pa11y return code: {returncode}")
            self.logger.debug(f"Pa11y stderr: {stderr}")
            
            # Pa11y gibt 2 zurück wenn es Probleme findet (das ist normal)
            if returncode == 2 or returncode == 0:
                try:
                    raw_results = json.loads(stdout)
                    
                    # Transformiere die Ergebnisse
                    processed_results = self._process_pa11y_results(raw_results, url)
                    
                    # Speichere die Rohergebnisse
                    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                    await self.save_results(
                        raw_results,
                        f"pa11y_raw_{timestamp}.json"
                    )
                    
                    return self.create_result(
                        "success",
                        url,
                        data=processed_results
                    )
                    
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse Pa11y output: {str(e)}"
                    self.logger.error(error_msg)
                    self.logger.debug(f"Raw output was: {stdout[:500]}...")
                    return self.create_result(
                        "error",
                        url,
                        error=error_msg
                    )
            
            # Wenn returncode nicht 0 oder 2 ist, ist es ein echter Fehler
            error_msg = f"Pa11y failed with code {returncode}: {stderr}"
            self.logger.error(error_msg)
            return self.create_result(
                "error",
                url,
                error=error_msg
            )
            
        except Exception as e:
            error_msg = f"Error running Pa11y: {str(e)}"
            self.logger.error(error_msg)
            return self.create_result(
                "error",
                url,
                error=error_msg
            )

    def _process_pa11y_results(self, raw_results: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Verarbeitet die Pa11y Rohergebnisse in ein standardisiertes Format
        
        Args:
            raw_results: Rohergebnisse von Pa11y
            url: Getestete URL
            
        Returns:
            Verarbeitete Ergebnisse
        """
        processed = {
            "url": url,
            "tool": "pa11y",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "issues": [],
            "statistics": {
                "total": 0,
                "by_type": {},
                "by_impact": {}
            }
        }
        
        if not isinstance(raw_results, list):
            self.logger.warning(f"Unexpected Pa11y results format: {type(raw_results)}")
            return processed
            
        for issue in raw_results:
            try:
                # Extrahiere WCAG Kriterium
                wcag_refs = []
                if "code" in issue:
                    wcag_pattern = r"WCAG\s*(\d+\.\d+\.\d+)"
                    matches = re.findall(wcag_pattern, issue["code"])
                    wcag_refs = [f"WCAG{m}" for m in matches]
                
                # Bestimme Severity
                severity = self._map_severity(issue.get("type", "unknown"))
                
                # Baue standardisiertes Issue
                processed_issue = {
                    "type": issue.get("type", "unknown"),
                    "code": issue.get("code", ""),
                    "message": issue.get("message", ""),
                    "context": issue.get("context", ""),
                    "selector": issue.get("selector", ""),
                    "severity": severity,
                    "wcag": wcag_refs,
                    "line": issue.get("position", {}).get("lineNumber"),
                    "column": issue.get("position", {}).get("columnNumber"),
                    "impact": self._determine_impact(issue)
                }
                
                processed["issues"].append(processed_issue)
                
                # Aktualisiere Statistiken
                processed["statistics"]["total"] += 1
                
                issue_type = issue.get("type", "unknown")
                processed["statistics"]["by_type"][issue_type] = \
                    processed["statistics"]["by_type"].get(issue_type, 0) + 1
                
                processed["statistics"]["by_impact"][processed_issue["impact"]] = \
                    processed["statistics"]["by_impact"].get(processed_issue["impact"], 0) + 1
                    
            except Exception as e:
                self.logger.error(f"Error processing Pa11y issue: {str(e)}")
                continue
        
        return processed

    def _map_severity(self, pa11y_type: str) -> int:
        """
        Mappt Pa11y Typen auf einheitliche Severity Levels
        
        Args:
            pa11y_type: Pa11y Issue Typ
            
        Returns:
            Severity Level (1-4)
        """
        severity_map = {
            "error": 1,      # Critical
            "warning": 2,    # Serious
            "notice": 3      # Moderate
        }
        return severity_map.get(pa11y_type.lower(), 3)

    def _determine_impact(self, issue: Dict[str, Any]) -> str:
        """
        Bestimmt den Impact Level eines Issues
        
        Args:
            issue: Pa11y Issue
            
        Returns:
            Impact Level (critical, serious, moderate, minor)
        """
        # Bestimme Impact basierend auf Type und Message
        if issue.get("type") == "error":
            if any(kw in issue.get("message", "").lower() for kw in 
                ["critical", "broken", "invalid", "missing required"]):
                return "critical"
            return "serious"
            
        elif issue.get("type") == "warning":
            return "moderate"
            
        return "minor"

    async def cleanup(self) -> None:
        """Keine spezielle Bereinigung erforderlich"""
        pass