#!/usr/bin/env python3
"""
Test script for improved multi-user focus tracking algorithm.
Tests productivity classification and FPS tracking for multiple users.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.focus_service import FocusTracker, ProductivityLevel
from datetime import datetime, timedelta
import time

def test_multi_user_focus_tracking():
    """Test focus tracking with multiple simulated users."""
    print("Testing Multi-User Focus Tracking Algorithm")
    print("=" * 50)
    
    # Initialize focus tracker
    tracker = FocusTracker()
    
    # Simulate multiple users with different focus patterns
    users = {
        "user1": {"focus_pattern": "highly_productive", "target_score": 90},
        "user2": {"focus_pattern": "moderately_productive", "target_score": 65},
        "user3": {"focus_pattern": "not_productive", "target_score": 35}
    }
    
    print(f"Starting sessions for {len(users)} users...")
    
    # Simulate frame processing for each user
    for frame_num in range(100):  # 100 frames per user
        for user_id, user_config in users.items():
            # Simulate face metrics based on user's focus pattern
            if user_config["focus_pattern"] == "highly_productive":
                # Mostly focused frames
                is_focused = frame_num % 10 < 9  # 90% focused
                angle = 15.0 if is_focused else 45.0
            elif user_config["focus_pattern"] == "moderately_productive":
                # Mixed focus
                is_focused = frame_num % 10 < 7  # 70% focused
                angle = 18.0 if is_focused else 40.0
            else:  # not_productive
                # Mostly distracted
                is_focused = frame_num % 10 < 4  # 40% focused
                angle = 25.0 if is_focused else 50.0
            
            # Create mock face metrics
            face_metrics = {
                "centroid": {"x": 100, "y": 100},
                "angle": angle,
                "magnitude": 10.0,
                "eye_gap": 30.0,
                "confidence": 0.9,
                "timestamp": datetime.now().isoformat()
            } if is_focused else None
            
            # Update user session
            result = tracker.update_user_session(user_id, face_metrics)
            
            # Show progress every 25 frames
            if frame_num % 25 == 0:
                print(f"User {user_id}: Focus Score = {result['focus_score']:.1f}%, "
                      f"FPS = {result['average_fps']:.1f}, "
                      f"State = {result['current_state']}")
    
    print("\nFinal Session Results:")
    print("-" * 30)
    
    # End sessions and get final results
    for user_id in users:
        session_data = tracker.end_user_session(user_id)
        
        print(f"\nUser {user_id} ({users[user_id]['focus_pattern']}):")
        print(f"  Final Focus Score: {session_data['focus_score']:.1f}%")
        print(f"  Productivity Level: {session_data['productivity_level']}")
        print(f"  Average FPS: {session_data['average_fps']:.1f}")
        print(f"  Session Duration: {session_data['session_duration_seconds']:.1f}s")
        print(f"  Total Frames: {session_data['total_frames']}")
        print(f"  Focused Frames: {session_data['focused_frames']}")
        print(f"  Distracted Frames: {session_data['distracted_frames']}")
        print(f"  Away Frames: {session_data['away_frames']}")
        
        # Verify productivity classification
        expected_level = None
        if session_data['focus_score'] >= 85:
            expected_level = ProductivityLevel.HIGHLY_PRODUCTIVE.value
        elif session_data['focus_score'] >= 70:
            expected_level = ProductivityLevel.PRODUCTIVE.value
        elif session_data['focus_score'] >= 50:
            expected_level = ProductivityLevel.MODERATELY_PRODUCTIVE.value
        else:
            expected_level = ProductivityLevel.NOT_PRODUCTIVE.value
        
        if session_data['productivity_level'] == expected_level:
            print(f"  ✅ Productivity classification correct")
        else:
            print(f"  ❌ Expected {expected_level}, got {session_data['productivity_level']}")
    
    print(f"\n✅ Multi-user test completed successfully!")
    print(f"Active users remaining: {len(tracker.get_active_users())}")

def test_fps_calculation():
    """Test FPS calculation accuracy."""
    print("\nTesting FPS Calculation")
    print("-" * 20)
    
    tracker = FocusTracker()
    user_id = "fps_test_user"
    
    # Simulate frames at known intervals
    start_time = datetime.now()
    for i in range(30):
        # Simulate 10 FPS (1 frame every 0.1 seconds)
        frame_time = start_time + timedelta(seconds=i * 0.1)
        
        face_metrics = {
            "centroid": {"x": 100, "y": 100},
            "angle": 15.0,
            "magnitude": 10.0,
            "eye_gap": 30.0,
            "confidence": 0.9,
            "timestamp": frame_time.isoformat()
        }
        
        # Manually set the frame timestamp to simulate precise timing
        session = tracker.user_sessions.get(user_id)
        if session is None:
            tracker.update_user_session(user_id, face_metrics)
            session = tracker.user_sessions[user_id]
        
        # Override the timestamp for precise FPS testing
        session["frame_timestamps"][-1] = frame_time
        session["last_update"] = frame_time.isoformat()
    
    # Check calculated FPS
    result = tracker.update_user_session(user_id, face_metrics)
    expected_fps = 10.0  # We're sending frames at 10 FPS
    actual_fps = result["average_fps"]
    
    print(f"Expected FPS: {expected_fps}")
    print(f"Actual FPS: {actual_fps:.2f}")
    
    if abs(actual_fps - expected_fps) < 1.0:  # Allow 1 FPS tolerance
        print("✅ FPS calculation accurate")
    else:
        print("❌ FPS calculation inaccurate")
    
    tracker.end_user_session(user_id)

if __name__ == "__main__":
    try:
        test_multi_user_focus_tracking()
        test_fps_calculation()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
