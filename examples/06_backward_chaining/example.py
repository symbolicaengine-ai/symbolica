#!/usr/bin/env python3
"""
Simple Backward Chaining Demo
=============================

Clean demonstration of backward chaining using a simple RPG quest scenario.
Shows how to work backwards from goals to find required dependencies.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts, goal

def main():
    print("Backward Chaining Demo")
    print("=" * 50)
    
    # Load simple quest rules
    engine = Engine.from_file("simple_quest.yaml")
    
    print(f"Loaded {len(engine.rules)} quest rules")
    print("\nBACKWARD CHAINING CONCEPT:")
    print("Instead of: 'What can I do with what I have?'")
    print("We ask: 'What do I need to achieve my goal?'")
    print("\n1. Set a goal: 'Defeat the dragon'")
    print("2. Find requirements: 'Need sword + fire resistance + high level'") 
    print("3. Find how to get requirements: 'Need magic ore + gold for sword'")
    print("4. Continue until you reach basic actions you can do now")
    
    # Test a clear goal
    dragon_goal = goal(quest_completed=True)
    print(f"\nGOAL: Defeat the Dragon")
    print(f"Target: {dragon_goal.target_facts}")
    
    # Show backward chaining analysis
    print(f"\nBACKWARD CHAINING ANALYSIS:")
    supporting_rules = engine.find_rules_for_goal(dragon_goal)
    
    if supporting_rules:
        main_rule = supporting_rules[0]
        print(f"Rule that achieves goal: '{main_rule.id}'")
        print(f"Condition: {main_rule.condition}")
        
        # Extract simple requirements
        requirements = ["has_dragon_sword == true", "fire_resistance >= 80", "level >= 15"]
        print(f"\nWhat you need:")
        for i, req in enumerate(requirements, 1):
            print(f"  {i}. {req}")
        
        # Find supporting rules for each requirement
        print(f"\nHow to get these:")
        
        # Dragon sword requirement
        sword_goal = goal(has_dragon_sword=True)
        sword_rules = engine.find_rules_for_goal(sword_goal)
        if sword_rules:
            print(f"  • Dragon sword: {sword_rules[0].id} ({sword_rules[0].condition})")
        
        # Fire resistance requirement  
        fire_goal = goal(fire_resistance=90)
        fire_rules = engine.find_rules_for_goal(fire_goal)
        if fire_rules:
            print(f"  • Fire resistance: {fire_rules[0].id} ({fire_rules[0].condition})")
        
        # Level requirement (find rules that increase level)
        print(f"  • High level: level_up_to_15 (experience >= 300)")
    
    # Test different character states
    test_scenarios = [
        {
            "name": "Newbie Character", 
            "state": facts(level=1, gold=0, experience=0),
            "description": "Just started the game"
        },
        {
            "name": "Rich but Weak",
            "state": facts(level=3, gold=500, experience=20),
            "description": "Has money but lacks experience"
        },
        {
            "name": "Experienced Hero",
            "state": facts(level=15, gold=300, experience=150, reputation=70, has_magic_ore=True),
            "description": "High level with resources"
        }
    ]
    
    print(f"\nTESTING DIFFERENT CHARACTER STATES:")
    for scenario in test_scenarios:
        print(f"\n{scenario['name']} - {scenario['description']}")
        print(f"Starting state: {scenario['state'].data}")
        
        # Check if goal is achievable
        can_achieve = engine.can_achieve_goal(dragon_goal, scenario['state'])
        status = "CAN ACHIEVE GOAL" if can_achieve else "CANNOT ACHIEVE GOAL"
        print(f"Result: {status}")
        
        if can_achieve:
            # Show what happens when we execute
            result = engine.reason(scenario['state'])
            if 'quest_completed' in result.verdict:
                print(f"Success! Final result: {result.verdict.get('quest_completed')}")
                print(f"Rules fired: {' → '.join(result.fired_rules[-3:])}")
            else:
                print(f"Progress made: {len(result.fired_rules)} rules fired")
                print(f"Final state includes: {list(result.verdict.keys())}")

    # Show dependency tree
    print(f"\nDEPENDENCY TREE ANALYSIS:")
    print("To defeat dragon, you need:")
    print("├── Dragon Sword")
    print("│   ├── Magic Ore (requires level 10)")
    print("│   └── 200 Gold")
    print("├── Fire Resistance (50 gold)")
    print("└── Level 15")
    print("    └── Experience (need 300 total)")
    print("\nBasic path: Work for gold → Gain experience → Level up → Get resources → Achieve goal!")

if __name__ == "__main__":
    main() 