# src/crew.py

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pathlib import Path
import yaml
from datetime import datetime, timezone
import json
import aiofiles
from typing import Dict, Any

from .wcag.unified_result_processor import UnifiedResultProcessor
from .logging_config import get_logger

@CrewBase
class WCAGTestingCrew:
    """WCAG 2.2 Testing Crew with integrated WCAG Manager"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        """Initialize the WCAG Testing Crew with all components"""
        # Base initialization
        self.results_path = Path("output/results")
        self.results_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger('WCAGTestingCrew', log_dir='output/results/logs')
        
        # Initialize Result Processor
        self.result_processor = UnifiedResultProcessor(logger=self.logger)
        
        self.logger.info("WCAGTestingCrew initialized successfully")

    @agent
    def compliance_controller(self) -> Agent:
        return Agent(
            config=self.agents_config['compliance_controller'],
            verbose=True
        )

    @agent
    def wcag_checkpoints(self) -> Agent:
        return Agent(
            config=self.agents_config['wcag_checkpoints'],
            verbose=True
        )

    @agent
    def accessibility_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['accessibility_analyzer'],
            verbose=True
        )

    # @agent
    # def pa11y_analyzer(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['pa11y_analyzer'],
    #         verbose=True
    #     )

    @agent
    def axe_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['axe_analyzer'],
            verbose=True
        )

    # @agent
    # def lighthouse_analyzer(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['lighthouse_analyzer'],
    #         verbose=True
    #     )

    @agent
    def remediation_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['remediation_specialist'],
            verbose=True
        )

    @task
    def init_testing(self) -> Task:
        return Task(
            config=self.tasks_config['init_testing']
        )

    @task
    def verify_tool_availability(self) -> Task:
        return Task(
            config=self.tasks_config['verify_tool_availability']
        )

    # @task
    # def run_pa11y_tests(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['run_pa11y_tests']
    #     )

    @task
    def run_axe_tests(self) -> Task:
        return Task(
            config=self.tasks_config['run_axe_tests']
        )

    # @task
    # def run_lighthouse_tests(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['run_lighthouse_tests']
    #     )

    @task
    def analyze_wcag_structure(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_wcag_structure']
        )

    @task
    def map_wcag_criteria(self) -> Task:
        return Task(
            config=self.tasks_config['map_wcag_criteria']
        )

    @task
    def develop_remediation(self) -> Task:
        return Task(
            config=self.tasks_config['develop_remediation']
        )

    @task
    def validate_results(self) -> Task:
        return Task(
            config=self.tasks_config['validate_results']
        )

    @crew
    def testing_crew(self) -> Crew:
        """Creates the testing crew for initial tests"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the complete WCAG 2.2 test process"""
        try:
            self.logger.info(f"Starting WCAG analysis for URL: {context.get('url')}")

            # Run the crew
            crew_instance = self.testing_crew()
            results = await crew_instance.kickoff_async(inputs=context)
            
            # Process results
            final_results = await self.process_results(results, context)
            
            # Save detailed results
            await self._save_detailed_results(final_results)
            
            return final_results

        except Exception as e:
            error_msg = f"Error in run process: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "status": "failed",
                "url": context.get("url", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def process_results(self, crew_output: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the test results with WCAG integration"""
        try:
            # Extract results from crew output
            results = self._serialize_crew_output(crew_output)
            
            # Add context information
            results["url"] = context.get("url", "")
            results["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            return results

        except Exception as e:
            self.logger.error(f"Error processing results: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _serialize_crew_output(self, crew_output: Any) -> dict:
        """Convert CrewOutput to a serializable dictionary with error handling"""
        try:
            if hasattr(crew_output, 'raw_output'):
                if isinstance(crew_output.raw_output, str):
                    try:
                        return json.loads(crew_output.raw_output)
                    except json.JSONDecodeError:
                        return {"raw_output": crew_output.raw_output}
                elif isinstance(crew_output.raw_output, dict):
                    return crew_output.raw_output
            
            return {
                "status": "completed",
                "message": str(crew_output) if crew_output is not None else None,
                "issues": [],
                "summary": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error serializing crew output: {str(e)}")
            return {
                "status": "error",
                "message": f"Error serializing crew output: {str(e)}",
                "issues": [],
                "summary": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _save_detailed_results(self, results: Dict[str, Any]) -> None:
        """Save detailed analysis results"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_dir = self.results_path / timestamp
            results_dir.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(results_dir / "results.json", 'w') as f:
                await f.write(json.dumps(results, indent=2))
                
            self.logger.info(f"Saved detailed results to {results_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving detailed results: {e}")