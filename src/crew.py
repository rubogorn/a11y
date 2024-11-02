from typing import TypedDict, List, Optional, Dict, Any
from crewai import Agent, Task, Crew, Process, LLM
from pathlib import Path
import json
import asyncio
import logging
from datetime import datetime, timezone
from .tools.result_processor import StandardizedResult
from .logging_config import get_logger

class CrewOutput(TypedDict):
    status: str
    message: Optional[str] 
    issues: List[Dict[str, Any]]
    summary: Dict[str, Any]
    timestamp: str
    url: Optional[str]

class WCAGTestingCrew:
    """WCAG 2.2 Testing Crew implementation"""

    def __init__(self):
        self.tools = self._get_wcag_testing_tools()
        self.results_path = Path("output/results")
        try:
            self.results_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger = get_logger('WCAGTestingCrew', log_dir='output/results/logs')
            self.logger.error(f"Failed to create results directory: {e}")
            raise

        self.logger = get_logger('WCAGTestingCrew', log_dir='output/results/logs')
        self._init_base_agents()
        self._init_tasks()

    def _get_wcag_testing_tools(self):
        """Initialize and return WCAG testing tools"""
        # Placeholder for actual WCAGTestingTools initialization
        return "WCAGTestingTools instance"

    def _init_base_agents(self):
        """Initialize base agents (always included)"""
        self.compliance_controller = Agent(
            role="WCAG 2.2 Compliance Controller",
            goal="Coordinate and oversee the complete WCAG 2.2 testing process",
            backstory="""You are an expert in web accessibility testing and WCAG 2.2 guidelines. 
            Your role is to ensure comprehensive testing coverage and validate results.""",
            verbose=True,
            llm="gpt-4o-mini"
        )

        self.consolidation_agent = Agent(
            role="Test Results Consolidation Specialist",
            goal="Merge and analyze results from all testing tools and agents",
            backstory="""You are an expert in analyzing and consolidating technical test results,
            identifying patterns and prioritizing issues.""",
            verbose=True,
            llm="gpt-4o-mini"
        )

        self.remediation_specialist = Agent(
            role="Accessibility Remediation Specialist",
            goal="Develop solutions and guidance for identified accessibility issues",
            backstory="""You are experienced in creating practical solutions and guidance
            for web accessibility issues, with deep knowledge of WCAG 2.2 requirements.""",
            verbose=True,
            llm="gpt-4o-mini"
        )

    def _get_accessibility_analyzer(self):
        """Create and return the Accessibility Analyzer agent"""
        return Agent(
            role="Accessibility Analysis Specialist",
            goal="Analyze webpage structure and content for WCAG 2.2 compliance",
            backstory="""You are specialized in analyzing HTML structure, ARIA implementations,
            and semantic markup for accessibility compliance.""",
            verbose=True,
            llm="gpt-4o-mini"
        )

    def _init_tasks(self):
        """Initialize all tasks with proper dependencies and context handling"""
        self.analyze_webpage = Task(
            description="""Analyze the webpage for WCAG 2.2 compliance using the provided test results.
            
            Input: URL and raw test results from automated tools
            Expected Output: JSON formatted analysis covering:
            - HTML structure issues
            - ARIA usage problems
            - Semantic markup validation
            - Document structure evaluation
            
            Use the raw_results from the testing tools to provide a comprehensive analysis.""",
            expected_output="""Detailed JSON report containing:
            {
                "html_structure": {
                    "issues": [...],
                    "aria_usage": [...],
                    "semantic_markup": [...],
                    "document_structure": [...]
                }
            }""",
            agent=None,  # Will be set dynamically based on configuration
            context_required=["url", "raw_results"]
        )

        self.consolidate_results = Task(
            description="""Consolidate and analyze all test results:
            1. Merge results from all testing tools
            2. Remove duplicate findings
            3. Categorize by WCAG criteria
            4. Prioritize by severity
            5. Generate comprehensive report
            
            Input: Analysis results from previous task
            Expected Output: JSON formatted consolidated report""",
            expected_output="""Consolidated JSON report with structure:
            {
                "issues": [{
                    "type": "string",
                    "severity": "number",
                    "message": "string",
                    "wcag_criteria": ["..."],
                    "tools": ["..."]
                }],
                "summary": {
                    "total_issues": "number",
                    "by_severity": {...},
                    "by_tool": {...}
                }
            }""",
            agent=self.consolidation_agent,
            context_required=["url", "raw_results", "normalized_results"]
        )

        self.create_remediation_plan = Task(
            description="""Create detailed remediation guidance for each issue:
            1. Analyze consolidated issues
            2. Generate specific solutions
            3. Provide code examples
            4. Include implementation steps
            
            Input: Consolidated results from previous task
            Expected Output: JSON formatted remediation plan""",
            expected_output="""Remediation plan JSON with structure:
            {
                "issues": [{
                    "issue_id": "string",
                    "solution": {
                        "steps": ["..."],
                        "code_example": "string",
                        "wcag_reference": "string",
                        "priority": "number"
                    }
                }],
                "summary": {
                    "total_issues": "number",
                    "estimated_effort": "string"
                }
            }""",
            agent=self.remediation_specialist,
            context_required=["normalized_results"]
        )

        self.validate_results = Task(
            description="""Final validation of all results and remediation plans:
            1. Verify WCAG 2.2 coverage
            2. Validate technical accuracy
            3. Check solution completeness
            4. Approve final report
            
            Input: All previous task results
            Expected Output: JSON formatted validation report""",
            expected_output="""Validation report JSON with structure:
            {
                "status": "string",
                "validation_results": {
                    "wcag_coverage": {
                        "covered_criteria": ["..."],
                        "missing_criteria": ["..."]
                    },
                    "technical_accuracy": {
                        "validated": "boolean",
                        "issues": ["..."]
                    },
                    "solution_completeness": {
                        "complete": "boolean",
                        "missing_elements": ["..."]
                    }
                },
                "approval": {
                    "approved": "boolean",
                    "comments": ["..."]
                }
            }""",
            agent=self.compliance_controller,
            context_required=["normalized_results", "remediation_plan"]
        )

    def get_crew(self, context: Dict[str, Any]) -> Crew:
        """
        Assembles and returns the WCAG testing crew based on configuration
        
        Args:
            context: Dictionary containing configuration including use_accessibility_analyzer flag
        """
        agents = [
            self.compliance_controller,
            self.consolidation_agent,
            self.remediation_specialist
        ]

        tasks = []
        
        # Configure analyze_webpage task based on accessibility analyzer usage
        if context.get("use_accessibility_analyzer", False):
            self.accessibility_analyzer = self._get_accessibility_analyzer()
            agents.append(self.accessibility_analyzer)
            self.analyze_webpage.agent = self.accessibility_analyzer
            tasks.append(self.analyze_webpage)
            self.logger.info("Accessibility Analyzer included in crew")
        else:
            self.logger.info("Accessibility Analyzer not included in crew")

        # Add remaining tasks
        tasks.extend([
            self.consolidate_results,
            self.create_remediation_plan,
            self.validate_results
        ])

        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run the complete WCAG 2.2 testing process"""
        try:
            url = context.get("url", "")
            raw_results = context.get("raw_results", {})
            normalized_results = context.get("normalized_results", [])

            crew = self.get_crew(context)
            
            try:
                # Execute crew tasks
                results = crew.kickoff()
                
                # Ensure results are in the correct format
                results_dict = self._standardize_results(results, url)
                
                # Save results
                self.save_results(results_dict)
                
                return results_dict
                    
            except Exception as e:
                self.logger.error(f"Crew execution failed: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        except Exception as e:
            error_results = {
                "error": str(e),
                "status": "failed",
                "url": url if "url" in locals() else "",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.save_results(error_results, "error_report.json")
            return error_results

    def _standardize_results(self, results: Any, url: str) -> Dict[str, Any]:
        """Standardize crew results to ensure all required fields are present"""
        # Convert to dictionary if needed
        if hasattr(results, 'dict'):
            results_dict = results.dict()
        elif hasattr(results, 'to_dict'):
            results_dict = results.to_dict()
        else:
            results_dict = results if isinstance(results, dict) else {"data": str(results)}

        # Extract or create required fields
        issues = []
        summary = {"total_issues": 0, "by_severity": {}, "by_tool": {}}

        # Process validation results if present
        if "validation_results" in results_dict:
            validation = results_dict["validation_results"]
            # Add WCAG coverage to summary
            if "wcag_coverage" in validation:
                summary["wcag_coverage"] = validation["wcag_coverage"]

        # Process remediation plan if present
        if "remediation_plan" in results_dict:
            remediation = results_dict.get("remediation_plan", {})
            remediation_issues = remediation.get("issues", [])
            issues.extend(remediation_issues)
            summary["total_issues"] = len(remediation_issues)

        # Ensure all required fields are present
        standardized_results = {
            "status": results_dict.get("status", "completed"),
            "issues": issues,
            "summary": summary,
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Add any additional fields from original results
        for key, value in results_dict.items():
            if key not in standardized_results:
                standardized_results[key] = value

        return standardized_results

    def save_results(self, results: Dict[str, Any], filename: str = None) -> None:
        """Save crew results to a JSON file
        
        Args:
            results: Dictionary containing the results to save
            filename: Optional filename, defaults to timestamp-based name
        """
        try:
            if not filename:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                filename = f"crew_results_{timestamp}.json"

            output_path = self.results_path / filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Results saved to {output_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            raise