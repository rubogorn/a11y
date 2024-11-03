from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class Pa11yConfig:
    """Pa11y configuration options with WCAG 2.2 defaults"""
    
    # WCAG Testing Standards
    standard: str = "WCAG2AA"
    runners: List[str] = field(default_factory=lambda: ["htmlcs", "axe"])
    
    # Test Level Configuration
    level: str = "error"
    threshold: int = 0
    include_notices: bool = False
    include_warnings: bool = False
    
    # Element Selection
    root_element: Optional[str] = None
    hide_elements: Optional[str] = None
    ignore: List[str] = field(default_factory=list)
    
    # Timing Configuration
    timeout: int = 60000  # 60 seconds
    wait: int = 1000     # 1 second
    
    # Browser Configuration
    viewport: Dict[str, Any] = field(default_factory=lambda: {
        "width": 1280,
        "height": 1024,
        "deviceScaleFactor": 1,
        "isMobile": False
    })
    
    # Actions and Interactions
    actions: List[str] = field(default_factory=list)
    
    # Output Configuration
    debug: bool = False
    screen_capture: Optional[str] = None
    reporters: List[str] = field(default_factory=lambda: ["json"])

    def to_command_args(self) -> List[str]:
        """Convert configuration to Pa11y command line arguments"""
        args = []
        
        # Add runners
        for runner in self.runners:
            args.extend(["--runner", runner])
        
        # Add standards and levels
        args.extend([
            "--standard", self.standard,
            "--level", self.level
        ])
        
        # Add threshold if specified
        if self.threshold > 0:
            args.extend(["--threshold", str(self.threshold)])
        
        # Add timing configurations
        args.extend([
            "--timeout", str(self.timeout),
            "--wait", str(self.wait)
        ])
        
        # Add element selections
        if self.root_element:
            args.extend(["--root-element", self.root_element])
        if self.hide_elements:
            args.extend(["--hide-elements", self.hide_elements])
        
        # Add ignore rules
        for rule in self.ignore:
            args.extend(["--ignore", rule])
        
        # Add feature flags
        if self.debug:
            args.append("--debug")
        if self.include_notices:
            args.append("--include-notices")
        if self.include_warnings:
            args.append("--include-warnings")
        
        # Add screen capture if specified
        if self.screen_capture:
            args.extend(["--screen-capture", self.screen_capture])
        
        # Add reporters
        for reporter in self.reporters:
            args.extend(["--reporter", reporter])
        
        return args

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format"""
        return {
            "standard": self.standard,
            "runners": self.runners,
            "level": self.level,
            "threshold": self.threshold,
            "timing": {
                "timeout": self.timeout,
                "wait": self.wait
            },
            "elements": {
                "root": self.root_element,
                "hidden": self.hide_elements,
                "ignored": self.ignore
            },
            "viewport": self.viewport,
            "actions": self.actions,
            "output": {
                "debug": self.debug,
                "screen_capture": self.screen_capture,
                "reporters": self.reporters,
                "notices": self.include_notices,
                "warnings": self.include_warnings
            }
        }