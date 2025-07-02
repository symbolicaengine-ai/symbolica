"""
symbolica.compiler.base
======================

Base classes for the Symbolica compiler architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Union
import pathlib
from dataclasses import dataclass, field

from .parser import RawRule


@dataclass
class CompilationContext:
    """Context passed through compilation pipeline."""
    rules_dir: pathlib.Path
    output_path: pathlib.Path
    options: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass 
class CompilationResult:
    """Result of compilation process."""
    success: bool
    rule_count: int
    output_path: Optional[pathlib.Path] = None
    file_size: Optional[int] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class CompilerStage(ABC):
    """Base class for compiler pipeline stages."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def process(self, context: CompilationContext) -> bool:
        """
        Process this compilation stage.
        
        Args:
            context: Compilation context with rules, options, etc.
            
        Returns:
            True if stage succeeded, False if failed
        """
        pass
    
    def add_error(self, context: CompilationContext, message: str) -> None:
        """Add error to compilation context."""
        context.errors.append(f"{self.name}: {message}")
    
    def add_warning(self, context: CompilationContext, message: str) -> None:
        """Add warning to compilation context.""" 
        context.warnings.append(f"{self.name}: {message}")


class RuleProcessor(Protocol):
    """Protocol for objects that can process rules."""
    
    def process_rules(self, rules: List[RawRule], context: CompilationContext) -> List[RawRule]:
        """Process a list of rules and return modified rules."""
        ...


class Compiler:
    """Main compiler orchestrator."""
    
    def __init__(self):
        self.stages: List[CompilerStage] = []
        self.rule_processors: List[RuleProcessor] = []
    
    def add_stage(self, stage: CompilerStage) -> 'Compiler':
        """Add a compilation stage."""
        self.stages.append(stage)
        return self
    
    def add_rule_processor(self, processor: RuleProcessor) -> 'Compiler':
        """Add a rule processor."""
        self.rule_processors.append(processor)
        return self
    
    def compile(self, 
                rules_dir: Union[str, pathlib.Path],
                output_path: Union[str, pathlib.Path],
                **options) -> CompilationResult:
        """
        Run the full compilation pipeline.
        
        Args:
            rules_dir: Directory containing rule files
            output_path: Output .rpack file path
            **options: Compilation options
            
        Returns:
            CompilationResult with success status and details
        """
        context = CompilationContext(
            rules_dir=pathlib.Path(rules_dir),
            output_path=pathlib.Path(output_path),
            options=options
        )
        
        # Run all stages
        for stage in self.stages:
            try:
                success = stage.process(context)
                if not success:
                    return CompilationResult(
                        success=False,
                        rule_count=0,
                        errors=context.errors,
                        warnings=context.warnings
                    )
            except Exception as e:
                context.errors.append(f"{stage.name}: Unexpected error: {e}")
                return CompilationResult(
                    success=False,
                    rule_count=0,
                    errors=context.errors,
                    warnings=context.warnings
                )
        
        # Create result
        return CompilationResult(
            success=len(context.errors) == 0,
            rule_count=context.stats.get('rule_count', 0),
            output_path=context.output_path if context.output_path.exists() else None,
            file_size=context.output_path.stat().st_size if context.output_path.exists() else None,
            errors=context.errors,
            warnings=context.warnings,
            stats=context.stats
        ) 