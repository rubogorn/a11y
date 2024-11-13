# src/crew.py

from typing import Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import json
import asyncio
import aiofiles
import yaml

from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import tool

from .logging_config import get_logger
from .wcag.wcag_mapping_agent import WCAGMappingAgent
from .wcag.unified_result_processor import UnifiedResultProcessor
from .wcag.analyzers.html_analyzer import HTMLAnalyzer
from .wcag.analyzers.pa11y_analyzer import Pa11yAnalyzer
from .wcag.analyzers.axe_analyzer import AxeAnalyzer
from .wcag.analyzers.lighthouse_analyzer import LighthouseAnalyzer

class WCAGToolsService:
    """Service class for managing analyzer tools"""
    
    def __init__(self, results_path: Path):
        self.results_path = results_path
        self.logger = get_logger('WCAGToolsService', log_dir='output/logs')
        self._analyzers = {}
        self._init_analyzers()
        
    def _init_analyzers(self):
        """Initialize available analyzers"""
        self.logger.info("Initializing analyzers")
        
        analyzers = {
            'pa11y': Pa11yAnalyzer(self.results_path / 'pa11y'),
            'axe': AxeAnalyzer(self.results_path / 'axe'),
            'lighthouse': LighthouseAnalyzer(self.results_path / 'lighthouse'),
            'html': HTMLAnalyzer(self.results_path / 'html')
        }
        
        self._analyzers = {
            name: analyzer for name, analyzer in analyzers.items() 
            if hasattr(analyzer, 'name')
        }
        
    def get_analyzer(self, name: str):
        """Get a specific analyzer"""
        return self._analyzers.get(name)

@CrewBase
class WCAGTestingCrew:
    """WCAG 2.2 Testing Crew with integrated WCAG manager"""

    def __init__(self):
        """Initialize the WCAG Testing Crew"""
        self.logger = get_logger('WCAGTestingCrew', log_dir='output/logs')
        self.results_path = Path("output/results")
        self.results_path.mkdir(parents=True, exist_ok=True)
        self.tools = WCAGToolsService(self.results_path)
        self.wcag_agent = WCAGMappingAgent()
        self.result_processor = UnifiedResultProcessor()

    @agent
    def pa11y_analyzer(self) -> Agent:
        """Pa11y analyzer agent"""
        pa11y_tool = self.tools.get_analyzer('pa11y')
        
        @tool("Run Pa11y Analysis")
        def run_pa11y_analysis(url: str) -> str:
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                setup_result = loop.run_until_complete(pa11y_tool.setup())
                results = loop.run_until_complete(pa11y_tool.analyze(url))
                return json.dumps(results, indent=2)
            except Exception as e:
                self.logger.error(f"Pa11y analysis failed: {str(e)}")
                return json.dumps({"status": "error", "message": str(e), "url": url})

        return Agent(
            config=self.agents_config['pa11y_analyzer'],
            tools=[run_pa11y_analysis]
        )

    # Add other agents using @agent decorator
    @agent
    def axe_analyzer(self) -> Agent:
        return Agent(config=self.agents_config['axe_analyzer'])

    @agent
    def lighthouse_analyzer(self) -> Agent:
        return Agent(config=self.agents_config['lighthouse_analyzer'])

    @agent
    def accessibility_analyzer(self) -> Agent:
        return Agent(config=self.agents_config['accessibility_analyzer'])

    @agent
    def wcag_checkpoints(self) -> Agent:
        return Agent(config=self.agents_config['wcag_checkpoints'])

    @agent
    def remediation_specialist(self) -> Agent:
        return Agent(config=self.agents_config['remediation_specialist'])

    @agent
    def compliance_controller(self) -> Agent:
        return Agent(config=self.agents_config['compliance_controller'])

    # Define tasks using @task decorator
    @task
    def run_pa11y(self) -> Task:
        return Task(config=self.tasks_config['run_pa11y'])

    @task
    def run_axe(self) -> Task:
        return Task(config=self.tasks_config['run_axe'])

    @task
    def run_lighthouse(self) -> Task:
        return Task(config=self.tasks_config['run_lighthouse'])

    @task
    def analyze_accessibility(self) -> Task:
        return Task(config=self.tasks_config['analyze_accessibility'])

    @task
    def analyze_wcag(self) -> Task:
        return Task(config=self.tasks_config['analyze_wcag'])

    @task
    def develop_solutions(self) -> Task:
        return Task(config=self.tasks_config['develop_solutions'])

    @task
    def validate_compliance(self) -> Task:
        return Task(config=self.tasks_config['validate_compliance'])

    @crew
    def testing_crew(self) -> Crew:
        """Creates the testing crew"""
        return Crew(
            agents=[
                self.pa11y_analyzer,
                self.axe_analyzer,
                self.lighthouse_analyzer,
                self.accessibility_analyzer
            ],
            tasks=[
                self.run_pa11y,
                self.run_axe,
                self.run_lighthouse,
                self.analyze_accessibility
            ],
            process=Process.sequential,
            verbose=True
        )

    @crew
    def analysis_crew(self) -> Crew:
        """Creates the analysis crew"""
        return Crew(
            agents=[
                self.wcag_checkpoints,
                self.remediation_specialist,
                self.compliance_controller
            ],
            tasks=[
                self.analyze_wcag,
                self.develop_solutions,
                self.validate_compliance
            ],
            process=Process.sequential,
            verbose=True
        )

    # Keep the existing helper methods
    async def process_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Existing implementation...
        pass

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Existing implementation using self.testing_crew and self.analysis_crew
        pass

    async def _save_detailed_results(self, results: Dict[str, Any]) -> None:
        # Existing implementation...
        pass