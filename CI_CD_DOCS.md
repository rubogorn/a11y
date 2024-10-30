# CI/CD Pipeline Documentation

## Übersicht

Die CI/CD-Pipeline für das WCAG-Testing-Projekt verwendet GitHub Actions in Kombination mit Poetry für Dependency-Management. Die Pipeline besteht aus drei Hauptjobs:

1. **Test**: Ausführung der Test-Suite
2. **Lint**: Code-Qualitätsprüfungen
3. **Security**: Sicherheitsanalysen

## Voraussetzungen

- Python 3.10
- Poetry
- Node.js & npm (für Pa11y)
- Chrome/Chromium (für Browser-Tests)

## Pipeline-Konfiguration

### Trigger Events

Die Pipeline wird ausgelöst bei:
- Push zu `main` oder `develop`
- Pull Requests zu `main` oder `develop`

Nur wenn Änderungen in folgenden Pfaden vorliegen:
- `src/**`
- `tests/**`
- `pyproject.toml`
- `poetry.lock`
- `.github/workflows/**`

### Job: Test

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
```

#### Schritte:
1. Repository auschecken
2. Python 3.10 einrichten
3. Poetry installieren und konfigurieren
4. Chrome und ChromeDriver installieren
5. Pa11y installieren
6. Dependencies über Poetry installieren
7. Tests ausführen
8. Coverage-Report erstellen und hochladen

### Job: Lint

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
```

#### Werkzeuge:
- **black**: Code-Formatierung
- **isort**: Import-Sortierung
- **flake8**: Style Guide Enforcement
- **mypy**: Statische Typ-Überprüfung

### Job: Security

```yaml
jobs:
  security:
    runs-on: ubuntu-latest
```

#### Werkzeuge:
- **bandit**: Python-Security-Linter
- **safety**: Dependency-Sicherheitsprüfung

## Poetry-Konfiguration

### Virtuelle Umgebung

Poetry wird so konfiguriert, dass die virtuelle Umgebung im Projektverzeichnis erstellt wird:
```bash
poetry config virtualenvs.create true
poetry config virtualenvs.in-project true
```

### Caching

Die virtuelle Umgebung wird gecacht um die Build-Zeit zu reduzieren:
```yaml
- name: Cache Poetry virtualenv
  uses: actions/cache@v3
  with:
    path: ./.venv
    key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}
```

## Tool-Konfigurationen

### Pytest

```toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=xml --cov-report=html"
testpaths = ["tests"]
asyncio_mode = "auto"
```

### Black

```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'
```

### isort

```toml
[tool.isort]
profile = "black"
multi_line_output = 3
```

### mypy

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
disallow_untyped_defs = true
```

## Lokale Entwicklung

### Setup

1. Repository klonen:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Poetry installieren:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Dependencies installieren:
```bash
poetry install
```

### Tests ausführen

```bash
poetry run pytest
```

### Linting

```bash
poetry run black src tests
poetry run isort src tests
poetry run flake8 src tests
poetry run mypy src tests
```

### Security Checks

```bash
poetry run bandit -r src/
poetry run safety check
```

## Continuous Integration

### Test-Coverage

Die Pipeline generiert Coverage-Reports in zwei Formaten:
- XML für Codecov
- HTML für lokale Inspektion

Coverage-Reports werden als Artefakte gespeichert und können nach dem Build heruntergeladen werden.

### Fehlschläge

Bei Fehlschlägen der Pipeline:
1. Überprüfen Sie die Job-Logs in GitHub Actions
2. Stellen Sie sicher, dass alle Tests lokal erfolgreich sind
3. Überprüfen Sie die Linting-Ausgabe
4. Beheben Sie Sicherheitsprobleme, die von bandit oder safety gemeldet werden

## Best Practices

1. **Dependencies**:
   - Regelmäßig `poetry update` ausführen
   - Dependencies in pyproject.toml auf aktuellem Stand halten

2. **Tests**:
   - Neue Features mit Tests abdecken
   - Coverage über 80% halten

3. **Code-Qualität**:
   - Code vor Commit formatieren
   - Typen-Annotationen verwenden
   - Linting-Fehler beheben

4. **Sicherheit**:
   - Sicherheitswarnungen zeitnah beheben
   - Dependencies regelmäßig auf Schwachstellen prüfen

## Fehlerbehandlung

### Häufige Probleme

1. **Poetry Lock-Konflikte**:
```bash
poetry lock --no-update
git add poetry.lock
git commit -m "Update poetry.lock"
```

2. **Coverage-Fehler**:
```bash
poetry run pytest --cov=src --cov-report=term-missing
```

3. **Linting-Fehler**:
```bash
poetry run black src tests --diff
poetry run isort src tests --diff
```

## Support

Bei Fragen oder Problemen:
1. GitHub Issues überprüfen
2. Pipeline-Logs analysieren
3. Team-Mitglieder kontaktieren