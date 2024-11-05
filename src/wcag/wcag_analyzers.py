from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from bs4 import BeautifulSoup
import aiohttp
from datetime import datetime, timezone
import json
import asyncio
from .wcag_analysis import WCAGIssue, WCAGAnalysisResult

class BaseAnalyzer:
    """Basisklasse für alle WCAG Analyzer"""
    
    def __init__(self, results_path: Path, logger: logging.Logger):
        self.results_path = results_path
        self.logger = logger
        self.tool_name = self.__class__.__name__.replace('Analyzer', '').lower()
        
    async def analyze(self, url: str) -> Dict[str, Any]:
        """
        Abstrakte Methode für die Analyse
        
        Args:
            url: Zu testende URL
            
        Returns:
            Analyseergebnisse
        """
        raise NotImplementedError("Subclasses must implement analyze method")
        
    def _create_error_result(self, error: str, url: str) -> Dict[str, Any]:
        """Erstellt ein standardisiertes Fehlerergebnis"""
        return {
            "status": "error",
            "error": str(error),
            "tool": self.tool_name,
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

class HTMLAnalyzer(BaseAnalyzer):
    """Analyzer für HTML Struktur und ARIA Verwendung"""
    
    async def analyze(self, url: str) -> Dict[str, Any]:
        """Analysiert HTML-Struktur und Zugänglichkeitsmerkmale"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return self._create_error_result(
                            f"Failed to fetch URL: {response.status}", url
                        )
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Strukturanalyse durchführen
                    analysis = self._analyze_structure(soup)
                    
                    # Probleme identifizieren
                    issues = self._check_for_issues(soup, analysis)
                    
                    return {
                        "status": "success",
                        "tool": "html",
                        "url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "analysis": analysis,
                        "issues": issues
                    }
                    
        except Exception as e:
            return self._create_error_result(str(e), url)

    def _analyze_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analysiert HTML-Strukturelemente"""
        return {
            "doctype": bool(soup.find('doctype')),
            "lang_attribute": bool(soup.find('html', attrs={'lang': True})),
            "head_elements": {
                "title": bool(soup.find('title')),
                "meta_viewport": bool(soup.find('meta', attrs={'name': 'viewport'})),
                "meta_charset": bool(soup.find('meta', attrs={'charset': True}))
            },
            "headings": {
                f"h{i}": len(soup.find_all(f'h{i}')) 
                for i in range(1, 7)
            },
            "landmarks": {
                "header": len(soup.find_all('header')),
                "nav": len(soup.find_all('nav')),
                "main": len(soup.find_all('main')),
                "footer": len(soup.find_all('footer')),
                "article": len(soup.find_all('article')),
                "aside": len(soup.find_all('aside'))
            },
            "aria": {
                "role_attributes": len(soup.find_all(attrs={'role': True})),
                "aria_labelledby": len(soup.find_all(attrs={'aria-labelledby': True})),
                "aria_label": len(soup.find_all(attrs={'aria-label': True})),
                "aria_describedby": len(soup.find_all(attrs={'aria-describedby': True}))
            }
        }

    def _check_for_issues(self, soup: BeautifulSoup, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Überprüft auf Zugänglichkeitsprobleme"""
        issues = []
        
        # Überprüfe Überschriftenhierarchie
        prev_level = 0
        for i in range(1, 7):
            curr_count = analysis["headings"][f"h{i}"]
            if curr_count > 0 and prev_level == 0 and i > 1:
                issues.append({
                    "type": "heading_hierarchy",
                    "level": "error",
                    "message": f"Heading level h{i} used before h{i-1}",
                    "wcag": ["WCAG2.1.3.1"],
                    "context": f"Found h{i} without preceding h{i-1}"
                })
            prev_level = curr_count
        
        # Überprüfe Landmarks
        if analysis["landmarks"]["main"] == 0:
            issues.append({
                "type": "landmarks",
                "level": "error",
                "message": "No <main> landmark found",
                "wcag": ["WCAG2.1.3.1", "WCAG2.4.1"],
                "context": "Document structure"
            })
        
        # Überprüfe Sprache
        if not analysis["lang_attribute"]:
            issues.append({
                "type": "language",
                "level": "error",
                "message": "Missing lang attribute on html element",
                "wcag": ["WCAG3.1.1"],
                "context": "Document language"
            })
        
        # Überprüfe Formularelemente
        self._check_form_elements(soup, issues)
        
        return issues

    def _check_form_elements(self, soup: BeautifulSoup, issues: List[Dict[str, Any]]) -> None:
        """Überprüft Formularelemente auf Zugänglichkeit"""
        inputs = soup.find_all('input', {'type': ['text', 'password', 'email', 'tel', 'number']})
        for input_field in inputs:
            if not (input_field.get('id') and soup.find('label', {'for': input_field['id']})) and \
               not (input_field.get('aria-label') or input_field.get('aria-labelledby')):
                issues.append({
                    "type": "form_labels",
                    "level": "error",
                    "message": "Input field missing label or aria-label",
                    "wcag": ["WCAG1.3.1", "WCAG3.3.2"],
                    "context": str(input_field),
                    "selector": self._get_selector(input_field)
                })

    def _get_selector(self, element) -> str:
        """Generiert einen CSS-Selektor für ein Element"""
        selector_parts = []
        
        while element and element.name:
            if element.get('id'):
                selector_parts.append(f"#{element['id']}")
                break
            elif element.get('class'):
                selector_parts.append(
                    f"{element.name}.{'.'.join(element['class'])}"
                )
            else:
                selector_parts.append(element.name)
            element = element.parent
            
        return ' '.join(reversed(selector_parts))

class Pa11yAnalyzer(BaseAnalyzer):
    """Analyzer für Pa11y Accessibility Tests"""
    
    async def analyze(self, url: str) -> Dict[str, Any]:
        """Führt Pa11y Tests aus und verarbeitet Ergebnisse"""
        try:
            # Pa11y Kommando vorbereiten
            cmd = [
                'pa11y',
                '--reporter', 'json',
                '--standard', 'WCAG2AA',
                '--timeout', '60000',
                '--wait', '1000',
                url
            ]
            
            # Pa11y ausführen
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Ergebnisse verarbeiten
            if process.returncode == 2:  # Pa11y gibt 2 zurück, wenn es Probleme findet
                try:
                    results = json.loads(stdout.decode())
                    return {
                        "status": "success",
                        "tool": "pa11y",
                        "url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "results": results
                    }
                except json.JSONDecodeError:
                    return self._create_error_result(
                        "Failed to parse Pa11y output", url
                    )
            elif process.returncode != 0:
                return self._create_error_result(
                    f"Pa11y failed with code {process.returncode}: {stderr.decode()}", 
                    url
                )
            
            # Keine Probleme gefunden
            return {
                "status": "success",
                "tool": "pa11y",
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "results": []
            }
            
        except Exception as e:
            return self._create_error_result(str(e), url)

class AxeAnalyzer(BaseAnalyzer):
    """Analyzer für Axe Core Tests"""
    
    async def analyze(self, url: str) -> Dict[str, Any]:
        """Führt Axe Core Tests aus und verarbeitet Ergebnisse"""
        try:
            async with aiohttp.ClientSession() as session:
                # Axe Core über CDP ausführen
                async with session.post(
                    'http://localhost:9222/json/new',
                    json={'url': url}
                ) as response:
                    if response.status != 200:
                        return self._create_error_result(
                            "Failed to create Chrome tab", url
                        )
                    
                    tab_info = await response.json()
                    tab_id = tab_info['id']
                    
                    # Axe Core injizieren und ausführen
                    script = """
                        const axe = require('@axe-core/cli');
                        return await axe.run();
                    """
                    
                    async with session.post(
                        f'http://localhost:9222/json/execute/{tab_id}',
                        json={'expression': script}
                    ) as exec_response:
                        if exec_response.status != 200:
                            return self._create_error_result(
                                "Failed to execute Axe Core", url
                            )
                        
                        results = await exec_response.json()
                        
                        return {
                            "status": "success",
                            "tool": "axe",
                            "url": url,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "results": results
                        }
                        
        except Exception as e:
            return self._create_error_result(str(e), url)

class LighthouseAnalyzer(BaseAnalyzer):
    """Analyzer für Lighthouse Accessibility Tests"""
    
    async def analyze(self, url: str) -> Dict[str, Any]:
        """Führt Lighthouse Tests aus und verarbeitet Ergebnisse"""
        try:
            # Lighthouse Kommando vorbereiten
            cmd = [
                'lighthouse',
                url,
                '--output=json',
                '--quiet',
                '--only-categories=accessibility',
                '--chrome-flags="--headless --no-sandbox --disable-gpu"'
            ]
            
            # Lighthouse ausführen
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return self._create_error_result(
                    f"Lighthouse failed with code {process.returncode}: {stderr.decode()}", 
                    url
                )
            
            try:
                results = json.loads(stdout.decode())
                return {
                    "status": "success",
                    "tool": "lighthouse",
                    "url": url,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "results": results.get("audits", {})
                }
            except json.JSONDecodeError:
                return self._create_error_result(
                    "Failed to parse Lighthouse output", 
                    url
                )
                
        except Exception as e:
            return self._create_error_result(str(e), url)