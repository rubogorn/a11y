import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from crewai_tools import JSONSearchTool
from src.logging_config import get_logger

class WCAGReferenceProcessor:
    """
    Processes WCAG reference data and provides search capabilities for accessibility testing.
    Uses RAG-based search to map accessibility issues to WCAG criteria.
    """
    
    def __init__(self, wcag_json_path: Union[str, Path] = "ressources/wcag.json"):
        """
        Initialize the WCAG reference processor.
        
        Args:
            wcag_json_path: Path to the WCAG reference JSON file
        """
        self.wcag_json_path = Path(wcag_json_path)
        self.logger = get_logger('WCAGReferenceProcessor')
        
        # Initialize JSON search tool with specific configuration
        self.json_search = JSONSearchTool(
            json_path=str(self.wcag_json_path),
            config={
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": "gpt-4o-mini",
                        "temperature": 0.3
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-ada-002"
                    }
                }
            }
        )
        
        try:
            self._init_wcag_data()
        except Exception as e:
            self.logger.error(f"Failed to initialize WCAG data: {e}")
            raise

    def _init_wcag_data(self) -> None:
        """Initialize and validate WCAG reference data"""
        try:
            # Validate that the file exists
            if not self.wcag_json_path.exists():
                raise FileNotFoundError(f"WCAG reference file not found at {self.wcag_json_path}")
            
            # Load and validate the JSON structure
            with open(self.wcag_json_path, 'r', encoding='utf-8') as f:
                self.wcag_data = json.load(f)
                
            # Create quick lookup maps
            self._create_lookup_maps()
            
            self.logger.info("WCAG reference data initialized successfully")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format in WCAG reference file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing WCAG data: {e}")
            raise

    def _create_lookup_maps(self) -> None:
        """Create lookup maps for quick access to WCAG criteria"""
        self.id_map = {}
        self.code_map = {}
        
        for criterion in self.wcag_data:
            criterion_id = criterion.get('id')
            if criterion_id:
                self.id_map[criterion_id] = criterion
                
                # Map known tool-specific codes to this criterion
                for code in criterion.get('tool_codes', []):
                    self.code_map[code.lower()] = criterion_id

    def find_criterion_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Find WCAG criterion by tool-specific code.
        
        Args:
            code: The tool-specific code to search for
            
        Returns:
            Matching WCAG criterion or None if not found
        """
        try:
            criterion_id = self.code_map.get(code.lower())
            if criterion_id:
                return self.id_map.get(criterion_id)
            return None
        except Exception as e:
            self.logger.error(f"Error finding criterion by code: {e}")
            return None

    async def search_by_description(self, issue_description: str) -> List[Dict[str, Any]]:
        """
        Search for relevant WCAG criteria based on issue description using RAG.
        
        Args:
            issue_description: Description of the accessibility issue
            
        Returns:
            List of relevant WCAG criteria
        """
        try:
            # Aufbau der Suchanfrage
            query = {
                "query": f"Find WCAG criteria relevant to this accessibility issue: {issue_description}",
                "max_results": 3  # Begrenzt die Anzahl der Ergebnisse
            }
            
            # Verwendung der query-Methode statt search
            search_results = await self.json_search.query(query)
            
            # Verarbeitung der Ergebnisse
            if isinstance(search_results, list):
                return search_results
            elif isinstance(search_results, dict):
                return [search_results]
            else:
                self.logger.warning(f"Unexpected search result format: {type(search_results)}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error searching by description: {e}")
            return []

    def get_criterion_details(self, criterion_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific WCAG criterion.
        
        Args:
            criterion_id: The WCAG criterion ID
            
        Returns:
            Dictionary containing criterion details including description,
            level, and documentation links
        """
        try:
            criterion = self.id_map.get(criterion_id, {})
            if not criterion:
                self.logger.warning(f"Criterion not found: {criterion_id}")
                return {}
                
            return {
                "id": criterion_id,
                "title": criterion.get("title", ""),
                "description": criterion.get("description", ""),
                "level": criterion.get("level", ""),
                "special_cases": criterion.get("special_cases", []),
                "documentation_links": {
                    "understanding": criterion.get("understanding_url", ""),
                    "how_to_meet": criterion.get("how_to_meet_url", "")
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting criterion details: {e}")
            return {}