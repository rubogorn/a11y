# src/wcag/analyzers/base_analyzer.py

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import logging
from pathlib import Path
import subprocess
import json
from abc import ABC, abstractmethod
from src.logging_config import get_logger

class BaseToolAnalyzer(ABC):
    """Basisklasse für WCAG-Test-Tool-Integration"""
    
    def __init__(self, results_path: Path, logger: Optional[logging.Logger] = None):
        """
        Initialisiert den Tool Analyzer
        
        Args:
            results_path: Pfad für Ergebnisse
            logger: Optional logger instance
        """
        self.results_path = results_path
        self.logger = logger or get_logger(self.__class__.__name__)
        self.tool_name = self.__class__.__name__.replace('Analyzer', '').lower()
        
    @abstractmethod
    async def setup(self) -> bool:
        """
        Richtet das Tool ein und prüft Verfügbarkeit
        
        Returns:
            True wenn Setup erfolgreich, sonst False
        """
        pass
        
    @abstractmethod
    async def analyze(self, url: str) -> Dict[str, Any]:
        """
        Führt die Analyse durch
        
        Args:
            url: Zu testende URL
            
        Returns:
            Analyseergebnisse
        """
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """Bereinigt verwendete Ressourcen"""
        pass

    async def run_command(self, cmd: List[str], timeout: int = 60) -> Tuple[int, str, str]:
        """Führt einen Kommandozeilen-Befehl aus"""
        print(f"rubrub: Running command: {' '.join(cmd)}")  # Debug print
        self.logger.debug(f"Running command: {' '.join(cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
                return process.returncode, stdout.decode(), stderr.decode()
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError(f"Command timed out after {timeout} seconds")
                
        except Exception as e:
            self.logger.error(f"Error running command: {str(e)}")
            raise
            
    def create_result(self, 
                     status: str,
                     url: str,
                     data: Optional[Dict[str, Any]] = None,
                     error: Optional[str] = None) -> Dict[str, Any]:
        """
        Erstellt ein standardisiertes Ergebnis
        
        Args:
            status: Status des Tests
            url: Getestete URL
            data: Optionale Ergebnisdaten
            error: Optionale Fehlermeldung
            
        Returns:
            Standardisiertes Ergebnisformat
        """
        result = {
            "status": status,
            "tool": self.tool_name,
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if data is not None:
            result["results"] = data
            
        if error is not None:
            result["error"] = str(error)
            
        return result
    
    async def save_results(self, results: Dict[str, Any]) -> None:
        """
        Speichert Ergebnisse
        
        Args:
            results: Zu speichernde Ergebnisse
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = self.results_path / f"{self.tool_name}_{timestamp}.json"
            
            # Stelle sicher dass das Verzeichnis existiert
            self.results_path.mkdir(parents=True, exist_ok=True)
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            self.logger.debug(f"Results saved to {results_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            raise