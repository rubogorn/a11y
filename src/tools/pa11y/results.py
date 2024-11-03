from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

@dataclass
class Pa11yIssue:
    """Represents a single Pa11y issue"""
    code: str
    message: str
    type: str
    selector: Optional[str] = None
    context: Optional[str] = None
    runner: str = "htmlcs"
    impact: Optional[str] = None
    wcag_level: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pa11yIssue':
        """Create issue from Pa11y result dictionary"""
        return cls(
            code=data.get("code", "unknown"),
            message=data.get("message", ""),
            type=data.get("type", "error"),
            selector=data.get("selector"),
            context=data.get("context"),
            runner=data.get("runner", "htmlcs"),
            impact=data.get("impact"),
            wcag_level=data.get("wcagLevel")
        )

@dataclass
class Pa11yResult:
    """Represents Pa11y analysis results"""
    status: str
    url: str
    timestamp: str
    issues: List[Pa11yIssue]
    artifacts: Dict[str, str]
    config: Dict[str, Any]
    issues_found: bool = False
    error_message: Optional[str] = None
    
    @classmethod
    def create_error(cls, url: str, message: str) -> 'Pa11yResult':
        """Create error result"""
        return cls(
            status="error",
            url=url,
            timestamp=datetime.now(timezone.utc).isoformat(),
            issues=[],
            artifacts={},
            config={},
            error_message=message
        )
    
    @classmethod
    def from_pa11y_output(cls, url: str, output: Dict[str, Any], 
                         artifacts: Dict[str, str], config: Dict[str, Any]) -> 'Pa11yResult':
        """Create result from Pa11y output"""
        issues = []
        if isinstance(output, list):
            issues = [Pa11yIssue.from_dict(issue) for issue in output]
        elif isinstance(output, dict) and "issues" in output:
            issues = [Pa11yIssue.from_dict(issue) for issue in output["issues"]]
        
        return cls(
            status="success",
            url=url,
            timestamp=datetime.now(timezone.utc).isoformat(),
            issues=issues,
            artifacts=artifacts,
            config=config,
            issues_found=bool(issues)
        )
    
    def get_issue_summary(self) -> Dict[str, int]:
        """Get summary of issues by type"""
        summary = {"error": 0, "warning": 0, "notice": 0}
        for issue in self.issues:
            if issue.type in summary:
                summary[issue.type] += 1
        return summary
    
    def get_wcag_summary(self) -> Dict[str, int]:
        """Get summary of issues by WCAG level"""
        summary = {"A": 0, "AA": 0, "AAA": 0}
        for issue in self.issues:
            if issue.wcag_level in summary:
                summary[issue.wcag_level] += 1
        return summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format"""
        return {
            "status": self.status,
            "url": self.url,
            "timestamp": self.timestamp,
            "issues_found": self.issues_found,
            "error_message": self.error_message,
            "tool": "pa11y",
            "issues": [
                {
                    "code": issue.code,
                    "message": issue.message,
                    "type": issue.type,
                    "selector": issue.selector,
                    "context": issue.context,
                    "runner": issue.runner,
                    "impact": issue.impact,
                    "wcag_level": issue.wcag_level
                }
                for issue in self.issues
            ],
            "artifacts": self.artifacts,
            "config": self.config,
            "summary": {
                "by_type": self.get_issue_summary(),
                "by_wcag": self.get_wcag_summary()
            }
        }