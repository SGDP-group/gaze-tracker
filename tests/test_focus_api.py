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

from src.api.main import app
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
        assert focus_tracker.user_sessions[user1]["user_id"] != focus_tracker.user_sessions[user2]["user_id"]
        
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
        assert session_data["total_frames"] == 5
        
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
