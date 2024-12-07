import os
import shutil
import socket
import tempfile
import threading
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import List, Optional, Tuple
import subprocess
import sys
import logging
from .logging_config import get_logger

logger = get_logger('utils')

def log_directory_contents(logger: logging.Logger, directory: Path) -> None:
    """Log the contents of a directory recursively
    
    Args:
        logger: Logger instance to use
        directory: Path to the directory to log
    """
    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return
        
    logger.info(f"Contents of {directory}:")
    for path in sorted(directory.rglob("*")):
        try:
            relative_path = path.relative_to(directory)
            if path.is_file():
                size = path.stat().st_size
                logger.info(f"  File: {relative_path} ({size} bytes)")
            else:
                logger.info(f"  Dir:  {relative_path}/")
        except Exception as e:
            logger.error(f"Error accessing {path}: {e}")

def _check_chromedriver_version() -> None:
    """Check if ChromeDriver is installed and matches Chrome version"""
    try:
        # Check if ChromeDriver is installed via Homebrew
        result = subprocess.run(['brew', 'list', 'chromedriver'], capture_output=True, text=True)
        if result.returncode != 0:
            print("Warning: ChromeDriver not found in Homebrew. To install:")
            print("brew install chromedriver")
            logger.warning("ChromeDriver not found in Homebrew")
    except Exception as e:
        print(f"Unable to check Chrome/ChromeDriver versions: {e}")
        logger.error(f"Error checking ChromeDriver: {e}")

def _is_valid_url(url: str) -> bool:
    """Validate if string is a valid URL"""
    try:
        result = urllib.parse.urlparse(url)
        valid = all([result.scheme, result.netloc])
        if not valid:
            logger.warning(f"Invalid URL: {url}")
        return valid
    except ValueError:
        logger.warning(f"Invalid URL format: {url}")
        return False

def _get_input_choice(prompt: str, valid_choices: List[str]) -> str:
    """Get user input with validation"""
    while True:
        choice = input(prompt).strip().lower()
        if choice in valid_choices:
            logger.info(f"User selected option: {choice}")
            return choice
        logger.warning(f"Invalid choice entered: {choice}")
        print(f"Invalid choice. Please enter one of: {', '.join(valid_choices)}")

def _create_file_server(html_file: str) -> Tuple[str, HTTPServer]:
    """Create temporary server for local HTML file"""
    logger.info(f"Setting up temporary server for {html_file}")

    # Find an available port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        port = s.getsockname()[1]

    # Create temporary directory and copy file
    temp_dir = Path(tempfile.mkdtemp())
    temp_file = temp_dir / "index.html"
    shutil.copy2(html_file, temp_file)
    logger.debug(f"Temporary file created at {temp_file}")

    # Configure and start server
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(temp_dir), **kwargs)

    server = HTTPServer(('localhost', port), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    server_url = f"http://localhost:{port}"
    logger.info(f"Local server started at {server_url}")
    return server_url, server

def _get_html_files(test_content_path: Path) -> List[Path]:
    """Get list of HTML files in test-content directory"""
    html_files = list(test_content_path.glob("*.html"))
    logger.info(f"Found {len(html_files)} HTML files in test-content directory")
    return html_files

def _get_user_input(test_content_path: Path) -> Tuple[str, Optional[Path], Optional[HTTPServer]]:
    """Get user input for testing source"""
    server = None
    
    while True:
        print("\nWCAG 2.2 Testing Tool")
        print("====================")
        print("1. Test URL")
        print("2. Test local HTML file")
        print("q. Quit")
        
        choice = _get_input_choice("Please select an option: ", ['1', '2', 'q'])
        
        if choice == 'q':
            logger.info("User chose to quit")
            sys.exit(0)
            
        elif choice == '1':
            url = input("Enter URL to test (press Enter for default): ").strip()
            if not url:
                url = "https://magicofnow.com"
                logger.info("Using default URL")
            if _is_valid_url(url):
                logger.info(f"User selected URL: {url}")
                return url, None, None
            print("Invalid URL format. Please try again.")
            
        elif choice == '2':
            logger.info("User selected local HTML file testing")
            html_files = _get_html_files(test_content_path)
            if not html_files:
                logger.warning("No HTML files found in test-content directory")
                print("No HTML files found in test-content directory.")
                print("Please add HTML files to test-content/ and try again.")
                continue
                
            print("\nAvailable HTML files:")
            for i, file in enumerate(html_files, 1):
                print(f"{i}. {file.name}")
                
            try:
                file_choice = int(input("\nSelect file number: ").strip())
                if 1 <= file_choice <= len(html_files):
                    selected_file = html_files[file_choice - 1]
                    logger.info(f"User selected file: {selected_file}")
                    url, server = _create_file_server(str(selected_file))
                    return url, selected_file, server
                logger.warning(f"Invalid file number selected: {file_choice}")
                print("Invalid file number. Please try again.")
            except ValueError:
                logger.warning("Invalid input: not a number")
                print("Invalid input. Please enter a number.")

def _cleanup_logs(initial_cleanup: bool = False) -> None:
    """Clean up output directories
    
    Args:
        initial_cleanup: If True, don't use logging (for initial cleanup before logging is initialized)
    """
    if not initial_cleanup:
        logger = get_logger('cleanup')
        
    cleanup_dirs = {
        "logs": Path("output/logs"),
        "results": Path("output/results"),
        "tool_results": Path("output/tool_results")
    }
    
    file_counts = {}
    total_files = 0
    
    for dir_name, dir_path in cleanup_dirs.items():
        if not dir_path.exists():
            continue
        
        files = list(dir_path.rglob("*"))
        files = [f for f in files if f.is_file()]
        file_counts[dir_name] = files
        total_files += len(files)
    
    if total_files == 0:
        if not initial_cleanup:
            logger.info("No files to clean up")
        return

    if not initial_cleanup:
        logger.info(f"Found {total_files} files in output directories")
    print("\nOutput Directory Cleanup")
    print("=======================")
    print("Found files in:")
    for dir_name, files in file_counts.items():
        if files:
            print(f"- {dir_name}: {len(files)} files")
    
    while True:
        response = input("\nDo you want to delete all output files? (y/n): ").strip().lower()
        if response == 'y':
            try:
                deleted_count = 0
                for dir_name, files in file_counts.items():
                    for file in files:
                        try:
                            file.unlink()
                            deleted_count += 1
                        except Exception as e:
                            if not initial_cleanup:
                                logger.error(f"Error deleting {file}: {e}")
                            print(f"Error deleting {file}: {e}")
                    
                    # Remove empty directories
                    try:
                        for dir_path in sorted(cleanup_dirs[dir_name].rglob("*"), reverse=True):
                            if dir_path.is_dir():
                                dir_path.rmdir()
                    except Exception as e:
                        if not initial_cleanup:
                            logger.error(f"Error removing directory {dir_path}: {e}")
                        print(f"Error removing directory {dir_path}: {e}")
                
                if not initial_cleanup:
                    logger.info(f"Deleted {deleted_count} files")
                print(f"Successfully deleted {deleted_count} files")
                
                # Recreate directories
                for dir_path in cleanup_dirs.values():
                    dir_path.mkdir(parents=True, exist_ok=True)
                
            except Exception as e:
                if not initial_cleanup:
                    logger.error(f"Error during cleanup: {e}")
                print(f"Error during cleanup: {e}")
            break
        elif response == 'n':
            if not initial_cleanup:
                logger.info("User chose not to clean up files")
            break
        else:
            print("Please enter 'y' for yes or 'n' for no.") 

def initialize_environment() -> None:
    """Initialize the application environment
    
    This function:
    1. Runs the initial cleanup (before logging is initialized)
    2. Creates necessary directories with proper structure
    """
    # Run cleanup first, before logging is initialized
    _cleanup_logs(initial_cleanup=True)
    
    # Create necessary directories with full structure
    dirs = [
        'output/logs',
        'output/results',
        'output/results/evidence',
        'output/results/evidence/screenshots',
        'output/results/evidence/code-snippets',
        'output/results/evidence/tool-output',
        'output/results/matrices',
        'output/results/action-plan',
        'output/tool_results',
        'test-content'
    ]
    
    for dir_path in dirs:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        
    logger.info("Application environment initialized with all required directories") 