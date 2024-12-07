# src/crew.py

import os
import yaml
from a11y.tools.axe_core_tool import AxeCoreTool
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pathlib import Path
from crewai_tools import DirectoryReadTool, FileReadTool, SeleniumScrapingTool
from dotenv import load_dotenv
from .wcag.unified_result_processor import UnifiedResultProcessor
from .logging_config import get_logger
from .utils import log_directory_contents

load_dotenv()

# Load environment variables for Browserbase
BROWSERBASE_API_KEY = os.getenv('BROWSERBASE_API_KEY')
BROWSERBASE_PROJECT_ID = os.getenv('BROWSERBASE_PROJECT_ID')

@CrewBase
class WCAGTestingCrew:
    """WCAG 2.2 Testing Crew with integrated WCAG Manager"""

    def __init__(self, results_path: Path = None):
        self.logger = get_logger(__name__)
        self.results_path = results_path or Path("output/results")
        
        # Make sure the results directory exists
        self.results_path.mkdir(parents=True, exist_ok=True)
        
        # Load configuration files
        try:
            with open('src/a11y/config/agents.yaml', 'r') as f:
                self.agents_config = yaml.safe_load(f)
            with open('src/a11y/config/tasks.yaml', 'r') as f:
                self.tasks_config = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load configuration files: {e}")
            raise

    @agent
    def compliance_controller(self) -> Agent:
        """Manager agent responsible for coordinating the testing process"""
        return Agent(
            role=self.agents_config['compliance_controller']['role'],
            goal=self.agents_config['compliance_controller']['goal'],
            backstory=self.agents_config['compliance_controller']['backstory'],
            verbose=True,
            allow_delegation=True,
            tools=[DirectoryReadTool(), FileReadTool()]
            # tools:
            #   - BrowserbaseWebLoader  # For initial site analysis
            #   - DirectoryReader      # For managing test artifacts
            #   - FileHandler         # For handling test results and reports
        )

    # @agent
    # def wcag_checkpoints(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['wcag_checkpoints'],
    #     )

    @agent
    def axe_core_specialist(self) -> Agent:
        """Specialist agent for running Axe Core tests"""
        config = self.agents_config['axe_core_specialist']
        return Agent(
            role=config['role'],
            goal=config['goal'],
            backstory=config['backstory'],
            verbose=config.get('verbose', True),
            memory=config.get('memory', True),
            allow_delegation=config.get('allow_delegation', False),
            tools=[AxeCoreTool(), FileReadTool()]
        )

    @agent
    def accessibility_analyzer(self) -> Agent:
        """Analyzer agent for WCAG structure analysis"""
        config = self.agents_config['accessibility_analyzer']
        
        return Agent(
            role=config['role'],
            goal=config['goal'],
            backstory=config['backstory'],
            verbose=config.get('verbose', True),
            memory=config.get('memory', True),
            allow_delegation=config.get('allow_delegation', False),
            tools=[FileReadTool(), SeleniumScrapingTool()]
        )

    # @agent
    # def pa11y_analyzer(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['pa11y_analyzer'],
    #         verbose=True
    #     )

    # @agent
    # def lighthouse_analyzer(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['lighthouse_analyzer'],
    #         verbose=True
    #     )

    # @agent
    # def remediation_specialist(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['remediation_specialist'],
    #         verbose=True
    #     )

    @agent
    def report_specialist(self) -> Agent:
        """Report generation specialist agent"""
        config = self.agents_config['report_specialist']
        return Agent(
            role=config['role'],
            goal=config['goal'],
            backstory=config['backstory'],
            verbose=config.get('verbose', True),
            memory=config.get('memory', True),
            allow_delegation=config.get('allow_delegation', False),
            tools=[
                FileReadTool(),
                DirectoryReadTool()
            ]
        )

    @task
    def run_axe_tests(self) -> Task:
        return Task(
            description=self.tasks_config['axe_core_testing_task']['description'],
            expected_output=self.tasks_config['axe_core_testing_task']['expected_output'],
            agent=self.axe_core_specialist()
        )

    # @task
    # def manage_testing_workflow(self) -> Task:
    #     return Task(
    #         description=self.tasks_config['manage_testing_workflow']['description'],
    #         expected_output=self.tasks_config['manage_testing_workflow']['expected_output'],
    #         agent=self.compliance_controller()
    #     )

    # @task
    # def verify_tool_availability(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['verify_tool_availability']
    #     )

    # @task
    # def run_pa11y_tests(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['run_pa11y_tests']
    #     )

    # @task
    # def run_lighthouse_tests(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['run_lighthouse_tests']
    #     )

    # @task
    # def analyze_wcag_structure(self) -> Task:
    #     return Task(
    #         description=self.tasks_config['analyze_wcag_structure']['description'],
    #         expected_output=self.tasks_config['analyze_wcag_structure']['expected_output'],
    #         agent=self.accessibility_analyzer()
    #     )

    # @task
    # def map_wcag_criteria(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['map_wcag_criteria']
    #     )

    # @task
    # def develop_remediation(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['develop_remediation']
    #     )

    # @task
    # def validate_results(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['validate_results']
    #     )

    @task
    def report_generation_task(self) -> Task:
        """Report generation task with enhanced logging"""
        self.logger.info("Starting report generation task")
        
        # Log available files using the new utility
        log_directory_contents(self.logger, self.results_path)
        
        return Task(
            description=self.tasks_config['report_generation_task']['description'],
            expected_output=self.tasks_config['report_generation_task']['expected_output'],
            agent=self.report_specialist()
        )

    @crew
    def testing_crew(self) -> Crew:
        """Creates the testing crew with compliance controller as manager"""
        return Crew(
            agents=[
                #self.accessibility_analyzer(),
                self.axe_core_specialist(),
                self.report_specialist()
            ],
            tasks=[
                # self.manage_testing_workflow(),
                self.run_axe_tests(),
                # self.analyze_wcag_structure(),
                self.report_generation_task()
            ],
            #manager_agent=self.compliance_controller(),
            #process=Process.hierarchical,
            verbose=True
        )