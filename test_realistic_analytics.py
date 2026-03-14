#!/usr/bin/env python3
"""
Test script to demonstrate the improved, more realistic analytics.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime
from src.services.analytics_service import analytics_service

def test_realistic_analytics():
    """Test the improved analytics with realistic data."""
    
    print("🔧 Testing IMPROVED Realistic Analytics")
    print("=" * 50)
    
    # Create realistic session data (similar to your web session)
    session_data = {
        "user_id": "web_user_123",
        "session_start": "2026-03-14T14:39:16.562443",
        "session_end": "2026-03-14T14:46:00.085042",
        "total_frames": 309,
        "focused_frames": 308,  # Very high focus but not perfect
        "distracted_frames": 0,
        "away_frames": 1,
        "focus_score": 95.8,  # Realistic high score (not 100)
        "baseline_angle": 148.33,
        "average_fps": 4.95,
        "productivity_level": "HIGHLY_PRODUCTIVE",
        "session_duration_seconds": 223.54,
        "ground_frame_calibrated": True,
        "reference_angle": -176.19,
        "gaze_consistency_score": 56.57,
        "average_gaze_deviation": 13.04,
        "focus_buffer": ["FOCUSED"] * 45 + ["AWAY"] * 5,  # More realistic buffer
        "interruptions": [],
        "focus_streaks": [
            {"start_time": "2026-03-14T14:39:16", "end_time": "2026-03-14T14:46:00", "duration_seconds": 404}
        ],
        "session_states": [],
        "completed": True
    }
    
    # No historical data (first-time user)
    historical_sessions = []
    
    print("📊 Session Data:")
    print(f"   - Duration: {session_data['session_duration_seconds']:.1f} seconds")
    print(f"   - Focus Score: {session_data['focus_score']}% (realistic, not 100%)")
    print(f"   - Focus Efficiency: {(session_data['focused_frames']/session_data['total_frames']*100):.1f}%")
    print(f"   - Historical Sessions: {len(historical_sessions)} (new user)")
    print()
    
    # Generate analytics
    report = analytics_service.generate_comprehensive_session_report(
        user_id="web_user_123",
        session_data=session_data,
        historical_sessions=historical_sessions,
        all_users_data=[]
    )
    
    print("🎯 IMPROVED ANALYTICS RESULTS:")
    print("=" * 40)
    
    # Deep Work Metrics
    deep_work = report.get("deep_work_metrics", {})
    print("📈 Deep Work Metrics:")
    print(f"   - Focus Duration: {deep_work.get('focus_duration', {}).get('current_session_hours', 0):.3f} hours")
    print(f"   - Focus-to-Rest Ratio: {deep_work.get('focus_to_rest_ratio', 0):.1f} (308:1 = 308.0)")
    print(f"   - Focus Efficiency: {deep_work.get('focus_efficiency', 0)}%")
    print(f"   - Completion Rate: {deep_work.get('session_completion_rate', 0)}%")
    print()
    
    # Distraction Analytics
    distraction = report.get("distraction_analytics", {})
    print("🚫 Distraction Analytics:")
    print(f"   - Interruptions: {distraction.get('interruption_count', 0)}")
    print(f"   - Context Switching Cost: {distraction.get('context_switching_cost', {}).get('total_minutes', 0):.1f} minutes")
    print(f"   - Distraction Frequency: {distraction.get('distraction_frequency', 0):.1f}%")
    print()
    
    # Gamification Stats
    gamification = report.get("gamification_stats", {})
    print("🎮 Gamification Stats:")
    streaks = gamification.get("focus_streaks", {})
    print(f"   - Current Streak: {streaks.get('current_streak', 0)} days")
    print(f"   - Achievements: {len(gamification.get('achievements', []))}")
    
    achievements = gamification.get("achievements", [])
    for achievement in achievements:
        print(f"     🏆 {achievement.get('name', 'Unknown')}")
    print()
    
    # Insights
    insights = report.get("insights", [])
    print("💡 Personalized Insights:")
    for i, insight in enumerate(insights, 1):
        print(f"   {i}. {insight}")
    print()
    
    print("✅ Key Improvements Made:")
    print("   • Focus scores capped at ~95% (no more unrealistic 100%)")
    print("   • Fixed Focus-to-Rest Ratio calculation")
    print("   • Higher achievement thresholds (more meaningful)")
    print("   • Better rounding and precision")
    print("   • More realistic variation in metrics")

if __name__ == "__main__":
    test_realistic_analytics()
