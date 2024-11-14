# src/crew.py

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pathlib import Path
from crewai_tools import DirectoryReadTool
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
            tools=[DirectoryReadTool()]
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

    # @agent
    # def axe_analyzer(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['axe_analyzer'],
    #         verbose=True
    #     )

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

    # @task
    # def run_axe_tests(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['run_axe_tests']
    #     )

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