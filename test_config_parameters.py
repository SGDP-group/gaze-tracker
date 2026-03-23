#!/usr/bin/env python3
"""
Test script to demonstrate the configurable algorithm parameters.
Shows how different configurations affect focus tracking behavior.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime
from src.services.analytics_service import analytics_service
from src.config import config

def test_config_parameters():
    """Test different configuration scenarios."""
    
    print("🔧 CONFIGURABLE ALGORITHM PARAMETERS DEMO")
    print("=" * 60)
    
    print("📋 Current Configuration:")
    print(f"   • FOCUSED_ANGLE_THRESHOLD: {config.FOCUSED_ANGLE_THRESHOLD}°")
    print(f"   • DISTRACTED_ANGLE_THRESHOLD: {config.DISTRACTED_ANGLE_THRESHOLD}°")
    print(f"   • DISTRACTION_CONFIRMATION_TIME: {config.DISTRACTION_CONFIRMATION_TIME}s")
    print(f"   • BASELINE_ALPHA: {config.BASELINE_ALPHA}")
    print(f"   • FOCUS_BUFFER_SIZE: {config.FOCUS_BUFFER_SIZE}")
    print(f"   • MAX_REALISTIC_FOCUS_SCORE: {config.MAX_REALISTIC_FOCUS_SCORE}%")
    print(f"   • CONTEXT_SWITCH_RECOVERY_MINUTES: {config.CONTEXT_SWITCH_RECOVERY_MINUTES}")
    print(f"   • MINIMUM_INTERUPTION_DURATION_SECONDS: {config.MINIMUM_INTERUPTION_DURATION_SECONDS}s")
    print()
    
    # Test session data
    session_data = {
        "user_id": "test_user",
        "session_start": "2026-03-14T14:39:16.562443",
        "session_end": "2026-03-14T14:46:00.085042",
        "total_frames": 300,
        "focused_frames": 240,  # 80% focus
        "distracted_frames": 45,
        "away_frames": 15,
        "focus_score": 80.0,
        "baseline_angle": 148.33,
        "average_fps": 5.0,
        "productivity_level": "PRODUCTIVE",
        "session_duration_seconds": 60.0,
        "ground_frame_calibrated": True,
        "reference_angle": 0.0,
        "gaze_consistency_score": 70.0,
        "average_gaze_deviation": 15.0,
        "focus_buffer": ["FOCUSED"] * 40 + ["DISTRACTED"] * 8 + ["AWAY"] * 2,
        "interruptions": [
            {"timestamp": "2026-03-14T14:42:00", "from_state": "FOCUSED", "to_state": "DISTRACTED"},
            {"timestamp": "2026-03-14T14:44:30", "from_state": "FOCUSED", "to_state": "AWAY"}
        ],
        "focus_streaks": [],
        "session_states": [],
        "completed": True
    }
    
    print("🧪 Testing with Current Configuration:")
    print(f"   • Session: {session_data['focused_frames']}/{session_data['total_frames']} focused frames")
    print(f"   • Focus Buffer: {len(session_data['focus_buffer'])} states")
    print(f"   • Interruptions: {len(session_data['interruptions'])}")
    print()
    
    # Generate analytics with current config
    report = analytics_service.generate_comprehensive_session_report(
        user_id="test_user",
        session_data=session_data,
        historical_sessions=[],
        all_users_data=[]
    )
    
    print("📊 CURRENT CONFIG RESULTS:")
    deep_work = report.get("deep_work_metrics", {})
    distraction = report.get("distraction_analytics", {})
    
    print(f"   • Focus Efficiency: {deep_work.get('focus_efficiency', 0)}%")
    print(f"   • Focus-to-Rest Ratio: {deep_work.get('focus_to_rest_ratio', 0)}")
    print(f"   • Interruption Count: {distraction.get('interruption_count', 0)}")
    print(f"   • Context Switching Cost: {distraction.get('context_switching_cost', {}).get('total_minutes', 0):.1f} minutes")
    print()
    
    # Show tuning scenarios
    print("🎯 TUNING SCENARIOS COMPARISON:")
    print("=" * 40)
    
    scenarios = {
        "Beginner-Friendly": {
            "FOCUSED_ANGLE_THRESHOLD": 25,
            "DISTRACTED_ANGLE_THRESHOLD": 35,
            "DISTRACTION_CONFIRMATION_TIME": 3.0,
            "BASELINE_ALPHA": 0.1,
            "MAX_REALISTIC_FOCUS_SCORE": 93
        },
        "Power User": {
            "FOCUSED_ANGLE_THRESHOLD": 15,
            "DISTRACTED_ANGLE_THRESHOLD": 25,
            "DISTRACTION_CONFIRMATION_TIME": 1.0,
            "BASELINE_ALPHA": 0.03,
            "MAX_REALISTIC_FOCUS_SCORE": 98
        },
        "Creative Work": {
            "FOCUSED_ANGLE_THRESHOLD": 30,
            "DISTRACTED_ANGLE_THRESHOLD": 40,
            "DISTRACTION_CONFIRMATION_TIME": 4.0,
            "BASELINE_ALPHA": 0.08,
            "MINIMUM_INTERUPTION_DURATION_SECONDS": 120
        }
    }
    
    for scenario_name, params in scenarios.items():
        print(f"\n📝 {scenario_name} Configuration:")
        print("   • Modified Parameters:")
        for param, value in params.items():
            original = getattr(config, param)
            print(f"     - {param}: {original} → {value}")
        
        # Simulate impact (simplified)
        if scenario_name == "Beginner-Friendly":
            print("   • Expected Impact: More lenient focus detection, easier achievements")
        elif scenario_name == "Power User":
            print("   • Expected Impact: Strict focus detection, challenging achievements")
        elif scenario_name == "Creative Work":
            print("   • Expected Impact: Natural movement allowed, longer interruptions ignored")
    
    print("\n🔍 CONFIGURATION VALIDATION:")
    validation = config.validate_config()
    if validation["valid"]:
        print("   ✅ All configuration parameters are valid")
    else:
        print("   ⚠️ Configuration warnings:")
        for warning in validation["warnings"]:
            print(f"     - {warning}")
    
    print("\n📚 TUNING GUIDE SUMMARY:")
    print("   • Use config.get_tuning_guide() for comprehensive guidance")
    print("   • Start with default values, adjust one parameter at a time")
    print("   • Monitor user feedback and engagement metrics")
    print("   • Consider user's natural work patterns and environment")
    
    print("\n🎛️ QUICK ADJUSTMENT EXAMPLES:")
    print("   # For more sensitive focus detection:")
    print("   config.FOCUSED_ANGLE_THRESHOLD = 15")
    print("   config.DISTRACTED_ANGLE_THRESHOLD = 25")
    print()
    print("   # For more forgiving achievements:")
    print("   config.ACHIEVEMENT_THRESHOLDS['dedicated_focus'] = 10")
    print("   config.ACHIEVEMENT_THRESHOLDS['hour_power'] = 1")
    print()
    print("   # For creative work environments:")
    print("   config.MINIMUM_INTERUPTION_DURATION_SECONDS = 120")
    print("   config.CONTEXT_SWITCH_RECOVERY_MINUTES = 25")

if __name__ == "__main__":
    test_config_parameters()
