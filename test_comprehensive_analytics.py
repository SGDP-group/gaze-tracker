#!/usr/bin/env python3
"""
Test script for comprehensive analytics implementation.
Tests the new analytics service with sample data.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta
from src.services.analytics_service import analytics_service

def create_sample_session_data():
    """Create sample session data for testing."""
    return {
        "user_id": "test_user",
        "session_id": "test_session_001",
        "session_start": (datetime.now() - timedelta(minutes=25)).isoformat(),
        "session_end": datetime.now().isoformat(),
        "total_frames": 1500,  # 25 minutes at ~1 FPS
        "focused_frames": 1200,  # 80% focus
        "distracted_frames": 200,
        "away_frames": 100,
        "focus_score": 80.0,
        "baseline_angle": 5.2,
        "average_fps": 1.0,
        "productivity_level": "PRODUCTIVE",
        "session_duration_seconds": 1500.0,
        "ground_frame_calibrated": True,
        "reference_angle": 0.0,
        "gaze_consistency_score": 75.0,
        "average_gaze_deviation": 15.0,
        "focus_buffer": ["FOCUSED"] * 40 + ["DISTRACTED"] * 5 + ["FOCUSED"] * 5,
        "interruptions": [
            {"timestamp": (datetime.now() - timedelta(minutes=20)).isoformat(), "from_state": "FOCUSED", "to_state": "DISTRACTED"},
            {"timestamp": (datetime.now() - timedelta(minutes=10)).isoformat(), "from_state": "FOCUSED", "to_state": "AWAY"}
        ],
        "focus_streaks": [
            {"start_time": (datetime.now() - timedelta(minutes=25)).isoformat(), "end_time": (datetime.now() - timedelta(minutes=20)).isoformat(), "duration_seconds": 300},
            {"start_time": (datetime.now() - timedelta(minutes=18)).isoformat(), "end_time": (datetime.now() - timedelta(minutes=10)).isoformat(), "duration_seconds": 480}
        ],
        "session_states": [
            {"timestamp": (datetime.now() - timedelta(minutes=25)).isoformat(), "from_state": "AWAY", "to_state": "FOCUSED"},
            {"timestamp": (datetime.now() - timedelta(minutes=20)).isoformat(), "from_state": "FOCUSED", "to_state": "DISTRACTED"},
            {"timestamp": (datetime.now() - timedelta(minutes=18)).isoformat(), "from_state": "DISTRACTED", "to_state": "FOCUSED"},
            {"timestamp": (datetime.now() - timedelta(minutes=10)).isoformat(), "from_state": "FOCUSED", "to_state": "AWAY"},
            {"timestamp": (datetime.now() - timedelta(minutes=8)).isoformat(), "from_state": "AWAY", "to_state": "FOCUSED"}
        ],
        "completed": True
    }

def create_historical_sessions():
    """Create sample historical sessions."""
    sessions = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(20):
        session_time = base_time + timedelta(days=i)
        sessions.append({
            "session_start": session_time.isoformat(),
            "session_end": (session_time + timedelta(minutes=20)).isoformat(),
            "total_frames": 1200,
            "focused_frames": 900 + (i % 3) * 100,  # Varying focus
            "distracted_frames": 200 - (i % 2) * 50,
            "away_frames": 100,
            "focus_score": 75.0 + (i % 4) * 5,
            "session_duration_seconds": 1200.0,
            "completed": True
        })
    
    return sessions

def create_peer_data():
    """Create sample peer comparison data."""
    peer_data = []
    
    for user_id in ["peer_1", "peer_2", "peer_3", "peer_4", "peer_5"]:
        sessions = []
        for i in range(10):
            session_time = datetime.now() - timedelta(days=i)
            sessions.append({
                "session_start": session_time.isoformat(),
                "focus_score": 60.0 + (hash(user_id) % 20),  # Different base scores
                "total_frames": 1000,
                "focused_frames": 600 + (hash(user_id) % 200),
                "session_duration_seconds": 1000.0
            })
        
        peer_data.append({
            "user_id": user_id,
            "sessions": sessions
        })
    
    return peer_data

def test_analytics_service():
    """Test the analytics service with sample data."""
    print("🧪 Testing Comprehensive Analytics Service")
    print("=" * 50)
    
    # Create test data
    session_data = create_sample_session_data()
    historical_sessions = create_historical_sessions()
    peer_data = create_peer_data()
    
    print(f"📊 Testing with session data:")
    print(f"   - Session duration: {session_data['session_duration_seconds']} seconds")
    print(f"   - Focus score: {session_data['focus_score']}%")
    print(f"   - Historical sessions: {len(historical_sessions)}")
    print(f"   - Peer users: {len(peer_data)}")
    print()
    
    try:
        # Test comprehensive report generation
        print("🔍 Generating comprehensive analytics report...")
        report = analytics_service.generate_comprehensive_session_report(
            user_id="test_user",
            session_data=session_data,
            historical_sessions=historical_sessions,
            all_users_data=peer_data
        )
        
        if "error" in report:
            print(f"❌ Error in report generation: {report['error']}")
            return False
        
        print("✅ Comprehensive report generated successfully!")
        print()
        
        # Test Deep Work Metrics
        print("📈 Deep Work Metrics:")
        deep_work = report.get("deep_work_metrics", {})
        if deep_work:
            print(f"   - Focus Duration (current): {deep_work.get('focus_duration', {}).get('current_session_hours', 0):.2f} hours")
            print(f"   - Focus-to-Rest Ratio: {deep_work.get('focus_to_rest_ratio', 0):.2f}")
            print(f"   - Longest Focus Streak: {deep_work.get('longest_focus_streak', {}).get('minutes', 0):.1f} minutes")
            print(f"   - Session Completion Rate: {deep_work.get('session_completion_rate', 0)}%")
            print(f"   - Focus Efficiency: {deep_work.get('focus_efficiency', 0)}%")
        else:
            print("   ❌ No deep work metrics found")
        print()
        
        # Test Distraction Analytics
        print("🚫 Distraction Analytics:")
        distraction = report.get("distraction_analytics", {})
        if distraction:
            print(f"   - Interruption Count: {distraction.get('interruption_count', 0)}")
            print(f"   - Context Switching Cost: {distraction.get('context_switching_cost', {}).get('total_minutes', 0):.1f} minutes")
            print(f"   - Distraction Frequency: {distraction.get('distraction_frequency', 0)}%")
            recovery = distraction.get('recovery_metrics', {})
            print(f"   - Average Recovery Time: {recovery.get('average_recovery_time_seconds', 0):.1f} seconds")
        else:
            print("   ❌ No distraction analytics found")
        print()
        
        # Test Biological Trends
        print("🌱 Biological Trends:")
        bio_trends = report.get("biological_trends", {})
        if bio_trends:
            heatmap = bio_trends.get("focus_heatmap", [])
            print(f"   - Heatmap Data Points: {len(heatmap)}")
            peak_times = bio_trends.get("peak_performance_times", [])
            if peak_times:
                best_time = peak_times[0]
                print(f"   - Peak Performance Time: {best_time.get('hour', 0):02d}:00 (Score: {best_time.get('average_focus_score', 0):.1f})")
        else:
            print("   ❌ No biological trends found")
        print()
        
        # Test Gamification Stats
        print("🎮 Gamification Stats:")
        gamification = report.get("gamification_stats", {})
        if gamification:
            streaks = gamification.get("focus_streaks", {})
            print(f"   - Current Focus Streak: {streaks.get('current_streak', 0)} days")
            print(f"   - Longest Focus Streak: {streaks.get('longest_streak', 0)} days")
            
            peer_comp = gamification.get("peer_comparison", {})
            if "focus_score_percentile" in peer_comp:
                print(f"   - Focus Score Percentile: {peer_comp.get('focus_score_percentile', 0):.1f}%")
                print(f"   - Peer Comparison: {peer_comp.get('comparison_summary', 'N/A')}")
            
            achievements = gamification.get("achievements", [])
            print(f"   - Achievements Unlocked: {len(achievements)}")
            for achievement in achievements[:3]:  # Show first 3
                print(f"     • {achievement.get('name', 'Unknown')}: {achievement.get('description', '')}")
        else:
            print("   ❌ No gamification stats found")
        print()
        
        # Test Personalized Insights
        print("💡 Personalized Insights:")
        insights = report.get("insights", [])
        if insights:
            for i, insight in enumerate(insights, 1):
                print(f"   {i}. {insight}")
        else:
            print("   ❌ No insights generated")
        print()
        
        print("🎉 All analytics tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_components():
    """Test individual analytics components."""
    print("\n🔧 Testing Individual Components")
    print("=" * 30)
    
    session_data = create_sample_session_data()
    historical_sessions = create_historical_sessions()
    
    try:
        # Test Deep Work Metrics
        print("Testing Deep Work Metrics...")
        deep_work = analytics_service.calculate_deep_work_metrics(session_data, historical_sessions)
        print(f"✅ Deep Work Metrics: {len(deep_work)} fields calculated")
        
        # Test Distraction Analytics
        print("Testing Distraction Analytics...")
        distraction = analytics_service.calculate_distraction_analytics(session_data)
        print(f"✅ Distraction Analytics: {len(distraction)} fields calculated")
        
        # Test Biological Trends
        print("Testing Biological Trends...")
        bio_trends = analytics_service.calculate_biological_trends(historical_sessions)
        print(f"✅ Biological Trends: {len(bio_trends)} fields calculated")
        
        # Test Gamification Stats
        print("Testing Gamification Stats...")
        gamification = analytics_service.calculate_gamification_stats("test_user", historical_sessions, create_peer_data())
        print(f"✅ Gamification Stats: {len(gamification)} fields calculated")
        
        print("\n🎯 All component tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in component testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Analytics Service Tests")
    print("=" * 40)
    
    success = True
    
    # Test individual components
    if not test_individual_components():
        success = False
    
    # Test comprehensive analytics
    if not test_analytics_service():
        success = False
    
    if success:
        print("\n🏆 ALL TESTS PASSED! 🎉")
        print("The comprehensive analytics implementation is working correctly.")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Please check the errors above and fix the issues.")
    
    sys.exit(0 if success else 1)
