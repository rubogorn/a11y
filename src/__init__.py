# src/__init__.py
from .crew import WCAGTestingCrew
from .wcag.unified_result_processor import UnifiedResultProcessor
from .wcag.wcag_integration_manager import WCAGIntegrationManager

__version__ = "0.1.0"

__all__ = [
    'WCAGTestingCrew',
    'UnifiedResultProcessor',
    'WCAGIntegrationManager'
]