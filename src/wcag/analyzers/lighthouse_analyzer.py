# src/wcag/analyzers/lighthouse_analyzer.py

import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import shutil
import os
import logging
from .base_analyzer import BaseToolAnalyzer

class LighthouseAnalyzer(BaseToolAnalyzer):
    """
    Analyzer für Lighthouse Accessibility Tests.
    Steuert Lighthouse über die Kommandozeilen-Schnittstelle.
    """
    
    def __init__(self, results_path: Path, logger: Optional[logging.Logger] = None):
        """
        Initialisiert den Lighthouse Analyzer
        
        Args:
            results_path: Pfad für Ergebnisse
            logger: Optional logger instance
        """
        super().__init__(results_path, logger)
        
        # Chrome Flags für Headless-Modus und Sicherheit
        self.chrome_flags = [
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-dev-shm-usage'
        ]
        
    async def setup(self) -> bool:
        """
        Prüft ob Lighthouse und Chrome installiert sind
        
        Returns:
            True wenn Setup erfolgreich, sonst False
        """
        try:
            # Prüfe ob Lighthouse installiert ist
            lighthouse_path = shutil.which('lighthouse')
            if not lighthouse_path:
                self.logger.error("Lighthouse is not installed")
                return False
                
            # Prüfe Version
            returncode, stdout, stderr = await self.run_command(['lighthouse', '--version'])
            if returncode != 0:
                self.logger.error(f"Error checking Lighthouse version: {stderr}")
                return False
                
            # Prüfe ob Chrome verfügbar ist
            chrome_path = shutil.which('google-chrome')
            if not chrome_path:
                chrome_path = shutil.which('chromium')
                
            if not chrome_path:
                self.logger.error("Neither Chrome nor Chromium found")
                return False
                
            self.logger.info(f"Lighthouse found at {lighthouse_path} with Chrome at {chrome_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up Lighthouse: {str(e)}")
            return False

    async def analyze(self, url: str) -> Dict[str, Any]:
        """
        Führt Lighthouse Tests aus
        
        Args:
            url: Zu testende URL
            
        Returns:
            Lighthouse Testergebnisse
        """
        try:
            # Prüfe Setup
            if not await self.setup():
                return self.create_result(
                    "error",
                    url,
                    error="Lighthouse is not available"
                )
            
            # Temporäres Verzeichnis für Ergebnisse
            output_path = self.results_path / f"lighthouse_{url.replace('://', '_').replace('/', '_')}.json"
            
            # Lighthouse Kommando vorbereiten
            cmd = [
                'lighthouse',
                url,
                '--output=json',
                f'--output-path={output_path}',
                '--quiet',
                '--only-categories=accessibility',
                f'--chrome-flags="{" ".join(self.chrome_flags)}"',
                '--no-enable-error-reporting',
                '--disable-full-page-screenshot'
            ]
            
            try:
                # Führe Lighthouse aus
                returncode, stdout, stderr = await self.run_command(cmd, timeout=300)  # 5 Minuten Timeout
                
                if returncode != 0:
                    return self.create_result(
                        "error",
                        url,
                        error=f"Lighthouse failed with code {returncode}: {stderr}"
                    )
                    
                # Lade und verarbeite Ergebnisse
                if output_path.exists():
                    with open(output_path, 'r', encoding='utf-8') as f:
                        raw_results = json.load(f)
                        
                    # Verarbeite die Ergebnisse
                    processed_results = self._process_lighthouse_results(raw_results)
                    await self.save_results(processed_results)
                    
                    return self.create_result(
                        "success",
                        url,
                        data=processed_results
                    )
                else:
                    return self.create_result(
                        "error",
                        url,
                        error="Lighthouse did not generate results file"
                    )
                    
            finally:
                # Bereinige temporäre Dateien
                if output_path.exists():
                    try:
                        os.remove(output_path)
                    except Exception as e:
                        self.logger.warning(f"Failed to remove temp file {output_path}: {e}")
                
        except Exception as e:
            error_msg = f"Error running Lighthouse: {str(e)}"
            self.logger.error(error_msg)
            return self.create_result(
                "error",
                url,
                error=error_msg
            )

    def _process_lighthouse_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet die Lighthouse Ergebnisse in ein standardisiertes Format
        
        Args:
            results: Rohergebnisse von Lighthouse
            
        Returns:
            Standardisierte Ergebnisse
        """
        processed = {
            "score": None,
            "issues": [],
            "statistics": {
                "total": 0,
                "by_impact": {},
                "by_category": {}
            }
        }
        
        try:
            # Extrahiere Accessibility Score
            categories = results.get("categories", {})
            accessibility = categories.get("accessibility", {})
            processed["score"] = accessibility.get("score", 0) * 100  # Konvertiere zu Prozent
            
            # Verarbeite Audits
            audits = results.get("audits", {})
            for audit_id, audit in audits.items():
                # Überspringe nicht-accessibility Audits
                if not audit.get("group") == "a11y":
                    continue
                    
                score = audit.get("score")
                if score is not None and score >= 1:
                    continue  # Überspringe bestandene Tests
                
                # Bestimme Impact Level
                impact = self._determine_impact_level(
                    score,
                    audit.get("details", {}).get("type", ""),
                    audit.get("errorCount", 0)
                )
                
                # Zähle nach Impact
                processed["statistics"]["by_impact"][impact] = \
                    processed["statistics"]["by_impact"].get(impact, 0) + 1
                    
                # Zähle nach Kategorie
                category = audit.get("group", "other")
                processed["statistics"]["by_category"][category] = \
                    processed["statistics"]["by_category"].get(category, 0) + 1
                
                # Erstelle Issue
                issue = {
                    "id": audit_id,
                    "type": "error" if score == 0 else "warning",
                    "impact": impact,
                    "message": audit.get("title", ""),
                    "description": audit.get("description", ""),
                    "score": score,
                    "details": self._process_audit_details(audit.get("details", {})),
                    "failure_points": audit.get("warnings", [])
                }
                
                processed["issues"].append(issue)
                processed["statistics"]["total"] += 1
        
        except Exception as e:
            self.logger.error(f"Error processing Lighthouse results: {str(e)}")
            
        return processed

    def _determine_impact_level(self, score: Optional[float], detail_type: str, error_count: int) -> str:
        """
        Bestimmt den Impact Level basierend auf verschiedenen Faktoren
        
        Args:
            score: Lighthouse Score
            detail_type: Art des Details
            error_count: Anzahl der Fehler
            
        Returns:
            Impact Level (critical, serious, moderate, minor)
        """
        if score == 0:
            if error_count > 5 or detail_type in ["table", "list"]:
                return "critical"
            return "serious"
        elif score is None or score < 0.5:
            return "serious"
        elif score < 0.9:
            return "moderate"
        return "minor"

    def _process_audit_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet die Details eines Lighthouse Audits
        
        Args:
            details: Audit Details von Lighthouse
            
        Returns:
            Verarbeitete Details
        """
        processed_details = {}
        
        # Extrahiere relevante Informationen basierend auf dem Typ
        if details.get("type") == "table":
            processed_details["items"] = details.get("items", [])
            
        elif details.get("type") == "list":
            processed_details["items"] = details.get("items", [])
            
        # Füge Debug-Daten hinzu wenn vorhanden
        if "debugData" in details:
            processed_details["debug"] = details["debugData"]
            
        return processed_details

    async def cleanup(self) -> None:
        """
        Bereinigt temporäre Dateien und Ressourcen
        In diesem Fall keine spezielle Aktion nötig
        """
        pass