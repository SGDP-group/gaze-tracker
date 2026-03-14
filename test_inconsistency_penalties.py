#!/usr/bin/env python3
"""
Test script to demonstrate inconsistency penalties in focus scoring.
Shows how inconsistent focus patterns affect the overall score.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import config

def calculate_inconsistency_penalty(focus_buffer):
    """Calculate penalty for inconsistent focus patterns."""
    if not config.INCONSISTENCY_PENALTY_ENABLED or len(focus_buffer) < 10:
        return 0.0
    
    # Count state changes
    state_changes = 0
    for i in range(1, len(focus_buffer)):
        if focus_buffer[i] != focus_buffer[i-1]:
            state_changes += 1
    
    # Calculate penalty based on change frequency
    max_possible_changes = len(focus_buffer) - 1
    change_frequency = state_changes / max_possible_changes
    
    # Apply penalty factor
    penalty = change_frequency * config.INCONSISTENCY_PENALTY_FACTOR * 100
    
    # Cap at maximum penalty
    penalty = min(penalty, config.MAX_INCONSISTENCY_PENALTY)
    
    return penalty

def test_inconsistency_penalties():
    """Test how inconsistency penalties affect focus scores."""
    
    print("🔄 INCONSISTENCY PENALTY DEMO")
    print("=" * 50)
    
    print("⚙️ Current Inconsistency Settings:")
    print(f"   • INCONSISTENCY_PENALTY_ENABLED: {config.INCONSISTENCY_PENALTY_ENABLED}")
    print(f"   • INCONSISTENCY_PENALTY_FACTOR: {config.INCONSISTENCY_PENALTY_FACTOR}")
    print(f"   • MAX_INCONSISTENCY_PENALTY: {config.MAX_INCONSISTENCY_PENALTY}%")
    print()
    
    # Test scenarios with different focus patterns
    scenarios = {
        "Consistent Focus": ["FOCUSED"] * 45 + ["DISTRACTED"] * 5,  # 1 state change
        "Moderately Inconsistent": ["FOCUSED"] * 20 + ["DISTRACTED"] * 5 + ["FOCUSED"] * 15 + ["AWAY"] * 5 + ["FOCUSED"] * 5,  # 4 changes
        "Highly Inconsistent": ["FOCUSED", "DISTRACTED"] * 25,  # 49 changes
        "Chaotic Focus": ["FOCUSED", "DISTRACTED", "AWAY", "FOCUSED", "AWAY", "DISTRACTED"] * 8 + ["FOCUSED"] * 2,  # 47 changes
    }
    
    print("🧪 Testing Different Focus Patterns:")
    print("-" * 40)
    
    for scenario_name, focus_buffer in scenarios.items():
        print(f"\n📊 {scenario_name}:")
        print(f"   • Buffer length: {len(focus_buffer)} frames")
        print(f"   • State changes: {sum(1 for i in range(1, len(focus_buffer)) if focus_buffer[i] != focus_buffer[i-1])}")
        
        # Calculate focused frames
        focused_count = sum(1 for state in focus_buffer if state == "FOCUSED")
        raw_focus_percentage = (focused_count / len(focus_buffer)) * 100
        
        print(f"   • Raw focus percentage: {raw_focus_percentage:.1f}%")
        
        # Calculate inconsistency penalty
        penalty = calculate_inconsistency_penalty(focus_buffer)
        adjusted_score = max(0, raw_focus_percentage - penalty)
        
        print(f"   • Inconsistency penalty: {penalty:.1f}%")
        print(f"   • Adjusted focus score: {adjusted_score:.1f}%")
        print(f"   • Score reduction: {raw_focus_percentage - adjusted_score:.1f}%")
    
    print("\n🎯 Impact Analysis:")
    print("=" * 30)
    
    # Show how different penalty factors affect scores
    test_buffer = ["FOCUSED"] * 15 + ["DISTRACTED"] * 5 + ["FOCUSED"] * 15 + ["AWAY"] * 5 + ["FOCUSED"] * 10  # 4 changes
    raw_score = (sum(1 for state in test_buffer if state == "FOCUSED") / len(test_buffer)) * 100
    
    print(f"Test scenario: 4 state changes, {raw_score:.1f}% raw focus")
    print()
    
    penalty_factors = [0.05, 0.1, 0.15, 0.2]
    for factor in penalty_factors:
        config.INCONSISTENCY_PENALTY_FACTOR = factor
        penalty = calculate_inconsistency_penalty(test_buffer)
        adjusted = max(0, raw_score - penalty)
        print(f"   Factor {factor:.2f}: {penalty:.1f}% penalty → {adjusted:.1f}% final score")
    
    # Reset to default
    config.INCONSISTENCY_PENALTY_FACTOR = 0.1
    
    print("\n🔧 Configuration Examples:")
    print("-" * 30)
    
    print("For beginners (more lenient):")
    print("   config.INCONSISTENCY_PENALTY_FACTOR = 0.05")
    print("   config.MAX_INCONSISTENCY_PENALTY = 5.0")
    print()
    
    print("For power users (strict):")
    print("   config.INCONSISTENCY_PENALTY_FACTOR = 0.2")
    print("   config.MAX_INCONSISTENCY_PENALTY = 20.0")
    print()
    
    print("To disable penalties:")
    print("   config.INCONSISTENCY_PENALTY_ENABLED = False")
    
    print("\n💡 How Inconsistency is Measured:")
    print("-" * 35)
    print("• State changes: FOCUSED ↔ DISTRACTED/AWAY transitions")
    print("• Change frequency: (changes / (buffer_size - 1))")
    print("• Penalty formula: frequency × factor × 100")
    print("• Capped at MAX_INCONSISTENCY_PENALTY to prevent harsh scores")
    print("• Only applied with 10+ frames in buffer")
    
    print("\n✅ Benefits of Inconsistency Penalties:")
    print("-" * 40)
    print("• Encourages sustained focus periods")
    print("• Discourages 'jumpy' attention patterns")
    print("• Rewards deep work over scattered attention")
    print("• Provides more realistic productivity metrics")
    print("• Helps users identify focus improvement areas")

if __name__ == "__main__":
    test_inconsistency_penalties()
