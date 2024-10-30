from typing import Dict, List, Any
from pathlib import Path
import json
from datetime import datetime, timezone

from src.wcag.wcag_reference_processor import WCAGReferenceProcessor
from src.logging_config import get_logger

class WCAGTaskExecutor:
    """
    Executes WCAG analysis tasks using the WCAGReferenceProcessor.
    Processes accessibility test results and generates detailed WCAG-mapped reports.
    """
    
    def __init__(self):
        """Initialize the WCAG task executor"""
        self.logger = get_logger('WCAGTaskExecutor')
        self.reference_processor = WCAGReferenceProcessor()

    async def process_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw accessibility test results and map them to WCAG criteria
        
        Args:
            raw_results: Dictionary containing raw test results
            
        Returns:
            Processed results with WCAG mappings and recommendations
        """
        try:
            processed_results = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "issues": [],
                "summary": {
                    "total_issues": 0,
                    "by_level": {},
                    "by_principle": {},
                    "coverage": []
                }
            }
            
            # Process each issue from the raw results
            normalized_results = raw_results.get("normalized_results", [])
            for issue in normalized_results:
                processed_issue = await self._process_single_issue(issue)
                if processed_issue:
                    processed_results["issues"].append(processed_issue)
                    
            # Generate summary statistics
            self._generate_summary(processed_results)
            
            self.logger.info(f"Processed {len(processed_results['issues'])} issues")
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Error processing results: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _process_single_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single accessibility issue and enrich it with WCAG data
        
        Args:
            issue: Dictionary containing issue details
            
        Returns:
            Enriched issue data with WCAG mappings
        """
        try:
            # First try to find by direct code mapping
            wcag_data = None
            if issue.get("code"):
                wcag_data = self.reference_processor.find_criterion_by_code(issue["code"])
            
            # If no direct mapping found, search by description
            if not wcag_data and issue.get("message"):
                search_results = await self.reference_processor.search_by_description(
                    issue["message"]
                )
                if search_results:
                    wcag_data = search_results[0]  # Use the most relevant match
            
            if not wcag_data:
                self.logger.warning(f"No WCAG mapping found for issue: {issue.get('message', '')}")
                return issue  # Return original issue if no mapping found
            
            # Enrich the issue with WCAG data
            criterion_details = self.reference_processor.get_criterion_details(wcag_data["id"])
            
            return {
                **issue,  # Original issue data
                "wcag_mapping": {
                    "criterion_id": wcag_data["id"],
                    "title": criterion_details.get("title", ""),
                    "level": criterion_details.get("level", ""),
                    "description": criterion_details.get("description", ""),
                    "special_cases": criterion_details.get("special_cases", []),
                    "documentation_links": criterion_details.get("documentation_links", {})
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error processing issue: {e}")
            return issue

    def _generate_summary(self, processed_results: Dict[str, Any]) -> None:
        """
        Generate summary statistics for processed results
        
        Args:
            processed_results: Dictionary containing processed issues
        """
        try:
            summary = processed_results["summary"]
            issues = processed_results["issues"]
            
            # Count totals
            summary["total_issues"] = len(issues)
            
            # Count by WCAG level
            level_counts = {}
            principle_counts = {}
            covered_criteria = set()
            
            for issue in issues:
                wcag_mapping = issue.get("wcag_mapping", {})
                
                # Count by level
                level = wcag_mapping.get("level", "unknown")
                level_counts[level] = level_counts.get(level, 0) + 1
                
                # Count by principle
                criterion_id = wcag_mapping.get("criterion_id", "unknown")
                principle = criterion_id.split(".")[0] if "." in criterion_id else "unknown"
                principle_counts[principle] = principle_counts.get(principle, 0) + 1
                
                # Track covered criteria
                if criterion_id != "unknown":
                    covered_criteria.add(criterion_id)
            
            summary["by_level"] = level_counts
            summary["by_principle"] = principle_counts
            summary["coverage"] = sorted(list(covered_criteria))
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            # Ensure we have at least an empty summary structure
            processed_results["summary"] = {
                "total_issues": 0,
                "by_level": {},
                "by_principle": {},
                "coverage": []
            }