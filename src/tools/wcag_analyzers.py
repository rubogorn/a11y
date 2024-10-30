import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import logging
from bs4 import BeautifulSoup
import aiohttp
from typing import Dict, Any, List
from playwright.async_api import Page, Browser, async_playwright
from abc import ABC, abstractmethod

class BaseAnalyzer(ABC):
    """Base class for all WCAG analyzers"""
    def __init__(self, results_path: Path, logger: logging.Logger):
        self.results_path = results_path
        self.logger = logger

    @abstractmethod
    async def analyze(self, url: str) -> Dict[str, Any]:
        """Abstract method for running the analysis"""
        pass

class HTMLAnalyzer(BaseAnalyzer):
    """Analyzer for HTML structure and ARIA usage"""
    
    async def analyze(self, url: str) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch URL: {response.status}")
                        
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    structure_analysis = self._analyze_structure(soup)
                    issues = self._check_for_issues(soup, structure_analysis)
                    
                    result = {
                        "analysis": structure_analysis,
                        "issues": issues,
                        "url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    self.logger.info(f"HTML analysis completed for {url}: found {len(issues)} issues")
                    return result
                    
        except Exception as e:
            error_msg = f"Error analyzing HTML structure: {str(e)}"
            self.logger.error(error_msg)
            return {
                "error": error_msg,
                "status": "failed",
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _analyze_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze HTML structure elements"""
        return {
            "doctype": bool(soup.find('doctype')),
            "lang_attribute": bool(soup.find('html', attrs={'lang': True})),
            "head_elements": {
                "title": bool(soup.find('title')),
                "meta_viewport": bool(soup.find('meta', attrs={'name': 'viewport'})),
                "meta_charset": bool(soup.find('meta', attrs={'charset': True}))
            },
            "headings": {
                f"h{i}": len(soup.find_all(f'h{i}')) for i in range(1, 7)
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
            },
            "forms": {
                "total": len(soup.find_all('form')),
                "with_labels": len([f for f in soup.find_all('form') if f.find('label')]),
                "inputs": len(soup.find_all('input')),
                "buttons": len(soup.find_all('button'))
            }
        }

    def _check_for_issues(self, soup: BeautifulSoup, structure_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for accessibility issues in the HTML structure"""
        issues = []
        
        # Check heading hierarchy
        prev_level = 0
        for i in range(1, 7):
            curr_count = structure_analysis["headings"][f"h{i}"]
            if curr_count > 0 and prev_level == 0 and i > 1:
                issues.append({
                    "type": "heading_hierarchy",
                    "level": "error",
                    "message": f"Heading level h{i} used before h{i-1}"
                })
            prev_level = curr_count
        
        # Check landmarks
        if structure_analysis["landmarks"]["main"] == 0:
            issues.append({
                "type": "landmarks",
                "level": "error",
                "message": "No <main> landmark found"
            })
        
        # Check language
        if not structure_analysis["lang_attribute"]:
            issues.append({
                "type": "language",
                "level": "error",
                "message": "Missing lang attribute on html element"
            })
        
        # Check forms for labels
        self._check_form_labels(soup, issues)
        
        return issues

    def _check_form_labels(self, soup: BeautifulSoup, issues: List[Dict[str, Any]]) -> None:
        """Check form inputs for proper labeling"""
        forms = soup.find_all('form')
        for form in forms:
            inputs = form.find_all('input', {'type': ['text', 'password', 'email', 'tel', 'number']})
            for input_field in inputs:
                if not (input_field.get('id') and form.find('label', {'for': input_field['id']})) and \
                   not (input_field.get('aria-label') or input_field.get('aria-labelledby')):
                    issues.append({
                        "type": "form_labels",
                        "level": "error",
                        "message": f"Input field missing label or aria-label: {input_field}"
                    })

class Pa11yAnalyzer(BaseAnalyzer):
    """Analyzer for Pa11y accessibility testing"""

    async def analyze(self, url: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"Starting Pa11y test for {url}")
            
            cmd = [
                'pa11y',
                '--reporter', 'json',
                '--standard', 'WCAG2AA',
                '--level', 'error',
                '--timeout', '60000',
                '--wait', '1000',
                '--ignore', 'notice',
                '--threshold', '10',
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                if process.returncode == 2:  # Pa11y returns 2 when it finds accessibility issues
                    try:
                        # Try to parse the output as JSON even with exit code 2
                        results = json.loads(stdout.decode())
                        return {
                            "status": "success",
                            "results": results,
                            "tool": "pa11y",
                            "url": url,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    except json.JSONDecodeError:
                        self.logger.error(f"Failed to parse Pa11y output as JSON: {stdout.decode()}")
                        raise
                else:
                    error_msg = f"Pa11y process failed with code {process.returncode}: {stderr.decode()}"
                    self.logger.error(error_msg)
                    return {
                        "status": "error",
                        "message": error_msg,
                        "tool": "pa11y",
                        "results": [],
                        "url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
            
            try:
                results = json.loads(stdout.decode())
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse Pa11y output: {str(e)}"
                self.logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg,
                    "tool": "pa11y",
                    "results": [],
                    "url": url,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return {
                "status": "success",
                "results": results,
                "tool": "pa11y",
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            error_msg = f"Unexpected error running Pa11y: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "tool": "pa11y",
                "results": [],
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

class AxeAnalyzer(BaseAnalyzer):
    """Analyzer for Axe accessibility testing"""

    def __init__(self, results_path: Path, logger: logging.Logger, browser: Browser):
        """
        Initialize AxeAnalyzer
        
        Args:
            results_path: Path to save results
            logger: Logger instance
            browser: Playwright browser instance
        """
        # Call parent's __init__ first
        super().__init__(results_path, logger)
        # Then set browser
        self.browser = browser

    async def analyze(self, url: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"Starting Axe test for {url}")
            
            page = await self.browser.new_page()
            await page.goto(url)
            
            # Axe-Core Script injizieren und ausführen
            await page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.0/axe.min.js")
            results = await page.evaluate("() => axe.run()")
            
            return {
                "status": "success",
                "results": results.get("violations", []),
                "tool": "axe",
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error running Axe: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "tool": "axe",
                "results": [],
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        finally:
            if 'page' in locals():
                await page.close()

class LighthouseAnalyzer(BaseAnalyzer):
    """Analyzer for Lighthouse accessibility testing"""

    def __init__(self, results_path: Path, logger: logging.Logger, browser: Browser):
        """
        Initialize LighthouseAnalyzer
        
        Args:
            results_path: Path to save results
            logger: Logger instance
            browser: Playwright browser instance
        """
        super().__init__(results_path, logger)
        self.browser = browser

    async def analyze(self, url: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"Starting Lighthouse test for {url}")
            
            cmd = [
                'lighthouse',
                url,
                '--output=json',
                '--quiet',
                '--only-categories=accessibility,best-practices',
                '--chrome-flags="--headless --no-sandbox --disable-gpu"',
                '--only-audits=accessibility'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            try:
                results = json.loads(stdout.decode())
                return {
                    "status": "success",
                    "results": results.get("audits", {}),
                    "tool": "lighthouse",
                    "url": url,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse Lighthouse output: {e}")
            
        except Exception as e:
            error_msg = f"Error running Lighthouse: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "tool": "lighthouse",
                "results": [],
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }