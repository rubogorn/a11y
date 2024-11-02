from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional

class WCAGReportMapper:
    """Maps normalized test results to WCAG 2.2 criteria and principles"""

    def __init__(self):
        """Initialize the WCAG mapper with criteria mappings"""
        self.logger = logging.getLogger('WCAGReportMapper')
        
        # WCAG 2.2 Principles
        self.principles = {
            "1": "Perceivable",
            "2": "Operable",
            "3": "Understandable",
            "4": "Robust"
        }
        
        # WCAG criteria mappings
        self.wcag_mappings = {
            # Principle 1: Perceivable
            "H49": {
                "principle": "1",
                "guideline": "1.3",
                "criteria": "1.3.1",
                "level": "A",
                "title": "Info and Relationships",
                "description": "Information, structure, and relationships conveyed through presentation can be programmatically determined."
            },
            "F92": {
                "principle": "1",
                "guideline": "1.3",
                "criteria": "1.3.1",
                "level": "A",
                "title": "Info and Relationships",
                "description": "Information, structure, and relationships conveyed through presentation can be programmatically determined."
            },
            # Principle 2: Operable
            "2.4.1": {
                "principle": "2",
                "guideline": "2.4",
                "criteria": "2.4.1",
                "level": "A",
                "title": "Bypass Blocks",
                "description": "A mechanism is available to bypass blocks of content that are repeated on multiple Web pages."
            },
            # Principle 3: Understandable
            "3.3.1": {
                "principle": "3",
                "guideline": "3.3",
                "criteria": "3.3.1",
                "level": "A",
                "title": "Error Identification",
                "description": "If an input error is automatically detected, the item that is in error is identified and the error is described to the user in text."
            },
            # Principle 4: Robust
            "4.1.1": {
                "principle": "4",
                "guideline": "4.1",
                "criteria": "4.1.1",
                "level": "A",
                "title": "Parsing",
                "description": "In content implemented using markup languages, elements have complete start and end tags, elements are nested according to their specifications, elements do not contain duplicate attributes, and any IDs are unique."
            }
            # Add more WCAG mappings as needed
        }

    def map_results_to_wcag(self, normalized_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Maps normalized test results to WCAG criteria structure
        
        Args:
            normalized_results: List of normalized test results
            
        Returns:
            Dictionary containing WCAG-structured results
        """
        try:
            # Initialize structure for all principles
            wcag_issues = {
                principle: {
                    "name": name,
                    "criteria": {},
                    "total_issues": 0,
                    "failed": 0
                }
                for principle, name in self.principles.items()
            }

            # Process each result
            for result in normalized_results:
                wcag_info = self._extract_wcag_info(result)
                if wcag_info:
                    self._add_issue_to_wcag_structure(wcag_issues, wcag_info, result)
                else:
                    self._add_unmapped_issue(wcag_issues, result)

            self.logger.info(f"Mapped {len(normalized_results)} results to WCAG criteria")
            return wcag_issues
            
        except Exception as e:
            self.logger.error(f"Error mapping results to WCAG: {str(e)}")
            return self._create_empty_wcag_structure()

    def _extract_wcag_info(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extracts WCAG information from a result
        
        Args:
            result: Single test result
            
        Returns:
            WCAG mapping information or None if not found
        """
        try:
            # First try to get from code
            code = result.get("code", "")
            if code:
                for key in self.wcag_mappings.keys():
                    if key in code:
                        return self.wcag_mappings[key]

            # Then try WCAG criteria directly
            wcag_criteria = result.get("wcag_criteria", [])
            for criterion in wcag_criteria:
                criterion_id = criterion.replace("WCAG", "").strip()
                if criterion_id in self.wcag_mappings:
                    return self.wcag_mappings[criterion_id]

            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting WCAG info: {str(e)}")
            return None

    def _add_issue_to_wcag_structure(self, wcag_issues: Dict[str, Any], wcag_info: Dict[str, Any], 
                                   result: Dict[str, Any]) -> None:
        """
        Adds an issue to the WCAG structure
        
        Args:
            wcag_issues: WCAG issues structure
            wcag_info: WCAG mapping information
            result: Test result to add
        """
        try:
            principle = wcag_info["principle"]
            criteria = wcag_info["criteria"]
            
            # Initialize criteria if not exists
            if criteria not in wcag_issues[principle]["criteria"]:
                wcag_issues[principle]["criteria"][criteria] = {
                    "title": wcag_info["title"],
                    "description": wcag_info["description"],
                    "level": wcag_info["level"],
                    "status": "Fail" if result["level"] == 1 else "Warning",
                    "issues": []
                }
            
            # Add the issue
            wcag_issues[principle]["criteria"][criteria]["issues"].append({
                "description": result["message"],
                "context": result.get("context", ""),
                "selector": result.get("selector", ""),
                "severity": result["level"],
                "tools": result["tools"]
            })
            
            # Update counters
            wcag_issues[principle]["total_issues"] += 1
            if result["level"] == 1:
                wcag_issues[principle]["failed"] += 1
                
        except Exception as e:
            self.logger.error(f"Error adding issue to WCAG structure: {str(e)}")

    def _add_unmapped_issue(self, wcag_issues: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Adds an unmapped issue to a general category
        
        Args:
            wcag_issues: WCAG issues structure
            result: Test result to add
        """
        try:
            # Add to Principle 4 (Robust) as a general technical issue
            principle = "4"
            criteria = "4.1.1"  # General parsing/technical issues
            
            if criteria not in wcag_issues[principle]["criteria"]:
                wcag_issues[principle]["criteria"][criteria] = {
                    "title": "Technical Issues",
                    "description": "Issues that may affect robustness and compatibility",
                    "level": "A",
                    "status": "Fail" if result["level"] == 1 else "Warning",
                    "issues": []
                }
            
            wcag_issues[principle]["criteria"][criteria]["issues"].append({
                "description": result["message"],
                "context": result.get("context", ""),
                "selector": result.get("selector", ""),
                "severity": result["level"],
                "tools": result["tools"]
            })
            
            wcag_issues[principle]["total_issues"] += 1
            if result["level"] == 1:
                wcag_issues[principle]["failed"] += 1
                
        except Exception as e:
            self.logger.error(f"Error adding unmapped issue: {str(e)}")

    def _create_empty_wcag_structure(self) -> Dict[str, Any]:
        """Creates an empty WCAG structure for error cases"""
        return {
            principle: {
                "name": name,
                "criteria": {},
                "total_issues": 0,
                "failed": 0
            }
            for principle, name in self.principles.items()
        }

    def generate_report_data(self, normalized_results: List[Dict[str, Any]], url: str) -> Dict[str, Any]:
        """
        Generates complete report data structure
        
        Args:
            normalized_results: List of normalized test results
            url: URL that was tested
            
        Returns:
            Complete report data structure
        """
        try:
            wcag_issues = self.map_results_to_wcag(normalized_results)
            
            # Calculate summary statistics
            total_issues = sum(p["total_issues"] for p in wcag_issues.values())
            total_failed = sum(p["failed"] for p in wcag_issues.values())
            
            by_level = {
                "A": {"total": 0, "failed": 0},
                "AA": {"total": 0, "failed": 0},
                "AAA": {"total": 0, "failed": 0}
            }
            
            # Process criteria by level
            for principle in wcag_issues.values():
                for criterion in principle["criteria"].values():
                    level = criterion["level"]
                    by_level[level]["total"] += 1
                    if criterion["status"] == "Fail":
                        by_level[level]["failed"] += 1

            return {
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_criteria": total_issues,
                    "failed": total_failed,
                    "passed": total_issues - total_failed,
                    "not_applicable": 0,
                    "by_level": by_level,
                    "by_principle": {
                        pid: {
                            "name": pdata["name"],
                            "total": pdata["total_issues"],
                            "failed": pdata["failed"]
                        }
                        for pid, pdata in wcag_issues.items()
                    }
                },
                "results": wcag_issues
            }
            
        except Exception as e:
            self.logger.error(f"Error generating report data: {str(e)}")
            return {
                "error": str(e),
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }