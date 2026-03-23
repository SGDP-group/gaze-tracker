"""
Tests for focus tracking API endpoints.
"""

import pytest
import base64
import io
import json
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np

from server import app
from src.services.focus_service import focus_tracker

class TestFocusTrackingAPI:
    """Test focus tracking API endpoints."""
    
    @pytest.fixture
    def sample_frame_data(self):
        """Create a sample frame for testing."""
        # Create a simple test image (100x100 pixels)
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Convert to base64
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{img_base64}"
    
    @pytest.fixture
    def test_user_id(self):
        """Test user ID."""
        return "test_user_focus_123"
    
    def test_start_focus_session(self, test_user_id):
        """Test starting a focus session."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/focus/session/start",
                json={
                    "user_id": test_user_id,
                    "session_name": "Test Session"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == test_user_id
            assert data["status"] == "active"
            assert "session_id" in data
    
    def test_analyze_focus_frame_no_face(self, sample_frame_data, test_user_id):
        """Test frame analysis with no face detected."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/focus/analyze",
                json={
                    "user_id": test_user_id,
                    "frame_data": sample_frame_data,
                    "image_width": 100,
                    "image_height": 100
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == test_user_id
            assert data["current_state"] == "AWAY"
            assert data["focus_score"] == 0.0
            assert data["face_metrics"] is None
    
    def test_analyze_focus_frame_with_session(self, sample_frame_data, test_user_id):
        """Test frame analysis with active session."""
        with TestClient(app) as client:
            # Start session first
            client.post(
                "/api/v1/focus/session/start",
                json={"user_id": test_user_id}
            )
            
            # Analyze frame
            response = client.post(
                "/api/v1/focus/analyze",
                json={
                    "user_id": test_user_id,
                    "frame_data": sample_frame_data,
                    "image_width": 100,
                    "image_height": 100
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == test_user_id
            assert "session_stats" in data
            assert data["session_stats"]["total_frames"] >= 1
    
    def test_get_session_data(self, test_user_id):
        """Test getting session data."""
        with TestClient(app) as client:
            # Start session
            client.post(
                "/api/v1/focus/session/start",
                json={"user_id": test_user_id}
            )
            
            # Get session data
            response = client.get(f"/api/v1/focus/session/{test_user_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == test_user_id
            assert "session_start" in data
            assert "total_frames" in data
    
    def test_get_session_data_not_found(self):
        """Test getting session data for non-existent user."""
        with TestClient(app) as client:
            response = client.get("/api/v1/focus/session/nonexistent_user")
            
            assert response.status_code == 404
            assert "No session found" in response.json()["detail"]
    
    def test_end_focus_session(self, test_user_id):
        """Test ending a focus session."""
        with TestClient(app) as client:
            # Start session
            client.post(
                "/api/v1/focus/session/start",
                json={"user_id": test_user_id}
            )
            
            # End session
            response = client.post(
                "/api/v1/focus/session/end",
                params={"user_id": test_user_id}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == test_user_id
            assert "session_start" in data
            assert "session_end" in data
    
    def test_end_session_not_found(self):
        """Test ending session for non-existent user."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/focus/session/end",
                params={"user_id": "nonexistent_user"}
            )
            
            assert response.status_code == 404
            assert "No active session found" in response.json()["detail"]
    
    def test_get_active_users(self, test_user_id):
        """Test getting list of active users."""
        with TestClient(app) as client:
            # Start sessions for multiple users
            users = [f"{test_user_id}_{i}" for i in range(3)]
            
            for user_id in users:
                client.post(
                    "/api/v1/focus/session/start",
                    json={"user_id": user_id}
                )
            
            # Get active users
            response = client.get("/api/v1/focus/users/active")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] >= 3
            assert len(data["active_users"]) >= 3
    
    def test_cleanup_inactive_sessions(self, test_user_id):
        """Test cleaning up inactive sessions."""
        with TestClient(app) as client:
            # Start session
            client.post(
                "/api/v1/focus/session/start",
                json={"user_id": test_user_id}
            )
            
            # Cleanup (should not remove active session)
            response = client.post("/api/v1/focus/cleanup")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "active_users" in data
    
    def test_focus_health_check(self):
        """Test focus service health check."""
        with TestClient(app) as client:
            response = client.get("/api/v1/focus/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "active_sessions" in data
            assert "service_version" in data
    
    def test_invalid_frame_data(self, test_user_id):
        """Test handling of invalid frame data."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/focus/analyze",
                json={
                    "user_id": test_user_id,
                    "frame_data": "invalid_base64_data",
                    "image_width": 100,
                    "image_height": 100
                }
            )
            
            # Should handle error gracefully
            assert response.status_code in [400, 500]
    
    def test_missing_required_fields(self, test_user_id):
        """Test requests with missing required fields."""
        with TestClient(app) as client:
            # Missing frame_data
            response = client.post(
                "/api/v1/focus/analyze",
                json={
                    "user_id": test_user_id,
                    "image_width": 100,
                    "image_height": 100
                }
            )
            
            assert response.status_code == 422  # Validation error
            
            # Missing user_id
            response = client.post(
                "/api/v1/focus/analyze",
                json={
                    "frame_data": "data:image/jpeg;base64,test",
                    "image_width": 100,
                    "image_height": 100
                }
            )
            
            assert response.status_code == 422  # Validation error


class TestFocusServiceIntegration:
    """Test focus service integration."""
    
    def test_multiple_users_concurrent(self):
        """Test concurrent tracking of multiple users."""
        # This test verifies that user sessions are properly separated
        user1 = "user1"
        user2 = "user2"
        
        # Start sessions for both users
        focus_tracker.update_user_session(user1, None)
        focus_tracker.update_user_session(user2, None)
        
        # Verify sessions are separate
        assert user1 in focus_tracker.user_sessions
        assert user2 in focus_tracker.user_sessions
        assert focus_tracker.user_sessions[user1]["user_id"] == user1
        assert focus_tracker.user_sessions[user2]["user_id"] == user2
        assert focus_tracker.user_sessions[user1] is not focus_tracker.user_sessions[user2]
        
        # Clean up
        focus_tracker.end_user_session(user1)
        focus_tracker.end_user_session(user2)
    
    def test_session_persistence(self):
        """Test that session data persists across multiple frames."""
        user_id = "persistence_test_user"
        
        # Start session
        focus_tracker.update_user_session(user_id, None)
        
        # Send multiple frames
        for i in range(5):
            focus_tracker.update_user_session(user_id, None)
        
        # Check session data
        session_data = focus_tracker.get_user_session_data(user_id)
        assert session_data is not None
        assert session_data["total_frames"] == 6
        
        # Clean up
        focus_tracker.end_user_session(user_id)
    
    def test_baseline_angle_adaptation(self):
        """Test baseline angle adaptation over time."""
        user_id = "baseline_test_user"
        
        # Start session
        focus_tracker.update_user_session(user_id, None)
        
        # Simulate consistent angle
        fake_metrics = {
            "angle": 15.0,
            "confidence": 0.8,
            "timestamp": "2024-01-01T00:00:00"
        }
        
        initial_baseline = focus_tracker.user_sessions[user_id]["baseline_angle"]
        
        # Update with consistent angle
        for i in range(10):
            focus_tracker.update_user_session(user_id, fake_metrics)
        
        # Check that baseline adapted
        final_baseline = focus_tracker.user_sessions[user_id]["baseline_angle"]
        assert abs(final_baseline - 15.0) < abs(initial_baseline - 15.0)
        
        # Clean up
        focus_tracker.end_user_session(user_id)


class TestMultiUserIsolation:
    """Comprehensive tests for multi-user session isolation in the focus algorithm."""

    def setup_method(self):
        """Clean up any leftover sessions before each test."""
        for uid in list(focus_tracker.user_sessions.keys()):
            focus_tracker.end_user_session(uid)

    def teardown_method(self):
        """Clean up sessions after each test."""
        for uid in list(focus_tracker.user_sessions.keys()):
            focus_tracker.end_user_session(uid)

    def test_interleaved_frames_independent_counts(self):
        """Interleaved frame processing must keep frame counts independent per user."""
        user_a = "iso_user_a"
        user_b = "iso_user_b"

        # User A: 3 frames, User B: 7 frames, interleaved
        focus_tracker.update_user_session(user_a, None)
        focus_tracker.update_user_session(user_b, None)
        focus_tracker.update_user_session(user_a, None)
        focus_tracker.update_user_session(user_b, None)
        focus_tracker.update_user_session(user_b, None)
        focus_tracker.update_user_session(user_a, None)
        focus_tracker.update_user_session(user_b, None)
        focus_tracker.update_user_session(user_b, None)
        focus_tracker.update_user_session(user_b, None)
        focus_tracker.update_user_session(user_b, None)

        data_a = focus_tracker.get_user_session_data(user_a)
        data_b = focus_tracker.get_user_session_data(user_b)

        assert data_a["total_frames"] == 3
        assert data_b["total_frames"] == 7

    def test_different_angles_independent_baselines(self):
        """Users with different head angles must have independent baselines."""
        user_a = "baseline_iso_a"
        user_b = "baseline_iso_b"

        metrics_a = {"angle": 10.0, "confidence": 0.9, "timestamp": "2024-01-01T00:00:00"}
        metrics_b = {"angle": 80.0, "confidence": 0.9, "timestamp": "2024-01-01T00:00:00"}

        for _ in range(20):
            focus_tracker.update_user_session(user_a, metrics_a)
            focus_tracker.update_user_session(user_b, metrics_b)

        baseline_a = focus_tracker.user_sessions[user_a]["baseline_angle"]
        baseline_b = focus_tracker.user_sessions[user_b]["baseline_angle"]

        # Baselines should have diverged toward their respective angles
        assert baseline_a < 30, f"User A baseline {baseline_a} should be near 10"
        assert baseline_b > 50, f"User B baseline {baseline_b} should be near 80"

    def test_one_user_focused_other_away(self):
        """One user focused while other is away — states must not bleed."""
        user_a = "state_iso_a"
        user_b = "state_iso_b"

        metrics_focused = {"angle": 0.0, "confidence": 0.9, "timestamp": "2024-01-01T00:00:00"}

        for _ in range(10):
            focus_tracker.update_user_session(user_a, metrics_focused)  # face detected
            focus_tracker.update_user_session(user_b, None)              # no face

        session_a = focus_tracker.user_sessions[user_a]
        session_b = focus_tracker.user_sessions[user_b]

        assert session_a["current_state"] == "FOCUSED"
        assert session_b["current_state"] == "AWAY"
        assert session_a["away_frames"] == 0
        assert session_b["focused_frames"] == 0

    def test_ending_one_session_preserves_other(self):
        """Ending one user's session must not affect another user's session."""
        user_a = "end_iso_a"
        user_b = "end_iso_b"

        metrics = {"angle": 5.0, "confidence": 0.9, "timestamp": "2024-01-01T00:00:00"}

        for _ in range(5):
            focus_tracker.update_user_session(user_a, metrics)
            focus_tracker.update_user_session(user_b, metrics)

        # End user A
        end_data = focus_tracker.end_user_session(user_a)
        assert end_data is not None
        assert end_data["total_frames"] == 5

        # User B must still be active and unaffected
        assert user_b in focus_tracker.user_sessions
        assert user_a not in focus_tracker.user_sessions
        data_b = focus_tracker.get_user_session_data(user_b)
        assert data_b["total_frames"] == 5

    def test_focus_scores_independent(self):
        """Focus scores must be computed independently per user."""
        user_a = "score_iso_a"
        user_b = "score_iso_b"

        metrics_focused = {"angle": 0.0, "confidence": 0.9, "timestamp": "2024-01-01T00:00:00"}

        # User A: all focused frames
        for _ in range(10):
            focus_tracker.update_user_session(user_a, metrics_focused)

        # User B: all away frames
        for _ in range(10):
            focus_tracker.update_user_session(user_b, None)

        data_a = focus_tracker.get_user_session_data(user_a)
        data_b = focus_tracker.get_user_session_data(user_b)

        assert data_a["focus_score"] == 100.0
        assert data_b["focus_score"] == 0.0

    def test_frame_counts_always_sum_correctly(self):
        """focused + distracted + away must equal total_frames for each user."""
        user_a = "sum_iso_a"
        user_b = "sum_iso_b"

        metrics_focused = {"angle": 0.0, "confidence": 0.9, "timestamp": "2024-01-01T00:00:00"}
        metrics_large_angle = {"angle": 90.0, "confidence": 0.9, "timestamp": "2024-01-01T00:00:00"}

        # User A: mix of focused and away
        for i in range(20):
            if i % 3 == 0:
                focus_tracker.update_user_session(user_a, None)
            else:
                focus_tracker.update_user_session(user_a, metrics_focused)

        # User B: mix of focused and large-angle
        for i in range(15):
            if i % 2 == 0:
                focus_tracker.update_user_session(user_b, metrics_large_angle)
            else:
                focus_tracker.update_user_session(user_b, metrics_focused)

        for uid in [user_a, user_b]:
            s = focus_tracker.user_sessions[uid]
            total = s["focused_frames"] + s["distracted_frames"] + s["away_frames"]
            assert total == s["total_frames"], (
                f"User {uid}: {s['focused_frames']}+{s['distracted_frames']}+"
                f"{s['away_frames']}={total} != {s['total_frames']}"
            )

    def test_many_concurrent_users(self):
        """Stress test: 20 concurrent users with interleaved updates."""
        num_users = 20
        frames_per_user = 15
        user_ids = [f"stress_user_{i}" for i in range(num_users)]

        metrics_list = [
            {"angle": float(i * 4), "confidence": 0.9, "timestamp": "2024-01-01T00:00:00"}
            for i in range(num_users)
        ]

        # Interleave frames across all users
        for frame_idx in range(frames_per_user):
            for i, uid in enumerate(user_ids):
                if frame_idx % 5 == 0:
                    focus_tracker.update_user_session(uid, None)
                else:
                    focus_tracker.update_user_session(uid, metrics_list[i])

        # Verify each user has correct independent frame count
        for uid in user_ids:
            data = focus_tracker.get_user_session_data(uid)
            assert data is not None
            assert data["total_frames"] == frames_per_user
            s = focus_tracker.user_sessions[uid]
            total = s["focused_frames"] + s["distracted_frames"] + s["away_frames"]
            assert total == frames_per_user


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
