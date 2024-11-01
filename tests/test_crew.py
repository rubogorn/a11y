# tests/test_crew.py

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Importiere die zu testende Klasse
from src.crew import WCAGTestingCrew

class TestWCAGTestingCrew:
    @pytest.fixture
    def crew(self):
        return WCAGTestingCrew()

    def test_run_success(self, crew):
        # Mocke die Abhängigkeiten
        with patch.object(crew, '_serialize_results', return_value={'serialized': 'results'}) as mock_serialize, \
             patch.object(crew, 'save_results') as mock_save:
            # Simuliere erfolgreiche Ergebnisse
            results = {'some': 'results'}
            context = {'use_accessibility_analyzer': True}

            # Rufe die Methode auf
            serialized_results = crew.run(results, context)

            # Überprüfe die Aufrufe und Ergebnisse
            mock_serialize.assert_called_once_with(results)
            mock_save.assert_called_once_with({'serialized': 'results', 'accessibility_analyzer_used': True})
            assert serialized_results == {'serialized': 'results', 'accessibility_analyzer_used': True}

    def test_run_execution_error(self, crew):
        # Mocke die Abhängigkeiten
        with patch.object(crew, '_serialize_results', side_effect=Exception('Serialization failed')) as mock_serialize, \
             patch.object(crew.logger, 'error') as mock_logger_error:
            # Simuliere Ergebnisse und Kontext
            results = {'some': 'results'}
            context = {}

            # Rufe die Methode auf
            serialized_results = crew.run(results, context)

            # Überprüfe die Aufrufe und Ergebnisse
            mock_serialize.assert_called_once_with(results)
            mock_logger_error.assert_called_once()
            assert serialized_results['status'] == 'error'
            assert 'Serialization failed' in serialized_results['message']
            assert 'timestamp' in serialized_results

    def test_run_outer_exception(self, crew):
        # Mocke die Methode, um eine Ausnahme zu werfen
        with patch.object(crew, 'save_results', side_effect=Exception('Save failed')) as mock_save, \
             patch.object(crew.logger, 'error') as mock_logger_error:
            # Simuliere Ergebnisse und Kontext
            results = {'some': 'results'}
            context = {}

            # Rufe die Methode auf
            serialized_results = crew.run(results, context)

            # Überprüfe die Aufrufe und Ergebnisse
            mock_save.assert_called_once()
            mock_logger_error.assert_called_once()
            assert serialized_results['status'] == 'failed'
            assert 'Save failed' in serialized_results['error']
            assert 'timestamp' in serialized_results
