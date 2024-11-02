from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from datetime import datetime, timezone

from src.wcag.wcag_reference_processor import WCAGReferenceProcessor
from src.logging_config import get_logger, ui_message

class WCAGTaskExecutor:
    """
    Executes WCAG analysis tasks using the WCAGReferenceProcessor.
    Processes accessibility test results and generates detailed WCAG-mapped reports.
    """
    
    def __init__(self):
        """Initialize the WCAG task executor"""
        self.logger = get_logger('WCAGTaskExecutor', log_dir='output/results/logs')
        self.reference_processor = WCAGReferenceProcessor()
        self.results_cache = {}

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
            ui_message("\nProcessing test results and mapping to WCAG criteria...")
            
            normalized_results = raw_results.get("normalized_results", [])
            for index, issue in enumerate(normalized_results, 1):
                ui_message(
                    self.logger,
                    f"Processing issue {index}/{len(normalized_results)}...",
                    level="DEBUG"
                )
                processed_issue = await self._process_single_issue(issue)
                if processed_issue:
                    processed_results["issues"].append(processed_issue)
                    
            # Generate summary statistics
            self._generate_summary(processed_results)
            
            # Cache results for potential reuse
            cache_key = self._generate_cache_key(raw_results)
            self.results_cache[cache_key] = processed_results
            
            self.logger.info(
                f"Successfully processed {len(processed_results['issues'])} issues "
                f"and mapped them to WCAG criteria"
            )
            return processed_results
            
        except Exception as e:
            error_msg = f"Error processing results: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _process_single_issue(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single accessibility issue and enrich it with WCAG data
        
        Args:
            issue: Dictionary containing issue details
            
        Returns:
            Enriched issue data with WCAG mappings or None if processing fails
        """
        try:
            # First try to find by direct code mapping
            wcag_data = None
            if issue.get("code"):
                wcag_data = self.reference_processor.find_criterion_by_code(issue["code"])
                self.logger.debug(f"Found WCAG mapping by code: {issue['code']}")
            
            # If no direct mapping found, search by description
            if not wcag_data and issue.get("message"):
                search_results = await self.reference_processor.search_by_description(
                    issue["message"]
                )
                if search_results:
                    wcag_data = search_results[0]  # Use the most relevant match
                    self.logger.debug(
                        f"Found WCAG mapping by description for issue: {issue['message'][:50]}..."
                    )
            
            if not wcag_data:
                self.logger.warning(
                    f"No WCAG mapping found for issue: {issue.get('message', '')[:50]}..."
                )
                return issue  # Return original issue if no mapping found
            
            # Enrich the issue with WCAG data
            criterion_details = self.reference_processor.get_criterion_details(wcag_data["id"])
            
            enriched_issue = {
                **issue,  # Original issue data
                "wcag_mapping": {
                    "criterion_id": wcag_data["id"],
                    "title": criterion_details.get("title", ""),
                    "level": criterion_details.get("level", ""),
                    "description": criterion_details.get("description", ""),
                    "special_cases": criterion_details.get("special_cases", []),
                    "documentation_links": criterion_details.get("documentation_links", {}),
                    "recommendations": criterion_details.get("best_practices", [])
                },
                "processed_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Add severity if not present
            if "severity" not in enriched_issue:
                enriched_issue["severity"] = self._assess_severity(
                    enriched_issue, 
                    enriched_issue["wcag_mapping"]
                )
            
            return enriched_issue
            
        except Exception as e:
            self.logger.error(f"Error processing issue: {str(e)}", exc_info=True)
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
                
                if principle not in principle_counts:
                    principle_counts[principle] = {
                        "count": 0,
                        "criteria": set(),
                        "severity_counts": {1: 0, 2: 0, 3: 0, 4: 0}
                    }
                
                principle_counts[principle]["count"] += 1
                principle_counts[principle]["criteria"].add(criterion_id)
                
                # Count by severity within principle
                severity = issue.get("severity", 3)
                principle_counts[principle]["severity_counts"][severity] += 1
                
                # Track covered criteria
                if criterion_id != "unknown":
                    covered_criteria.add(criterion_id)
            
            # Update summary with detailed statistics
            summary["by_level"] = level_counts
            summary["by_principle"] = {
                principle: {
                    "count": data["count"],
                    "unique_criteria": len(data["criteria"]),
                    "severity_breakdown": data["severity_counts"]
                }
                for principle, data in principle_counts.items()
            }
            summary["coverage"] = sorted(list(covered_criteria))
            summary["total_criteria_covered"] = len(covered_criteria)
            
            # Add timestamp to summary
            summary["generated_at"] = datetime.now(timezone.utc).isoformat()
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}", exc_info=True)
            # Ensure we have at least an empty summary structure
            processed_results["summary"] = {
                "total_issues": 0,
                "by_level": {},
                "by_principle": {},
                "coverage": []
            }

    def _assess_severity(self, issue: Dict[str, Any], wcag_mapping: Dict[str, Any]) -> int:
        """
        Assess the severity of an issue based on its WCAG level and impact
        
        Args:
            issue: Issue data
            wcag_mapping: WCAG mapping data
            
        Returns:
            Severity level (1-4, where 1 is most severe)
        """
        try:
            # Default to moderate severity
            base_severity = 3

            # Adjust based on WCAG level
            if wcag_mapping and 'level' in wcag_mapping:
                level = wcag_mapping['level'].upper()
                if level == 'A':
                    base_severity = 1  # Most severe for Level A violations
                elif level == 'AA':
                    base_severity = 2  # Serious for Level AA violations
                # Level AAA violations remain at moderate severity

            # Consider impact if available
            impact = issue.get('impact', '').lower()
            if impact in ['critical', 'severe']:
                base_severity = max(1, base_severity - 1)
            elif impact == 'minor':
                base_severity = min(4, base_severity + 1)

            return base_severity

        except Exception as e:
            self.logger.error(f"Error assessing severity: {str(e)}", exc_info=True)
            return 3  # Return moderate severity as default

    def _generate_cache_key(self, results: Dict[str, Any]) -> str:
        """
        Generate a cache key for results
        
        Args:
            results: Results dictionary to generate key for
            
        Returns:
            Cache key string
        """
        try:
            # Create a simplified version of results for hashing
            key_data = {
                "url": results.get("url", ""),
                "timestamp": results.get("timestamp", ""),
                "count": len(results.get("normalized_results", []))
            }
            return json.dumps(key_data, sort_keys=True)
        except Exception as e:
            self.logger.error(f"Error generating cache key: {str(e)}", exc_info=True)
            return str(datetime.now(timezone.utc).timestamp())