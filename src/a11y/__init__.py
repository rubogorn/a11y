# src/__init__.py
from .crew import WCAGTestingCrew
from .wcag import UnifiedResultProcessor, WCAGIntegrationManager

__version__ = "0.1.0"

__all__ = [
    'WCAGTestingCrew',
    'UnifiedResultProcessor',
    'WCAGIntegrationManager'
]