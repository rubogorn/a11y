# tests/test_main.py

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import sys
import asyncio

# Füge den src-Pfad zum sys.path hinzu, um Module zu importieren
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from src.main import WCAGTestingCLI

@pytest.fixture
def cli():
    with patch('main.get_logger'):
        return WCAGTestingCLI()

class TestWCAGTestingCLI:
    def test_initialization_creates_test_content_dir(self):
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            with patch('main.get_logger'):
                cli = WCAGTestingCLI()
                mock_mkdir.assert_called_with(exist_ok=True)

    def test_is_valid_url_valid(self, cli):
        valid_urls = [
            "http://example.com",
            "https://example.org",
            "ftp://example.net",
            "http://localhost:8000"
        ]
        for url in valid_urls:
            assert cli._is_valid_url(url) is True

    def test_is_valid_url_invalid(self, cli):
        invalid_urls = [
            "example.com",
            "just_text",
            "",
            None,
            "http://"
        ]
        for url in invalid_urls:
            assert cli._is_valid_url(url) is False

    def test_get_html_files_returns_list(self, cli):
        with patch('pathlib.Path.glob') as mock_glob:
            mock_glob.return_value = [Path('test1.html'), Path('test2.html')]
            html_files = cli._get_html_files()
            assert len(html_files) == 2
            assert all(isinstance(f, Path) for f in html_files)

    def test_initialization_handles_mkdir_error(self):
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Access denied")
            with patch('builtins.exit') as mock_exit:
                with patch('main.get_logger') as mock_logger:
                    cli = WCAGTestingCLI()
                    mock_logger().error.assert_called_once()
                    mock_exit.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_tests(self, cli):
        with patch.object(cli.tools, 'analyze_url', new_callable=AsyncMock) as mock_analyze, \
             patch.object(cli.wcag_executor, 'process_results', return_value={"summary": {}}) as mock_process, \
             patch.object(cli.crew, 'run', return_value={}) as mock_crew_run, \
             patch.object(cli.report_generator, 'save_results') as mock_save:

            mock_analyze.return_value = {"normalized_results": []}

            await cli.run_tests("http://example.com")

            mock_analyze.assert_awaited_once()
            mock_process.assert_called_once()
            mock_crew_run.assert_called_once()
            mock_save.assert_called_once()

    def test_get_input_choice_url(self, cli):
        with patch('builtins.input', side_effect=['1', 'http://example.com']):
            url, html_file = cli._get_input_choice()
            assert url == 'http://example.com'
            assert html_file is None

    def test_get_input_choice_file(self, cli):
        with patch('builtins.input', side_effect=['2', '1']), \
             patch.object(cli, '_get_html_files', return_value=[Path('test1.html')]):
            url, html_file = cli._get_input_choice()
            assert url == ''
            assert html_file.name == 'test1.html'

    @pytest.mark.asyncio
    async def test_run_tests_handles_analysis_error(self, cli):
        with patch.object(cli.tools, 'analyze_url', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {"error": "Analysis failed"}
            with patch.object(cli.logger, 'error') as mock_logger_error:
                await cli.run_tests("http://example.com")
                mock_logger_error.assert_called_with("Analysis failed during run_tests")

    def test_create_file_server(self, cli):
        test_file = Path("test.html")
        with patch('http.server.HTTPServer'), \
             patch('threading.Thread'), \
             patch('socket.socket'):
            server_url = cli._create_file_server(test_file)
            assert server_url.startswith("http://localhost:")

    @pytest.mark.asyncio
    async def test_full_workflow(self, cli):
        with patch.object(cli.tools, 'analyze_url', new_callable=AsyncMock) as mock_analyze, \
             patch.object(cli.wcag_executor, 'process_results', return_value={"summary": {}}) as mock_process, \
             patch.object(cli.crew, 'run', return_value={}) as mock_crew_run, \
             patch.object(cli.report_generator, 'save_results') as mock_save:

            mock_analyze.return_value = {"normalized_results": []}

            await cli.run_tests("http://example.com")

            mock_analyze.assert_awaited_once()
            mock_process.assert_called_once()
            mock_crew_run.assert_called_once()
            mock_save.assert_called_once()

    def test_logger_initialization(self):
        with patch('main.get_logger') as mock_get_logger:
            cli = WCAGTestingCLI()
            mock_get_logger.assert_called_with('WCAGTestingCLI', log_dir='output/results/logs')
