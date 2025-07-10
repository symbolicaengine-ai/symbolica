"""
Schema Documentation Generator
==============================

Focused generator for schema documentation.
Extracted from SchemaValidator to follow Single Responsibility Principle.
"""

from .schema_constants import SchemaConstants
from ..config.system_config import SystemConfig


class SchemaDocumentationGenerator:
    """Generates human-readable schema documentation."""
    
    def __init__(self):
        """Initialize documentation generator with schema constants."""
        self._constants = SchemaConstants()
    
    def generate_schema_documentation(self) -> str:
        """Generate human-readable schema documentation.
        
        Returns:
            Formatted schema documentation
        """
        doc = []
        doc.append("Symbolica YAML Schema")
        doc.append("=" * 21)
        doc.append("")
        
        doc.append("Top-level Structure:")
        doc.append("-------------------")
        doc.append("rules: []           # Required: List of rules")
        doc.append("version: \"1.0\"       # Optional: Schema version")
        doc.append("description: \"...\"   # Optional: File description")
        doc.append("metadata: {}        # Optional: Additional metadata")
        doc.append("")
        
        doc.append("Rule Structure:")
        doc.append("---------------")
        doc.append("- id: \"rule_name\"     # Required: Unique identifier")
        doc.append("  priority: 100       # Optional: Execution priority (integer)")
        doc.append("  condition: \"...\"    # Required: String or structured dict")
        doc.append("  facts: {}           # Optional: Intermediate state (dict)")
        doc.append("  actions: {}         # Required: Final outputs (dict)")
        doc.append("  triggers: []        # Optional: Rules to trigger (list)")
        doc.append("  tags: []            # Optional: Metadata tags (list)")
        doc.append("  description: \"...\"  # Optional: Rule description")
        doc.append("  enabled: true       # Optional: Enable/disable flag")
        doc.append("")
        
        doc.append("Reserved Keywords:")
        doc.append("-" * 17)
        doc.append("The following keywords are reserved and cannot be used")
        doc.append("as rule IDs, fact names, or action names:")
        doc.append("")
        
        # Group reserved keywords by category
        keywords = sorted(self._constants.SYSTEM_RESERVED_KEYWORDS)
        doc.append("(Sample of reserved keywords - total: {})".format(len(keywords)))
        doc.append("")
        
        # Show sample keywords using system configuration
        sample_count = SystemConfig.SAMPLE_KEYWORDS_COUNT
        keywords_per_line = SystemConfig.KEYWORDS_PER_DOC_LINE
        
        for i, keyword in enumerate(keywords[:sample_count]):
            if i % keywords_per_line == 0:
                doc.append("")
            if i % keywords_per_line == 0:
                line = f"  {keyword:<15}"
            else:
                line += f"{keyword:<15}"
            
            if (i + 1) % keywords_per_line == 0 or i == len(keywords[:sample_count]) - 1:
                doc.append(line)
        
        doc.append("")
        doc.append("... and {} more keywords".format(len(keywords) - sample_count))
        
        return "\n".join(doc) 