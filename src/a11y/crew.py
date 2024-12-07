# src/crew.py

import os
from a11y.tools.axe_core_tool import AxeCoreTool
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pathlib import Path
from crewai_tools import DirectoryReadTool, BrowserbaseLoadTool, FileReadTool, SeleniumScrapingTool
from dotenv import load_dotenv
from .wcag.unified_result_processor import UnifiedResultProcessor
from .logging_config import get_logger

load_dotenv()

# browserbase_tool = BrowserbaseLoadTool()

# Extract the text from the site
# text = browserbase_tool.run()
# print(text)

@CrewBase
class WCAGTestingCrew:
    """WCAG 2.2 Testing Crew with integrated WCAG Manager"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self, results_path: Path = None):
        self.logger = get_logger(__name__)
        self.results_path = results_path or Path("output/results")
        
        # Make sure the results directory exists
        self.results_path.mkdir(parents=True, exist_ok=True)

    # @agent
    # def compliance_controller(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['compliance_controller'],
    #         verbose=True,
    #         memory=True,
    #         allow_delegation=True,
    #         max_rpm=30,
    #         max_iter=5,
    #         respect_context_window=True,
    #         use_system_prompt=True,
    #         max_retry_limit=2,
    #         cache=True,
    #         llm='gpt-4o-mini',
    #         tools=[FileReadTool()]
    #         # tools:
    #         #   - BrowserbaseWebLoader  # For initial site analysis
    #         #   - DirectoryReader      # For managing test artifacts
    #         #   - FileHandler         # For handling test results and reports
    #    )

    # @agent
    # def wcag_checkpoints(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['wcag_checkpoints'],
    #     )

    @agent
    def axe_core_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['axe_core_specialist'],
            tools=[
                AxeCoreTool(),
                FileReadTool()
            ],
            verbose=True,
            memory=True,
            allow_delegation=False,
            max_rpm=3,
            max_iter=2,
            respect_context_window=True,
            use_system_prompt=True,
            max_retry_limit=2,
            cache=True
        )

    # @agent
    # def accessibility_analyzer(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['accessibility_analyzer'],
    #         tools=[SeleniumScrapingTool(website_url='https://shapeofnew.de')],
    #         verbose=True
    #     )

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
        return Agent(
            config=self.agents_config['report_specialist'],
            verbose=True
        )
    
    @task
    def run_axe_tests(self) -> Task:
        return Task(
            config=self.tasks_config['axe_core_testing_task'],
            verbose=True
        )

    # @task
    # def init_testing(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['init_testing'],
    #         verbose=True
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
    #         config=self.tasks_config['analyze_wcag_structure']
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
        return Task(
            config=self.tasks_config['report_generation_task']
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
            tasks=self.tasks,
            # manager_agent=self.compliance_controller(),
            # process=Process.hierarchical,
            verbose=True
        )