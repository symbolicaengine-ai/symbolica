"""
Rule Visualizer - Main Interface
================================

Unified interface for visualizing rule structure, dependencies, and execution order.
"""

import json
import sys
import os
from typing import Dict, List, Any, Optional

# Add symbolica to path if running from visualization directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .ast_visualizer import ASTVisualizer
from .dag_visualizer import DAGVisualizer


class RuleVisualizer:
    """Main interface for rule visualization and analysis."""
    
    def __init__(self, engine_or_rules):
        """Initialize with either an Engine instance or list of rules."""
        if hasattr(engine_or_rules, 'rules'):
            # Engine instance
            self.engine = engine_or_rules
            self.rules = engine_or_rules.rules
        else:
            # List of rules
            self.engine = None
            self.rules = engine_or_rules
        
        self.ast_viz = ASTVisualizer(self.rules)
        self.dag_viz = DAGVisualizer(self.rules)
    
    def show_ast(self, rule_id: Optional[str] = None) -> None:
        """Show AST visualization for a specific rule or all rules."""
        if rule_id:
            self.ast_viz.print_rule_ast(rule_id)
        else:
            self.ast_viz.print_all_asts()
    
    def show_dag(self) -> None:
        """Show DAG visualization of rule dependencies."""
        self.dag_viz.print_execution_order()
        self.dag_viz.print_dependency_graph()
        self.dag_viz.print_critical_path()
        self.dag_viz.print_stats()
    
    def analyze_rule(self, rule_id: str) -> Dict[str, Any]:
        """Detailed analysis of a specific rule."""
        rule = next((r for r in self.rules if r.id == rule_id), None)
        if not rule:
            return {'error': f'Rule {rule_id} not found'}
        
        ast_tree = self.ast_viz.get_ast_tree(rule_id)
        dep_graph = self.dag_viz.get_dependency_graph()
        
        return {
            'rule': {
                'id': rule.id,
                'priority': rule.priority,
                'condition': rule.condition,
                'actions': rule.actions,
                'tags': getattr(rule, 'tags', [])
            },
            'ast': ast_tree,
            'dependencies': dep_graph.get(rule_id, {}),
            'condition_fields': list(self.dag_viz._extract_fields_from_condition(rule.condition)),
            'action_fields': list(self.dag_viz._extract_fields_from_actions(rule.actions))
        }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution order and dependencies."""
        stats = self.dag_viz.get_stats()
        execution_order = self.dag_viz.execution_order
        critical_path = self.dag_viz.get_critical_path()
        
        return {
            'statistics': stats,
            'execution_levels': execution_order,
            'critical_path': critical_path,
            'parallelization_opportunities': [
                {'level': i, 'parallel_rules': len(rules), 'rules': rules}
                for i, rules in enumerate(execution_order)
                if len(rules) > 1
            ]
        }
    
    def generate_report(self, filename: str = 'rule_analysis.html') -> None:
        """Generate comprehensive HTML report."""
        html_content = self._generate_html_report()
        
        with open(filename, 'w') as f:
            f.write(html_content)
        
        print(f"Analysis report saved to: {filename}")
    
    def _generate_html_report(self) -> str:
        """Generate HTML report content."""
        execution_summary = self.get_execution_summary()
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Symbolica Rule Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #333; }}
        .summary {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .rule-card {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; background-color: #fafafa; }}
        .execution-level {{ background-color: #f0f8ff; padding: 10px; margin: 5px 0; border-left: 4px solid #007acc; }}
        .dependency {{ color: #666; font-style: italic; }}
        .ast-tree {{ background-color: #f9f9f9; border: 1px solid #ddd; padding: 10px; font-family: monospace; white-space: pre-wrap; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #007acc; }}
        .critical-path {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; }}
        .graphviz-note {{ background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Symbolica Rule Analysis Report</h1>
        
        <div class="summary">
            <h2>Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{execution_summary['statistics']['total_rules']}</div>
                    <div>Total Rules</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{execution_summary['statistics']['execution_levels']}</div>
                    <div>Execution Levels</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{execution_summary['statistics']['total_dependencies']}</div>
                    <div>Dependencies</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{execution_summary['statistics']['parallelization_potential']:.1f}</div>
                    <div>Avg Rules/Level</div>
                </div>
            </div>
        </div>
        
        <h2>Execution Order</h2>
        {self._generate_execution_order_html(execution_summary['execution_levels'])}
        
        <h2>Critical Path Analysis</h2>
        <div class="critical-path">
            {self._generate_critical_path_html(execution_summary['critical_path'])}
        </div>
        
        <h2>Rule Details</h2>
        {self._generate_rule_details_html()}
        
        <h2>Dependency Graph</h2>
        <div class="graphviz-note">
            <strong>Graphviz Visualization:</strong> To generate a visual dependency graph, save the following DOT content 
            to a .dot file and render with: <code>dot -Tpng filename.dot -o graph.png</code>
            <pre style="margin-top: 10px; background-color: white; padding: 10px; border: 1px solid #ddd;">{self.dag_viz.to_graphviz()}</pre>
        </div>
        
        <h2>Parallelization Opportunities</h2>
        {self._generate_parallelization_html(execution_summary['parallelization_opportunities'])}
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; text-align: center;">
            Generated by Symbolica Rule Visualizer
        </div>
    </div>
</body>
</html>"""
        return html
    
    def _generate_execution_order_html(self, execution_levels: List[List[str]]) -> str:
        """Generate HTML for execution order section."""
        html = ""
        for level, rules in enumerate(execution_levels):
            html += f'<div class="execution-level">'
            html += f'<h3>Level {level}</h3>'
            for rule_id in rules:
                rule = next(r for r in self.rules if r.id == rule_id)
                deps = self.dag_viz.dependencies.get(rule_id, set())
                deps_str = f" (depends on: {', '.join(sorted(deps))})" if deps else ""
                html += f'<div>• {rule_id} [priority: {rule.priority}]{deps_str}</div>'
            html += '</div>'
        return html
    
    def _generate_critical_path_html(self, critical_path: List[str]) -> str:
        """Generate HTML for critical path section."""
        if not critical_path:
            return "<p>No dependencies found - all rules are independent</p>"
        
        html = "<p><strong>Longest dependency chain:</strong></p><p>"
        for i, rule_id in enumerate(critical_path):
            rule = next(r for r in self.rules if r.id == rule_id)
            arrow = " → " if i < len(critical_path) - 1 else ""
            html += f"{rule_id} [priority: {rule.priority}]{arrow}"
        html += f"</p><p><strong>Chain length:</strong> {len(critical_path)} rules</p>"
        return html
    
    def _generate_rule_details_html(self) -> str:
        """Generate HTML for rule details section."""
        html = ""
        for rule in sorted(self.rules, key=lambda r: r.priority, reverse=True):
            analysis = self.analyze_rule(rule.id)
            
            html += f'<div class="rule-card">'
            html += f'<h3>{rule.id}</h3>'
            html += f'<p><strong>Priority:</strong> {rule.priority}</p>'
            html += f'<p><strong>Condition:</strong> <code>{rule.condition}</code></p>'
            html += f'<p><strong>Actions:</strong> {len(rule.actions)} action(s)</p>'
            
            if hasattr(rule, 'tags') and rule.tags:
                html += f'<p><strong>Tags:</strong> {", ".join(rule.tags)}</p>'
            
            # Dependencies
            deps = analysis['dependencies'].get('dependencies', [])
            if deps:
                html += f'<p class="dependency"><strong>Depends on:</strong> {", ".join(deps)}</p>'
            
            # AST Tree
            if analysis['ast']:
                html += '<details><summary><strong>AST Structure</strong></summary>'
                html += f'<div class="ast-tree">{self.ast_viz.to_text_tree(analysis["ast"])}</div>'
                html += '</details>'
            
            html += '</div>'
        
        return html
    
    def _generate_parallelization_html(self, opportunities: List[Dict[str, Any]]) -> str:
        """Generate HTML for parallelization opportunities."""
        if not opportunities:
            return "<p>No parallelization opportunities found - rules execute sequentially.</p>"
        
        html = "<p>The following execution levels can run rules in parallel:</p>"
        for opp in opportunities:
            html += f'<div class="execution-level">'
            html += f'<strong>Level {opp["level"]}:</strong> {opp["parallel_rules"]} rules can execute in parallel'
            html += f'<br>Rules: {", ".join(opp["rules"])}'
            html += '</div>'
        
        return html
    
    def export_graphviz(self, filename: str = 'rule_dependencies.dot') -> None:
        """Export dependency graph as Graphviz DOT file."""
        self.dag_viz.save_graphviz(filename)
    
    def export_json(self, filename: str = 'rule_analysis.json') -> None:
        """Export analysis data as JSON."""
        data = {
            'rules': [
                {
                    'id': rule.id,
                    'priority': rule.priority,
                    'condition': rule.condition,
                    'actions': rule.actions,
                    'tags': getattr(rule, 'tags', [])
                }
                for rule in self.rules
            ],
            'execution_summary': self.get_execution_summary(),
            'rule_analyses': {
                rule.id: self.analyze_rule(rule.id)
                for rule in self.rules
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Analysis data exported to: {filename}")
    
    def quick_summary(self) -> None:
        """Print a quick summary of the rule structure."""
        stats = self.dag_viz.get_stats()
        
        print("\nQuick Rule Summary:")
        print("=" * 50)
        print(f"Total rules: {stats['total_rules']}")
        print(f"Execution levels: {stats['execution_levels']}")
        print(f"Total dependencies: {stats['total_dependencies']}")
        print(f"Independent rules: {stats['independent_rules']}")
        print(f"Parallelization potential: {stats['parallelization_potential']:.1f} rules per level")
        
        if stats['critical_path_length'] > 0:
            print(f"Critical path: {stats['critical_path_length']} rules")
        else:
            print("No dependency chains found")


def visualize_from_yaml(yaml_content: str, show_ast: bool = True, show_dag: bool = True) -> RuleVisualizer:
    """Quick function to visualize rules from YAML content."""
    try:
        from symbolica import Engine
        engine = Engine.from_yaml(yaml_content)
        visualizer = RuleVisualizer(engine)
        
        if show_ast:
            visualizer.show_ast()
        
        if show_dag:
            visualizer.show_dag()
        
        return visualizer
    except ImportError:
        print("Error: Could not import symbolica. Make sure it's in your Python path.")
        return None


def visualize_from_file(yaml_file: str, **kwargs) -> RuleVisualizer:
    """Quick function to visualize rules from YAML file."""
    with open(yaml_file, 'r') as f:
        yaml_content = f.read()
    return visualize_from_yaml(yaml_content, **kwargs) 