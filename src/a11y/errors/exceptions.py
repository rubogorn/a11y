# src/errors/exceptions.py

class ReportGenerationError(Exception):
    """Basisklasse für Report-Generierungsfehler"""
    pass

class TemplateError(ReportGenerationError):
    """Fehler bei der Template-Verarbeitung"""
    pass

class DataValidationError(ReportGenerationError):
    """Fehler bei der Datenvalidierung"""
    pass