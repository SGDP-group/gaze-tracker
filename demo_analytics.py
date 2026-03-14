#!/usr/bin/env python3
"""
Demo script showing the comprehensive analytics in action.
This demonstrates how the new analytics metrics would be used.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import json
from datetime import datetime
from src.services.analytics_service import analytics_service

def demo_comprehensive_analytics():
    """Demonstrate the comprehensive analytics with a realistic scenario."""
    
    print("🎯 Focus Analytics System - Comprehensive Demo")
    print("=" * 60)
    print("This demo shows the new analytics metrics that are now")
    print("available at the end of each focus session.")
    print()
    
    # Simulate a realistic focus session
    print("📊 Simulating Focus Session...")
    print("   - User: 'alex_digital'")
    print("   - Session: Morning coding session")
    print("   - Duration: 45 minutes")
    print("   - Task: Feature development")
    print()
    
    # Create realistic session data
    session_data = {
        "user_id": "alex_digital",
        "session_id": "session_2024_03_14_09_00",
        "session_start": "2024-03-14T09:00:00",
        "session_end": "2024-03-14T09:45:00",
        "total_frames": 2700,  # 45 minutes at 1 FPS
        "focused_frames": 2160,  # 80% focus
        "distracted_frames": 360,
        "away_frames": 180,
        "focus_score": 80.0,
        "baseline_angle": 3.2,
        "average_fps": 1.0,
        "productivity_level": "PRODUCTIVE",
        "session_duration_seconds": 2700.0,
        "ground_frame_calibrated": True,
        "reference_angle": 0.0,
        "gaze_consistency_score": 78.5,
        "average_gaze_deviation": 12.3,
        "focus_buffer": ["FOCUSED"] * 35 + ["DISTRACTED"] * 8 + ["FOCUSED"] * 7,
        "interruptions": [
            {"timestamp": "2024-03-14T09:15:30", "from_state": "FOCUSED", "to_state": "DISTRACTED"},
            {"timestamp": "2024-03-14T09:32:15", "from_state": "FOCUSED", "to_state": "AWAY"}
        ],
        "focus_streaks": [
            {"start_time": "2024-03-14T09:00:00", "end_time": "2024-03-14T09:15:30", "duration_seconds": 930},
            {"start_time": "2024-03-14T09:18:00", "end_time": "2024-03-14T09:32:15", "duration_seconds": 855},
            {"start_time": "2024-03-14T09:35:00", "end_time": "2024-03-14T09:45:00", "duration_seconds": 600}
        ],
        "session_states": [
            {"timestamp": "2024-03-14T09:00:00", "from_state": "AWAY", "to_state": "FOCUSED"},
            {"timestamp": "2024-03-14T09:15:30", "from_state": "FOCUSED", "to_state": "DISTRACTED"},
            {"timestamp": "2024-03-14T09:18:00", "from_state": "DISTRACTED", "to_state": "FOCUSED"},
            {"timestamp": "2024-03-14T09:32:15", "from_state": "FOCUSED", "to_state": "AWAY"},
            {"timestamp": "2024-03-14T09:35:00", "from_state": "AWAY", "to_state": "FOCUSED"}
        ],
        "completed": True
    }
    
    # Create some historical data for context
    historical_sessions = []
    for i in range(15):
        historical_sessions.append({
            "session_start": f"2024-03-{14-i:02d}T09:00:00",
            "session_end": f"2024-03-{14-i:02d}T09:30:00",
            "total_frames": 1800,
            "focused_frames": 1440 + (i % 4) * 60,
            "distracted_frames": 240 - (i % 3) * 40,
            "away_frames": 120,
            "focus_score": 75.0 + (i % 5) * 3,
            "session_duration_seconds": 1800.0,
            "completed": True
        })
    
    # Generate comprehensive analytics
    print("🔍 Generating Comprehensive Analytics Report...")
    print()
    
    report = analytics_service.generate_comprehensive_session_report(
        user_id="alex_digital",
        session_data=session_data,
        historical_sessions=historical_sessions,
        all_users_data=[]  # No peer data for this demo
    )
    
    # Display the results in a user-friendly format
    print("📈 COMPREHENSIVE SESSION ANALYTICS")
    print("=" * 60)
    
    # Session Summary
    print("\n📋 SESSION SUMMARY")
    print("-" * 30)
    print(f"Duration: {session_data['session_duration_seconds']/60:.1f} minutes")
    print(f"Focus Score: {session_data['focus_score']}%")
    print(f"Productivity Level: {session_data['productivity_level']}")
    print(f"Session completed at: {session_data['session_end']}")
    
    # Deep Work Metrics
    print("\n🎯 CORE DEEP WORK METRICS")
    print("-" * 30)
    deep_work = report.get("deep_work_metrics", {})
    if deep_work:
        focus_duration = deep_work.get("focus_duration", {})
        print(f"Focus Duration (Current): {focus_duration.get('current_session_hours', 0):.2f} hours")
        print(f"Focus Duration (Daily Total): {focus_duration.get('daily_total_hours', 0):.2f} hours")
        print(f"Focus-to-Rest Ratio: {deep_work.get('focus_to_rest_ratio', 0):.2f}")
        
        streak = deep_work.get("longest_focus_streak", {})
        print(f"Longest Focus Streak: {streak.get('minutes', 0):.1f} minutes")
        print(f"Session Completion Rate: {deep_work.get('session_completion_rate', 0):.1f}%")
        print(f"Focus Efficiency: {deep_work.get('focus_efficiency', 0):.1f}%")
    
    # Distraction Analytics
    print("\n🚫 DISTRACTION & INTERFERENCE ANALYTICS")
    print("-" * 30)
    distraction = report.get("distraction_analytics", {})
    if distraction:
        print(f"Interruption Count: {distraction.get('interruption_count', 0)}")
        
        context_cost = distraction.get("context_switching_cost", {})
        print(f"Context Switching Cost: {context_cost.get('total_minutes', 0):.1f} minutes")
        print(f"  (Based on {context_cost.get('cost_per_interruption_minutes', 0):.0f} min per interruption)")
        
        print(f"Distraction Frequency: {distraction.get('distraction_frequency', 0):.1f}%")
        
        recovery = distraction.get("recovery_metrics", {})
        print(f"Average Recovery Time: {recovery.get('average_recovery_time_seconds', 0):.1f} seconds")
        
        patterns = distraction.get("distraction_patterns", {})
        print(f"Common Distraction Types: {list(patterns.get('common_distraction_types', {}).keys())}")
    
    # Biological Trends
    print("\n🌱 BIOLOGICAL & RHYTHMIC TRENDS")
    print("-" * 30)
    bio_trends = report.get("biological_trends", {})
    if bio_trends and bio_trends.get("peak_performance_times"):
        peak_times = bio_trends.get("peak_performance_times", [])
        if peak_times:
            best_time = peak_times[0]
            print(f"Peak Performance Time: {best_time.get('hour', 0):02d}:00")
            print(f"Average Score at Peak: {best_time.get('average_focus_score', 0):.1f}%")
            print(f"Performance Level: {best_time.get('performance_level', 'UNKNOWN')}")
        
        heatmap = bio_trends.get("focus_heatmap", [])
        print(f"Heatmap Data Points: {len(heatmap)} (hour × day combinations)")
        
        insights = bio_trends.get("rhythmic_insights", {})
        if "best_performance_day" in insights:
            print(f"Best Performance Day: {insights.get('best_performance_day', 'Unknown')}")
            print(f"Pattern Consistency: {insights.get('pattern_consistency', 0):.1f}%")
    
    # Gamification Stats
    print("\n🎮 GAMIFICATION & RETENTION STATS")
    print("-" * 30)
    gamification = report.get("gamification_stats", {})
    if gamification:
        streaks = gamification.get("focus_streaks", {})
        print(f"Current Focus Streak: {streaks.get('current_streak', 0)} days 🔥")
        print(f"Longest Focus Streak: {streaks.get('longest_streak', 0)} days")
        print(f"Total Active Days: {streaks.get('total_active_days', 0)}")
        
        achievements = gamification.get("achievements", [])
        print(f"Achievements Unlocked: {len(achievements)}")
        for achievement in achievements:
            print(f"  🏆 {achievement.get('name', 'Unknown')}")
        
        retention = gamification.get("retention_metrics", {})
        if "average_days_between_sessions" in retention:
            print(f"Session Frequency: {retention.get('session_frequency_score', 'Unknown')}")
            print(f"Retention Rate (30 days): {retention.get('retention_rate_30_days', 0):.1f}%")
    
    # Personalized Insights
    print("\n💡 PERSONALIZED INSIGHTS")
    print("-" * 30)
    insights = report.get("insights", [])
    if insights:
        for i, insight in enumerate(insights, 1):
            print(f"{i}. {insight}")
    else:
        print("No insights available for this session.")
    
    print("\n" + "=" * 60)
    print("🎉 Analytics Demo Complete!")
    print("These comprehensive metrics are now available at the end of")
    print("each focus session via the API endpoints:")
    print("  • POST /api/v1/focus/session/end")
    print("  • GET /api/v1/focus/session/{user_id}")
    print()

if __name__ == "__main__":
    demo_comprehensive_analytics()
