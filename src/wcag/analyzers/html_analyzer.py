# src/wcag/analyzers/html_analyzer.py

import logging
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import re
from .base_analyzer import BaseToolAnalyzer

class HTMLAnalyzer(BaseToolAnalyzer):
    """
    Analyzer für HTML Struktur und Semantik.
    Fokussiert auf WCAG 2.2 Konformität der HTML-Implementierung.
    """
    
    def __init__(self, results_path: Path, logger: Optional[logging.Logger] = None):
        """
        Initialisiert den HTML Analyzer
        
        Args:
            results_path: Pfad für Ergebnisse
            logger: Optional logger instance
        """
        super().__init__(results_path, logger)
        
        # Definiere wichtige HTML5 Landmarks
        self.landmark_roles = {
            'banner': 'header[role="banner"], header:not([role])',
            'navigation': 'nav[role="navigation"], nav:not([role])',
            'main': 'main[role="main"], main:not([role])',
            'complementary': 'aside[role="complementary"], aside:not([role])',
            'contentinfo': 'footer[role="contentinfo"], footer:not([role])',
            'search': '[role="search"]'
        }
        
        # Definiere wichtige ARIA Live Regions
        self.live_regions = {
            'alert': '[role="alert"]',
            'status': '[role="status"]',
            'log': '[role="log"]',
            'timer': '[role="timer"]',
            'marquee': '[role="marquee"]',
            'progressbar': '[role="progressbar"]'
        }
        
    async def setup(self) -> bool:
        """
        HTML Analyzer benötigt kein spezielles Setup
        
        Returns:
            True, da keine Setup-Anforderungen
        """
        return True

    async def analyze(self, url: str) -> Dict[str, Any]:
        """
        Analysiert die HTML-Struktur einer URL
        
        Args:
            url: Zu testende URL
            
        Returns:
            HTML Analyse-Ergebnisse
        """
        try:
            # Hole HTML-Content
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return self.create_result(
                            "error",
                            url,
                            error=f"Failed to fetch URL: {response.status}"
                        )
                    
                    html = await response.text()
                    
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Führe Analysen durch
            structure_analysis = self._analyze_document_structure(soup)
            landmark_analysis = self._analyze_landmarks(soup)
            semantic_analysis = self._analyze_semantic_elements(soup)
            
            # Kombiniere die Ergebnisse
            issues = []
            issues.extend(structure_analysis["issues"])
            issues.extend(landmark_analysis["issues"])
            issues.extend(semantic_analysis["issues"])
            
            # Erstelle Gesamtanalyse
            analysis_result = {
                "document_structure": structure_analysis["stats"],
                "landmarks": landmark_analysis["stats"],
                "semantic_elements": semantic_analysis["stats"],
                "issues": issues,
                "statistics": {
                    "total_issues": len(issues),
                    "by_severity": self._count_issues_by_severity(issues),
                    "by_category": self._count_issues_by_category(issues)
                }
            }
            
            # Speichere Ergebnisse
            await self.save_results(analysis_result)
            
            return self.create_result(
                "success",
                url,
                data=analysis_result
            )
            
        except Exception as e:
            error_msg = f"Error analyzing HTML: {str(e)}"
            self.logger.error(error_msg)
            return self.create_result(
                "error",
                url,
                error=error_msg
            )

    def _analyze_document_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analysiert die grundlegende Dokumentstruktur
        
        Args:
            soup: BeautifulSoup Instanz
            
        Returns:
            Analyse der Dokumentstruktur
        """
        issues = []
        stats = {
            "has_doctype": bool(soup.find('doctype')),
            "has_html_tag": bool(soup.find('html')),
            "has_head": bool(soup.find('head')),
            "has_body": bool(soup.find('body')),
            "language": self._check_language(soup),
            "title": bool(soup.find('title')),
            "meta_viewport": bool(soup.find('meta', attrs={'name': 'viewport'})),
            "meta_charset": bool(soup.find('meta', attrs={'charset': True}))
        }
        
        # Prüfe grundlegende Struktur
        if not stats["has_doctype"]:
            issues.append({
                "type": "structure",
                "category": "document",
                "severity": "error",
                "message": "Document is missing DOCTYPE declaration",
                "wcag": ["4.1.1"],
                "context": "Document root"
            })
            
        if not stats["language"]:
            issues.append({
                "type": "structure",
                "category": "document",
                "severity": "error",
                "message": "Document language is not specified",
                "wcag": ["3.1.1"],
                "context": "html tag"
            })
            
        if not stats["title"]:
            issues.append({
                "type": "structure",
                "category": "document",
                "severity": "error",
                "message": "Document does not have a title",
                "wcag": ["2.4.2"],
                "context": "head section"
            })
            
        if not stats["meta_viewport"]:
            issues.append({
                "type": "structure",
                "category": "document",
                "severity": "warning",
                "message": "No viewport meta tag found",
                "wcag": ["1.4.4"],
                "context": "head section"
            })
        
        return {
            "stats": stats,
            "issues": issues
        }

    def _check_language(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Prüft die Sprach-Deklaration des Dokuments
        
        Args:
            soup: BeautifulSoup Instanz
            
        Returns:
            Gefundener Sprachcode oder None
        """
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag['lang']
        return None

    def _analyze_landmarks(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analysiert die Landmark-Regionen
        
        Args:
            soup: BeautifulSoup Instanz
            
        Returns:
            Analyse der Landmarks
        """
        issues = []
        stats = {role: [] for role in self.landmark_roles}
        
        # Prüfe jede Landmark-Region
        for role, selector in self.landmark_roles.items():
            elements = soup.select(selector)
            stats[role] = len(elements)
            
            # Spezifische Prüfungen für verschiedene Landmarks
            if role == 'main' and not elements:
                issues.append({
                    "type": "landmark",
                    "category": "structure",
                    "severity": "error",
                    "message": "No main landmark found",
                    "wcag": ["1.3.1", "2.4.1"],
                    "context": "document structure"
                })
                
            elif role == 'navigation' and not elements:
                issues.append({
                    "type": "landmark",
                    "category": "navigation",
                    "severity": "warning",
                    "message": "No navigation landmark found",
                    "wcag": ["2.4.1"],
                    "context": "document structure"
                })
                
        return {
            "stats": stats,
            "issues": issues
        }
    
    # src/wcag/analyzers/html_analyzer.py (Fortsetzung)

    def _analyze_semantic_elements(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analysiert die semantischen Elemente und deren Verwendung
        
        Args:
            soup: BeautifulSoup Instanz
            
        Returns:
            Analyse der semantischen Elemente
        """
        issues = []
        stats = {
            "headings": self._analyze_headings(soup),
            "lists": self._analyze_lists(soup),
            "tables": self._analyze_tables(soup),
            "forms": self._analyze_forms(soup),
            "interactive": self._analyze_interactive_elements(soup),
            "aria": self._analyze_aria_usage(soup)
        }
        
        # Füge Issues aus den einzelnen Analysen zusammen
        for category in stats:
            if "issues" in stats[category]:
                issues.extend(stats[category]["issues"])
                # Entferne Issues aus Stats um Duplizierung zu vermeiden
                del stats[category]["issues"]
        
        return {
            "stats": stats,
            "issues": issues
        }

    def _analyze_headings(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analysiert die Überschriften-Hierarchie
        
        Args:
            soup: BeautifulSoup Instanz
            
        Returns:
            Analyse der Überschriften
        """
        issues = []
        stats = {f"h{i}": len(soup.find_all(f'h{i}')) for i in range(1, 7)}
        
        # Prüfe Überschriften-Hierarchie
        prev_level = 0
        for i in range(1, 7):
            curr_count = stats[f"h{i}"]
            if curr_count > 0:
                if prev_level == 0 and i > 1:
                    issues.append({
                        "type": "heading",
                        "category": "structure",
                        "severity": "error",
                        "message": f"Heading level h{i} is used before h{i-1}",
                        "wcag": ["1.3.1", "2.4.6"],
                        "context": f"h{i} elements"
                    })
            prev_level = curr_count
            
        # Prüfe auf leere Überschriften
        for i in range(1, 7):
            empty_headings = soup.find_all(f'h{i}', string=lambda s: not s or not s.strip())
            if empty_headings:
                issues.append({
                    "type": "heading",
                    "category": "content",
                    "severity": "error",
                    "message": f"Empty h{i} heading found",
                    "wcag": ["1.3.1", "2.4.6"],
                    "context": str(empty_headings[0])
                })
        
        return {
            "counts": stats,
            "issues": issues
        }

    def _analyze_forms(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analysiert Formular-Elemente und deren Zugänglichkeit
        
        Args:
            soup: BeautifulSoup Instanz
            
        Returns:
            Analyse der Formulare
        """
        issues = []
        stats = {
            "forms": len(soup.find_all('form')),
            "inputs": len(soup.find_all('input')),
            "selects": len(soup.find_all('select')),
            "textareas": len(soup.find_all('textarea')),
            "buttons": len(soup.find_all('button')),
            "labels": len(soup.find_all('label'))
        }
        
        # Prüfe Formular-Controls
        for input_field in soup.find_all(['input', 'select', 'textarea']):
            # Überspringe versteckte und Submit-Felder
            if input_field.get('type') in ['hidden', 'submit', 'button']:
                continue
                
            field_id = input_field.get('id', '')
            has_label = bool(soup.find('label', attrs={'for': field_id})) if field_id else False
            has_aria_label = bool(input_field.get('aria-label') or input_field.get('aria-labelledby'))
            
            if not (has_label or has_aria_label):
                issues.append({
                    "type": "form",
                    "category": "labels",
                    "severity": "error",
                    "message": "Form control missing label or aria-label",
                    "wcag": ["1.3.1", "3.3.2", "4.1.2"],
                    "context": str(input_field),
                    "selector": self._get_selector(input_field)
                })
        
        # Prüfe Buttons
        for button in soup.find_all('button'):
            if not button.string or not button.string.strip():
                issues.append({
                    "type": "form",
                    "category": "buttons",
                    "severity": "error",
                    "message": "Button has no text content",
                    "wcag": ["4.1.2"],
                    "context": str(button),
                    "selector": self._get_selector(button)
                })
        
        return {
            "counts": stats,
            "issues": issues
        }

    def _analyze_tables(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analysiert Tabellen auf korrekte Struktur
        
        Args:
            soup: BeautifulSoup Instanz
            
        Returns:
            Analyse der Tabellen
        """
        issues = []
        stats = {
            "tables": len(soup.find_all('table')),
            "with_headers": 0,
            "with_caption": 0
        }
        
        for table in soup.find_all('table'):
            # Prüfe auf Header
            headers = table.find_all(['th', 'thead'])
            if headers:
                stats["with_headers"] += 1
            else:
                issues.append({
                    "type": "table",
                    "category": "structure",
                    "severity": "error",
                    "message": "Table has no headers",
                    "wcag": ["1.3.1"],
                    "context": str(table)[:200],
                    "selector": self._get_selector(table)
                })
            
            # Prüfe auf Caption
            if table.find('caption'):
                stats["with_caption"] += 1
            else:
                issues.append({
                    "type": "table",
                    "category": "structure",
                    "severity": "warning",
                    "message": "Table has no caption",
                    "wcag": ["1.3.1"],
                    "context": str(table)[:200],
                    "selector": self._get_selector(table)
                })
        
        return {
            "counts": stats,
            "issues": issues
        }

    def _analyze_interactive_elements(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analysiert interaktive Elemente
        
        Args:
            soup: BeautifulSoup Instanz
            
        Returns:
            Analyse der interaktiven Elemente
        """
        issues = []
        stats = {
            "links": len(soup.find_all('a')),
            "buttons": len(soup.find_all('button')),
            "tabindex": len(soup.find_all(attrs={'tabindex': True}))
        }
        
        # Prüfe Links
        for link in soup.find_all('a'):
            if not link.get('href'):
                issues.append({
                    "type": "link",
                    "category": "navigation",
                    "severity": "error",
                    "message": "Link has no href attribute",
                    "wcag": ["4.1.2"],
                    "context": str(link),
                    "selector": self._get_selector(link)
                })
            
            if not link.string or not link.string.strip():
                issues.append({
                    "type": "link",
                    "category": "content",
                    "severity": "error",
                    "message": "Link has no text content",
                    "wcag": ["2.4.4", "4.1.2"],
                    "context": str(link),
                    "selector": self._get_selector(link)
                })
        
        # Prüfe tabindex
        for elem in soup.find_all(attrs={'tabindex': True}):
            try:
                tabindex = int(elem['tabindex'])
                if tabindex > 0:
                    issues.append({
                        "type": "interactive",
                        "category": "keyboard",
                        "severity": "warning",
                        "message": "Positive tabindex value may disrupt keyboard navigation",
                        "wcag": ["2.1.1", "2.4.3"],
                        "context": str(elem),
                        "selector": self._get_selector(elem)
                    })
            except ValueError:
                pass
        
        return {
            "counts": stats,
            "issues": issues
        }

    def _analyze_aria_usage(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analysiert ARIA-Attribute und Rollen
        
        Args:
            soup: BeautifulSoup Instanz
            
        Returns:
            Analyse der ARIA-Verwendung
        """
        issues = []
        stats = {
            "roles": len(soup.find_all(attrs={'role': True})),
            "live_regions": sum(len(soup.select(selector)) for selector in self.live_regions.values()),
            "aria_labels": len(soup.find_all(attrs={'aria-label': True})),
            "aria_labelledby": len(soup.find_all(attrs={'aria-labelledby': True})),
            "aria_describedby": len(soup.find_all(attrs={'aria-describedby': True}))
        }
        
        # Prüfe aria-labelledby Referenzen
        for elem in soup.find_all(attrs={'aria-labelledby': True}):
            ref_ids = elem['aria-labelledby'].split()
            for ref_id in ref_ids:
                if not soup.find(id=ref_id):
                    issues.append({
                        "type": "aria",
                        "category": "references",
                        "severity": "error",
                        "message": f"aria-labelledby references non-existent ID: {ref_id}",
                        "wcag": ["4.1.2"],
                        "context": str(elem),
                        "selector": self._get_selector(elem)
                    })
        
        # Prüfe aria-describedby Referenzen
        for elem in soup.find_all(attrs={'aria-describedby': True}):
            ref_ids = elem['aria-describedby'].split()
            for ref_id in ref_ids:
                if not soup.find(id=ref_id):
                    issues.append({
                        "type": "aria",
                        "category": "references",
                        "severity": "error",
                        "message": f"aria-describedby references non-existent ID: {ref_id}",
                        "wcag": ["4.1.2"],
                        "context": str(elem),
                        "selector": self._get_selector(elem)
                    })
        
        return {
            "counts": stats,
            "issues": issues
        }

    def _get_selector(self, element) -> str:
        """
        Generiert einen CSS-Selektor für ein Element
        
        Args:
            element: BeautifulSoup Tag
            
        Returns:
            CSS-Selektor String
        """
        selectors = []
        for parent in element.parents:
            if parent.name == '[document]':
                break
            
            # Versuche eine eindeutige ID zu verwenden
            if parent.get('id'):
                selectors.append(f"#{parent['id']}")
                break
            
            # Andernfalls verwende die Position des Elements
            siblings = parent.find_previous_siblings(parent.name)
            if siblings:
                selectors.append(f"{parent.name}:nth-of-type({len(siblings) + 1})")
            else:
                selectors.append(parent.name)
        
        # Element selbst
        if element.get('id'):
            selectors.append(f"#{element['id']}")
        else:
            siblings = element.find_previous_siblings(element.name)
            if siblings:
                selectors.append(f"{element.name}:nth-of-type({len(siblings) + 1})")
            else:
                selectors.append(element.name)
        
        return ' > '.join(reversed(selectors))

    def _count_issues_by_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Zählt Issues nach Schweregrad
        
        Args:
            issues: Liste von Issues
            
        Returns:
            Zählung nach Schweregrad
        """
        counts = {"error": 0, "warning": 0, "info": 0}
        for issue in issues:
            severity = issue.get("severity", "info")
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    def _count_issues_by_category(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Zählt Issues nach Kategorie
        
        Args:
            issues: Liste von Issues
            
        Returns:
            Zählung nach Kategorie
        """
        counts = {}
        for issue in issues:
            category = issue.get("category", "other")
            counts[category] = counts.get(category, 0) + 1
        return counts

    async def cleanup(self) -> None:
        """Keine spezielle Bereinigung erforderlich"""
        pass