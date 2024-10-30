# WCAG 2.2 Testing System

A comprehensive WCAG 2.2 testing system built with CrewAI that integrates multiple accessibility testing tools.

## Features

- Full WCAG 2.2 compliance testing
- Multiple testing tools integration:
  - HTML Structure Analysis
  - Pa11y
  - Axe Core
  - Lighthouse
- Comprehensive reporting in multiple formats
- AI-powered remediation suggestions
- Modular and extensible architecture

## Prerequisites

- Python 3.10 or higher
- Node.js and npm (for Pa11y and Lighthouse)
- Chrome/Chromium browser

### Install Required Node.js Tools

```bash
# Install Pa11y globally
npm install -g pa11y

# Install Lighthouse globally
npm install -g lighthouse
```

## Installation

```bash
# Create and activate virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install with poetry
poetry install

# Install Playwright browsers
playwright install
```

## Project Structure

```
a11y-wcag-testing/
├── README.md
├── pyproject.toml
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── agents.yaml
│   │   └── tasks.yaml
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── wcag_tools.py
│   │   ├── wcag_analyzers.py
│   │   └── result_processor.py
│   ├── crew.py
│   └── main.py
└── tests/
    └── __init__.py
```

## Usage

### Basic Usage

```bash
python -m src.main https://example.com --output reports --format json md
```

### Tool Output

The system generates detailed reports including:
- HTML structure and ARIA usage analysis
- WCAG 2.2 compliance issues
- Accessibility violations from multiple tools
- Combined and normalized results
- Summary statistics

Results are saved in the specified output directory with:
- Individual tool results
- Combined analysis
- Summary reports
- Timestamp-based file naming

## Required Environment Variables

```bash
OPENAI_API_KEY=your_openai_api_key
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT

## Dependencies

- crewai: AI agent orchestration
- beautifulsoup4: HTML parsing and analysis
- playwright: Browser automation
- aiofiles: Asynchronous file operations
- selenium: Web browser automation
- requests: HTTP requests
- Pa11y (Node.js): Accessibility testing
- Lighthouse (Node.js): Performance and accessibility auditing