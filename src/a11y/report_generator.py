# src/report_generator.py

from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import json
import aiofiles
from .logging_config import get_logger

class ReportGenerator:
    """Generates and saves WCAG test reports"""
    
    def __init__(self):
        self.logger = get_logger('ReportGenerator')
        self.output_dir = Path("output/results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def save_results(self, url: str, crew_results: Dict[str, Any]) -> Path:
        """
        Save test results and generate reports
        
        Args:
            url: Tested URL
            crew_results: Results from the crew analysis
            
        Returns:
            Path to output directory
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_dir = self.output_dir / timestamp
        results_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save raw results
            async with aiofiles.open(results_dir / "raw_results.json", 'w') as f:
                await f.write(json.dumps(crew_results, indent=2))
                
            self.logger.info(f"Results saved to {results_dir}")
            return results_dir
            
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            raise