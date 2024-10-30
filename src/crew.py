from typing import TypedDict, List, Optional, Dict, Any
from crewai import Agent, Task, Crew, Process
from pathlib import Path
import json
import asyncio
import logging
from .tools import WCAGTestingTools
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
        self.tools = WCAGTestingTools()
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

    def _init_base_agents(self):
        """Initialize base agents (always included)"""
        self.compliance_controller = Agent(
            role="WCAG 2.2 Compliance Controller",
            goal="Coordinate and oversee the complete WCAG 2.2 testing process",
            backstory="""You are an expert in web accessibility testing and WCAG 2.2 guidelines. 
            Your role is to ensure comprehensive testing coverage and validate results.""",
            verbose=True,
            llm_config={"model": "gpt-4-mini"}
        )

        self.consolidation_agent = Agent(
            role="Test Results Consolidation Specialist",
            goal="Merge and analyze results from all testing tools and agents",
            backstory="""You are an expert in analyzing and consolidating technical test results,
            identifying patterns and prioritizing issues.""",
            verbose=True,
            llm_config={"model": "gpt-4-mini"}
        )

        self.remediation_specialist = Agent(
            role="Accessibility Remediation Specialist",
            goal="Develop solutions and guidance for identified accessibility issues",
            backstory="""You are experienced in creating practical solutions and guidance
            for web accessibility issues, with deep knowledge of WCAG 2.2 requirements.""",
            verbose=True,
            llm_config={"model": "gpt-4-mini"}
        )

    def _get_accessibility_analyzer(self):
        """Create and return the Accessibility Analyzer agent"""
        return Agent(
            role="Accessibility Analysis Specialist",
            goal="Analyze webpage structure and content for WCAG 2.2 compliance",
            backstory="""You are specialized in analyzing HTML structure, ARIA implementations,
            and semantic markup for accessibility compliance.""",
            verbose=True,
            llm_config={"model": "gpt-4-mini"}
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
                
                # Validate results format
                if not isinstance(results, dict):
                    self.logger.error(f"Invalid results format: {type(results)}")
                    return {
                        "status": "error",
                        "message": "Invalid results format",
                        "data": results,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                
                # Check required fields
                required_fields = ["status", "issues", "summary"]
                missing_fields = [field for field in required_fields if field not in results]
                
                if missing_fields:
                    self.logger.error(f"Missing required fields: {missing_fields}")
                    return {
                        "status": "error", 
                        "message": f"Missing required fields: {missing_fields}",
                        "data": results,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                # Create standardized result
                std_result = StandardizedResult.from_raw_results(results)
                serialized_results = self._serialize_results(std_result.to_dict())
                
                # Add information about accessibility analyzer usage
                serialized_results["accessibility_analyzer_used"] = context.get("use_accessibility_analyzer", False)
                
                # Save results
                self.save_results(serialized_results)
                
                return serialized_results
                    
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