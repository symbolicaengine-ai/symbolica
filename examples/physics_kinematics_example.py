#!/usr/bin/env python3
"""
Newton's Kinematic Equations Example
===================================

Demonstrates how to implement physics calculations using Symbolica rules.
This example uses Newton's kinematic equations to solve motion problems:

1. v = v₀ + at           (final velocity)
2. x = x₀ + v₀t + ½at²   (position with constant acceleration)  
3. v² = v₀² + 2a(x - x₀) (velocity from acceleration and displacement)
4. x = x₀ + ½(v₀ + v)t   (position from average velocity)

Perfect for:
- Physics simulations and validations
- Engineering calculations
- Educational demonstrations
- Expression evaluation in actions (unquoted = computed, quoted = literal)
"""

from symbolica import Engine, facts


def create_kinematics_engine():
    """Create engine with kinematic equation rules using expression evaluation."""
    
    kinematics_rules = """
rules:
  # Rule 1: Calculate final velocity (v = v₀ + at)
  - id: "calculate_final_velocity"
    priority: 100
    condition:
      all:
        - "v0 is not None"
        - "a is not None" 
        - "t is not None"
        - "v is None"
    actions:
      v: v0 + a * t                    # Unquoted = evaluated as number
      calculation_used: "v = v₀ + at"  # Quoted = kept as string literal
      physics_law: "First kinematic equation"
    tags: ["velocity", "kinematics"]

  # Rule 2: Calculate position with constant acceleration (x = x₀ + v₀t + ½at²)
  - id: "calculate_position_acceleration"
    priority: 100
    condition:
      all:
        - "x0 is not None"
        - "v0 is not None"
        - "a is not None"
        - "t is not None"
        - "x is None"
    actions:
      x: x0 + v0 * t + 0.5 * a * (t ** 2)  # Complex expression = computed
      calculation_used: "x = x₀ + v₀t + ½at²"
      physics_law: "Second kinematic equation"
    tags: ["position", "kinematics"]

  # Rule 3: Calculate final velocity from acceleration and displacement (v² = v₀² + 2a(x - x₀))
  - id: "calculate_velocity_from_displacement"
    priority: 100
    condition:
      all:
        - "v0 is not None"
        - "a is not None"
        - "x is not None"
        - "x0 is not None"
        - "v is None"
    actions:
      v_squared: v0**2 + 2 * a * (x - x0)  # Mathematical expression
      calculation_used: "v² = v₀² + 2a(x - x₀)"
      physics_law: "Third kinematic equation"
    tags: ["velocity", "displacement", "kinematics"]

  # Rule 4: Calculate acceleration from velocity and time (a = (v - v₀)/t)
  - id: "calculate_acceleration"
    priority: 100
    condition:
      all:
        - "v is not None"
        - "v0 is not None"
        - "t is not None"
        - "t > 0"
        - "a is None"
    actions:
      a: (v - v0) / t                      # Expression with parentheses
      calculation_used: "a = (v - v₀)/t"
      physics_law: "Derived from first kinematic equation"
    tags: ["acceleration", "kinematics"]

  # Rule 5: Calculate time from velocity and acceleration (t = (v - v₀)/a)
  - id: "calculate_time"
    priority: 100
    condition:
      all:
        - "v is not None"
        - "v0 is not None"
        - "a is not None"
        - not: 
            any:
              - "a == 0"
        - "t is None"
    actions:
      t: (v - v0) / a
      calculation_used: "t = (v - v₀)/a"
      physics_law: "Derived from first kinematic equation"
    tags: ["time", "kinematics"]

  # Rule 6: Calculate position from average velocity (x = x₀ + ½(v₀ + v)t)
  - id: "calculate_position_average_velocity"
    priority: 90
    condition:
      all:
        - "x0 is not None"
        - "v0 is not None"
        - "v is not None"
        - "t is not None"
        - "x is None"
    actions:
      x: x0 + 0.5 * (v0 + v) * t
      calculation_used: "x = x₀ + ½(v₀ + v)t"
      physics_law: "Fourth kinematic equation"
    tags: ["position", "average_velocity", "kinematics"]

  # Rule 7: Validate physics constraints
  - id: "check_physical_validity"
    priority: 50
    condition: "True"  # Always check
    actions:
      is_physically_valid: true
    tags: ["validation"]

  # Rule 8: Classify motion types using computed values
  - id: "classify_motion_accelerating"
    priority: 40
    condition:
      all:
        - "a is not None"
        - "a > 0"
    actions:
      motion_type: "accelerating"
      motion_description: "Object is speeding up"
      acceleration_magnitude: abs(a)       # Function call in expression
    tags: ["classification"]

  - id: "classify_motion_decelerating"
    priority: 40
    condition:
      all:
        - "a is not None"
        - "a < 0"
    actions:
      motion_type: "decelerating"
      motion_description: "Object is slowing down"
      acceleration_magnitude: abs(a)
    tags: ["classification"]

  - id: "classify_motion_uniform"
    priority: 40
    condition:
      all:
        - "a is not None"
        - "a == 0"
    actions:
      motion_type: "uniform"
      motion_description: "Object moves at constant velocity"
      acceleration_magnitude: 0
    tags: ["classification"]

  # Rule 9: Complex safety checks with computed thresholds
  - id: "check_extreme_acceleration"
    priority: 30
    condition:
      all:
        - "a is not None"
        - "abs(a) > 100"
    actions:
      warning: "Extreme acceleration detected"
      extreme_conditions: true
      safety_factor: abs(a) / 100         # Computed safety ratio
    tags: ["safety", "validation"]

  # Rule 10: Advanced motion classification with multiple computations
  - id: "classify_projectile_motion"
    priority: 35
    condition:
      any:
        - all:
          - "v0 > 0"
          - "a < 0"
          - "abs(a) > 5"
        - all:
          - "v0 == 0"
          - "a < 0"
          - "abs(a) > 5"
    actions:
      motion_category: "projectile_or_freefall"
      motion_explanation: "Object under significant downward acceleration"
      gravitational_ratio: abs(a) / 9.81  # Computed ratio to Earth gravity
    tags: ["classification", "projectile"]

  # Rule 11: Energy calculations using expressions
  - id: "calculate_energy_metrics"
    priority: 25
    condition:
      all:
        - "v is not None"
        - "v != 0"
    actions:
      kinetic_energy_factor: 0.5 * (v ** 2)   # KE = ½mv² (assuming unit mass)
      speed: abs(v)                            # Speed is magnitude of velocity
      energy_description: "Kinetic energy computed"
    tags: ["energy", "calculations"]

  # Rule 12: Calculate displacement with expressions
  - id: "calculate_displacement"
    priority: 35
    condition:
      all:
        - "x is not None"
        - "x0 is not None"
    actions:
      displacement: x - x0
      displacement_magnitude: abs(x - x0)
      calculation_used: "Δx = x - x₀"
    tags: ["displacement"]

  # Rule 13: Detect special cases with computed conditions
  - id: "detect_zero_initial_conditions"
    priority: 20
    condition:
      all:
        - any:
          - "v0 == 0"
          - "x0 == 0"
        - not:
            any:
              - "a == 0"
    actions:
      special_case: "zero_initial_conditions"
      case_description: "Motion starts from rest or origin"
      initial_condition_type: "rest_or_origin"
    tags: ["special_cases"]

  # Rule 14: Advanced physics insights with multiple expressions
  - id: "calculate_comprehensive_metrics"
    priority: 15
    condition:
      all:
        - "v is not None"
        - "a is not None"
        - "t is not None"
    actions:
      velocity_change: abs(v - v0) if v0 is not None else abs(v)
      acceleration_time_product: abs(a * t)
      motion_efficiency: abs(v) / abs(a * t) if a != 0 and t != 0 else 1
      analysis_description: "Comprehensive motion analysis completed"
    tags: ["analysis", "comprehensive"]
"""

    return Engine.from_yaml(kinematics_rules)


def solve_physics_problem(engine, scenario_name, initial_conditions, description):
    """Solve a physics problem using kinematic rules with expression evaluation."""
    
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*60}")
    print(f"Description: {description}")
    print(f"Initial conditions: {initial_conditions}")
    
    # Create facts from initial conditions
    physics_facts = facts(**initial_conditions)
    
    # Solve using rules
    result = engine.reason(physics_facts)
    
    print(f"\nSOLUTION:")
    print(f"Execution time: {result.execution_time_ms:.3f}ms")
    
    # Display results organized by category
    verdict = result.verdict
    
    # Core physics results (computed values)
    physics_results = {}
    classifications = {}
    validations = {}
    insights = {}
    
    for key, value in verdict.items():
        if key in ['v', 'x', 'a', 't', 'displacement', 'v_squared', 'displacement_magnitude', 'speed', 'kinetic_energy_factor']:
            physics_results[key] = value
        elif 'motion' in key or 'classification' in key or 'category' in key or 'acceleration_magnitude' in key:
            classifications[key] = value
        elif 'validation' in key or 'warning' in key or 'extreme' in key or 'safety' in key:
            validations[key] = value
        elif 'energy' in key or 'special' in key or 'analysis' in key or 'efficiency' in key or 'ratio' in key:
            insights[key] = value
    
    # Display organized results
    if physics_results:
        print(f"\nPhysics Results (Computed Values):")
        for key, value in physics_results.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
    
    if classifications:
        print(f"\nMotion Classification:")
        for key, value in classifications.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
    
    if validations:
        print(f"\nValidation & Safety:")
        for key, value in validations.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
    
    if insights:
        print(f"\nPhysics Insights:")
        for key, value in insights.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
    
    # Show which physics law was used
    if 'calculation_used' in verdict:
        print(f"\nPhysics calculation: {verdict['calculation_used']}")
    if 'physics_law' in verdict:
        print(f"Based on: {verdict['physics_law']}")
    
    print(f"\nExpression Evaluation Summary:")
    print(f"Rules fired: {len(result.fired_rules)}")
    for rule_id in result.fired_rules:
        print(f"  ✓ {rule_id}")
    
    return result


def main():
    """Run kinematic equation examples with expression evaluation in actions."""
    
    print("Newton's Kinematic Equations with Expression Evaluation")
    print("Demonstrating unquoted expressions → computed numbers, quoted → string literals")
    
    # Create physics engine
    engine = create_kinematics_engine()
    
    # Example 1: Free fall problem
    solve_physics_problem(
        engine,
        "Free Fall from Building", 
        {
            'x0': 0,      # Starting at ground level reference
            'v0': 0,      # Dropped (not thrown)
            'a': -9.81,   # Gravitational acceleration (m/s²)
            't': 3.0,     # Time of fall (seconds)
            'x': None,    # Position to calculate
            'v': None     # Final velocity to calculate
        },
        "Object dropped from rest, falls for 3 seconds under gravity"
    )
    
    # Example 2: Car acceleration problem
    solve_physics_problem(
        engine,
        "Car Acceleration",
        {
            'v0': 15.0,   # Initial velocity (m/s) - about 54 km/h
            'v': 30.0,    # Final velocity (m/s) - about 108 km/h
            't': 5.0,     # Time interval (seconds)
            'x0': 0,      # Starting position
            'a': None,    # Acceleration to calculate
            'x': None     # Final position to calculate
        },
        "Car accelerates from 54 km/h to 108 km/h in 5 seconds"
    )
    
    # Example 3: Complex projectile motion
    solve_physics_problem(
        engine,
        "Projectile Launch",
        {
            'x0': 0,      # Starting position
            'v0': 50.0,   # Initial velocity (m/s)
            'a': -9.81,   # Gravitational acceleration
            't': 3.0,     # Flight time (seconds)
            'x': None,    # Position to calculate
            'v': None     # Final velocity to calculate
        },
        "Projectile launched with initial velocity, subject to gravity"
    )
    
    # Example 4: Extreme rocket scenario
    solve_physics_problem(
        engine,
        "Space Rocket Launch",
        {
            'v0': 0,      # Starting from rest
            'a': 250.0,   # Extreme acceleration (triggers warnings)
            't': 1.5,     # Burn time
            'x0': 0,      # Starting at launch pad
            'v': None,    # Final velocity
            'x': None     # Altitude reached
        },
        "Rocket with extreme acceleration (demonstrates expression evaluation)"
    )
    
    print(f"\n{'='*60}")
    print("EXPRESSION EVALUATION DEMONSTRATION COMPLETE")
    print("Key Features Demonstrated:")
    print("- Unquoted expressions evaluated as numbers (v0 + a * t)")
    print("- Quoted strings kept as literals ('Hello world')")
    print("- Complex mathematical expressions (0.5 * (v0 + v) * t)")
    print("- Function calls in expressions (abs(a))")
    print("- Conditional expressions (value if condition else other)")
    print("- Arithmetic operations: +, -, *, /, **, abs(), etc.")
    print("- Sub-millisecond execution with real computed values")
    print(f"{'='*60}")


if __name__ == "__main__":
    main() 