import logging
from typing import Dict, Any, List, Union
import re
from datetime import datetime, timezone

class TestResultProcessor:
    """Process and normalize results from different testing tools"""
    
    def __init__(self):
        self.issue_levels = {
            "error": 1,
            "warning": 2,
            "notice": 3
        }
        self.logger = logging.getLogger('ResultProcessor')

    def normalize_pa11y_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize Pa11y results to common format
        
        Args:
            results: Raw Pa11y results
                
        Returns:
            List of normalized issues
        """
        if not isinstance(results.get("results"), dict) and not isinstance(results.get("results"), list):
            self.logger.debug(f"Invalid Pa11y results format: {results.get('status')}")
            return []
                
        normalized = []
        raw_issues = []
        
        # Handle different possible result structures
        if isinstance(results.get("results"), dict) and "issues" in results["results"]:
            raw_issues = results["results"]["issues"]
        elif isinstance(results.get("results"), list):
            raw_issues = results["results"]
        
        self.logger.debug(f"Processing {len(raw_issues)} Pa11y issues")
        
        for issue in raw_issues:
            if not issue:
                continue
                    
            # Map Pa11y error types to our severity levels
            issue_type = issue.get("type", "").lower()
            if issue_type == "error":
                level = 1
            elif issue_type == "warning":
                level = 2
            else:  # notice or unknown
                level = 3
                    
            normalized.append({
                "tool": "pa11y",
                "type": issue.get("type", "unknown"),
                "code": issue.get("code", ""),
                "message": issue.get("message", ""),
                "context": issue.get("context", ""),
                "selector": issue.get("selector", ""),
                "level": level,
                "wcag_criteria": self._extract_wcag_criteria(issue.get("code", "")),
                "runner": issue.get("runner", "pa11y"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        self.logger.info(f"Normalized {len(normalized)} Pa11y results")
        return normalized

    def normalize_axe_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize Axe results to common format
        
        Args:
            results: Raw Axe results
            
        Returns:
            List of normalized issues
        """
        if results.get("status") != "success" or not isinstance(results.get("results"), list):
            self.logger.debug(f"Invalid Axe results format: {results.get('status')}")
            return []
            
        normalized = []
        for issue in results.get("results", []):
            if not issue:
                continue
                
            # Map Axe impact levels to our severity levels
            impact_to_level = {
                "critical": 1,
                "serious": 1,
                "moderate": 2,
                "minor": 3
            }
            
            normalized.append({
                "tool": "axe",
                "type": issue.get("type", "unknown"),
                "code": issue.get("code", ""),
                "message": issue.get("message", ""),
                "context": issue.get("context", ""),
                "selector": " ".join(issue.get("selector", [])) if isinstance(issue.get("selector"), list) else issue.get("selector", ""),
                "level": impact_to_level.get(issue.get("type", "minor"), 3),
                "wcag_criteria": [criteria for criteria in issue.get("wcag", []) if criteria.startswith("WCAG")],
                "help_url": issue.get("helpUrl", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        self.logger.info(f"Normalized {len(normalized)} Axe results")
        return normalized
    
    def normalize_lighthouse_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize Lighthouse results to common format
        
        Args:
            results: Raw Lighthouse results
            
        Returns:
            List of normalized issues
        """
        if results.get("status") != "success" or not isinstance(results.get("results"), list):
            self.logger.debug(f"Invalid Lighthouse results format: {results.get('status')}")
            return []
            
        normalized = []
        for issue in results.get("results", []):
            if not issue:
                continue
                
            # Map Lighthouse scores to severity levels
            score = issue.get('score', 1)
            if score == 0:
                level = 1  # error
            elif score < 0.9:
                level = 2  # warning
            else:
                level = 3  # notice
                
            normalized.append({
                "tool": "lighthouse",
                "type": issue.get("type", "unknown"),
                "code": issue.get("id", ""),
                "message": issue.get("message", ""),
                "description": issue.get("description", ""),
                "level": level,
                "score": score,
                "details": issue.get("details", {}),
                "warnings": issue.get("warnings", []),
                "manual": issue.get("manual", False),
                "wcag_criteria": [],  # Lighthouse doesn't directly map to WCAG criteria
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        self.logger.info(f"Normalized {len(normalized)} Lighthouse results")
        return normalized

    def normalize_html_structure_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize HTML structure analysis results
        
        Args:
            results: Raw HTML analysis results
            
        Returns:
            List of normalized issues
        """
        if not isinstance(results.get("issues"), list):
            self.logger.debug("Invalid HTML structure results format")
            return []
            
        normalized = []
        for issue in results.get("issues", []):
            if not issue:
                continue
                
            normalized.append({
                "tool": "html_analyzer",
                "type": issue.get("type", "unknown"),
                "message": issue.get("message", ""),
                "level": self.issue_levels.get(issue.get("level", "notice"), 3),
                "wcag_criteria": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        self.logger.info(f"Normalized {len(normalized)} HTML structure results")
        return normalized

    def _extract_wcag_criteria(self, text: str) -> List[str]:
        """
        Extract WCAG criteria references from text
        
        Args:
            text: Text to analyze
            
        Returns:
            List of WCAG criteria found
        """
        if not text:
            return []
            
        pattern = r"WCAG\s*(\d+\.\d+\.\d+)"
        matches = re.findall(pattern, text)
        
        criteria = [f"WCAG{m}" for m in matches]
        self.logger.debug(f"Extracted WCAG criteria: {criteria}")
        return criteria

    def merge_results(self, all_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Merge and normalize results from all tools
        
        Args:
            all_results: Dictionary containing results from all tools
            
        Returns:
            List of merged and normalized issues
        """
        try:
            if not isinstance(all_results, dict):
                self.logger.error("Invalid results format for merging")
                return []
                
            normalized_results = []
            
            # Process results from each tool
            tool_processors = {
                "html_structure": self.normalize_html_structure_results,
                "pa11y": self.normalize_pa11y_results,
                "axe": self.normalize_axe_results,
                "lighthouse": self.normalize_lighthouse_results
            }
            
            # Track seen issues to avoid duplicates
            seen_issues = {}
            
            for tool, processor in tool_processors.items():
                tool_results = all_results.get(tool)
                if tool_results is not None:
                    try:
                        processed_results = processor(tool_results)
                        
                        # Deduplicate based on message and selector
                        for result in processed_results:
                            key = (
                                result.get("message", ""),
                                result.get("selector", ""),
                                result.get("type", "")
                            )
                            
                            if key in seen_issues:
                                # Update existing issue with additional context
                                existing = seen_issues[key]
                                existing["tools"].add(tool)
                                if result.get("wcag_criteria"):
                                    existing["wcag_criteria"].extend(result["wcag_criteria"])
                            else:
                                # Add new issue
                                result["tools"] = {tool}
                                seen_issues[key] = result
                                
                    except Exception as e:
                        self.logger.error(f"Error processing {tool} results: {str(e)}")
                        continue

            # Convert seen_issues to list and clean up
            normalized_results = list(seen_issues.values())
            
            # Post-processing
            for result in normalized_results:
                # Convert tool set to list
                result["tools"] = list(result["tools"])
                # Deduplicate WCAG criteria
                if "wcag_criteria" in result:
                    result["wcag_criteria"] = list(set(result["wcag_criteria"]))
                    
            # Sort by severity and type
            normalized_results.sort(
                key=lambda x: (
                    x.get("level", 3),
                    x.get("type", "unknown"),
                    x.get("message", "")
                )
            )
            
            self.logger.info(f"Merged results: {len(normalized_results)} unique issues found")
            return normalized_results
                
        except Exception as e:
            self.logger.error(f"Error merging results: {str(e)}")
            return []

    def get_summary_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for the normalized results
        
        Args:
            results: List of normalized results
            
        Returns:
            Dictionary containing summary statistics
        """
        try:
            summary = {
                "total_issues": len(results),
                "by_level": {
                    "error": len([r for r in results if r.get("level") == 1]),
                    "warning": len([r for r in results if r.get("level") == 2]),
                    "notice": len([r for r in results if r.get("level") == 3])
                },
                "by_tool": {},
                "wcag_criteria_coverage": set()
            }
            
            # Count issues by tool
            for result in results:
                tool = result.get("tool", "unknown")
                summary["by_tool"][tool] = summary["by_tool"].get(tool, 0) + 1
                
                # Collect WCAG criteria
                if "wcag_criteria" in result:
                    summary["wcag_criteria_coverage"].update(result["wcag_criteria"])
            
            # Convert WCAG criteria set to sorted list
            summary["wcag_criteria_coverage"] = sorted(list(summary["wcag_criteria_coverage"]))
            
            self.logger.info(f"Generated summary statistics: {summary['total_issues']} total issues")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating summary statistics: {str(e)}")
            return {
                "error": str(e),
                "total_issues": 0,
                "by_level": {},
                "by_tool": {},
                "wcag_criteria_coverage": []
            }