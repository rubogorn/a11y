import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from crewai_tools import JSONSearchTool
from src.logging_config import get_logger
import ipdb

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
                        "model": "gpt-4o-mini"
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
            
            # Detaillierte Ausgabe des JSON-Inhalts
            self.logger.info("WCAG reference data loaded successfully:")
            self.logger.info(f"File path: {self.wcag_json_path}")
            #self.logger.info("Content:")
            #for criterion in self.wcag_data:
            #    self.logger.info(json.dumps(criterion, indent=2, ensure_ascii=False))
                
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
        """Find WCAG criterion by tool-specific code."""
        print("=" * 80 + "\n")
        print("🔍 FIND CRITERION BY CODE")
        self.logger.info(f"Input:\n  code: '{code}'\n")
        self.logger.info(f"LLM Query:\n  Looking up criterion with code: {code}\n")

        try:
            #ipdb.set_trace(code)
            criterion_id = self.code_map.get(code.lower())
            if criterion_id:
                result = self.id_map.get(criterion_id)
                print("✅ Result:")
                self.logger.info(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
                return result
                
            self.logger.info("❌ No criterion found\n")
            return None
            
        except Exception as e:
            self.logger.error(f"💥 Error: {str(e)}\n")
            return None
        finally:
            print("=" * 80 + "\n\n")

    async def search_by_description(self, issue_description: str) -> List[Dict[str, Any]]:
        """Search for relevant WCAG criteria based on issue description using RAG."""
        print("\n" + "=" * 80 + "\n")
        self.logger.info("🔎 SEARCH BY DESCRIPTION")
        self.logger.info(f"Input:\n  description: '{issue_description}'\n")

        try:
            search_query = f"Find WCAG criteria relevant to this accessibility issue: {issue_description}"
            self.logger.info(f"LLM Query:\n  {search_query}\n")
            
            # Die korrekte Methode ist "rag_search" statt "search"
            search_results = await self.json_search.rag_search(
                search_query=search_query
            )
            self.logger.info("🤖 Raw LLM Response:")
            self.logger.info(json.dumps(search_results, indent=2, ensure_ascii=False) + "\n")
            
            self.logger.info("-" * 40 + "\n")
            self.logger.info("✅ Processed Results:")
            
            if isinstance(search_results, list):
                self.logger.info(f"Found {len(search_results)} matching criteria:")
                self.logger.info(json.dumps(search_results, indent=2, ensure_ascii=False) + "\n")
                return search_results
            elif isinstance(search_results, dict):
                self.logger.info("Found single criterion:")
                self.logger.info(json.dumps(search_results, indent=2, ensure_ascii=False) + "\n")
                return [search_results]
            else:
                self.logger.warning("❌ No matching criteria found\n")
                return []
                
        except Exception as e:
            self.logger.error(f"💥 Error: {str(e)}\n")
            return []
        finally:
            print("=" * 80 + "\n\n")

    def get_criterion_details(self, criterion_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific WCAG criterion."""
        print("\n" + "=" * 80 + "\n")
        self.logger.info("📋 GET CRITERION DETAILS")
        self.logger.info(f"Input:  criterion_id: '{criterion_id}'\n")
        self.logger.info(f"LLM Query:\n  Retrieving details for criterion: {criterion_id}\n")

        try:
            criterion = self.id_map.get(criterion_id, {})
            if not criterion:
                print("-" * 40 + "\n")
                self.logger.warning(f"❌ Criterion not found: {criterion_id}\n")
                return {}
            
            result = {
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
            
            print("-" * 40 + "\n")
            self.logger.info("✅ Result:")
            self.logger.info(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
            return result
            
        except Exception as e:
            self.logger.error(f"💥 Error: {str(e)}\n")
            return {}
        finally:
            print("=" * 80 + "\n\n")