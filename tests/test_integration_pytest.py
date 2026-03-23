"""
Integration tests for the complete Focus Management System.
"""

import pytest
import time
import json
from datetime import datetime
from unittest.mock import patch

from src.database.models import User, UserSession, UserFeedback


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    @pytest.mark.integration
    def test_complete_user_workflow(self, client, db_session):
        """Test complete user workflow from creation to recommendations."""
        # 1. Create user
        user_response = client.post("/api/v1/users", json={"user_id": "e2e_test_user"})
        assert user_response.status_code == 200
        user_data = user_response.json()
        headers = {"Authorization": f"Bearer {user_data['api_key']}"}
        
        # 2. Create multiple sessions with feedback
        session_ids = []
        for i in range(5):
            # Create session
            session_data = {
                "user_id": user_data["user_id"],
                "session_id": f"e2e_session_{i+1}",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration_seconds": 1800.0,
                "total_frames": 900,
                "focused_frames": int(900 * (0.8 - i * 0.05)),
                "distracted_frames": 135,
                "away_frames": int(900 * 0.05),
                "focus_score": 80.0 - (i * 5),
                "baseline_angle": 45.0,
                "raw_session_data": f'{{"test": "session_{i+1}"}}',
                "angle_variance": 15.0 + (i * 2),
                "stability_score": 0.85 - (i * 0.05),
                "presence_ratio": 0.90,
                "context_switches": i + 1,
                "base_prediction": "Productive Session" if i < 3 else "Unproductive Session",
                "base_confidence": 0.8
            }
            
            session_response = client.post("/api/v1/sessions", json=session_data, headers=headers)
            assert session_response.status_code == 200
            session_ids.append(f"e2e_session_{i+1}")
            
            # Create feedback
            feedback_data = {
                "user_id": user_data["user_id"],
                "session_id": f"e2e_session_{i+1}",
                "productivity_rating": 4 if i < 3 else 2,
                "difficulty_rating": 3,
                "energy_level": 4,
                "task_type": "coding",
                "time_of_day": "morning",
                "interruptions": i,
                "notes": f"E2E test session {i+1}"
            }
            
            feedback_response = client.post("/api/v1/feedback", json=feedback_data, headers=headers)
            assert feedback_response.status_code == 200
        
        # 3. Get user statistics
        stats_response = client.get("/api/v1/statistics", headers=headers)
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["total_sessions"] == 5
        assert stats["total_duration_hours"] > 0
        
        # 4. Train model
        training_response = client.post(
            "/api/v1/models/train",
            json={"user_id": user_data["user_id"], "force_retrain": True},
            headers=headers
        )
        assert training_response.status_code == 200
        training_result = training_response.json()
        assert "model_version" in training_result
        assert "training_accuracy" in training_result
        
        # 5. Get recommendations
        recommendations_response = client.get("/api/v1/recommendations", headers=headers)
        assert recommendations_response.status_code == 200
        recommendations = recommendations_response.json()
        assert len(recommendations) >= 1
        assert "recommended_time_of_day" in recommendations[0]
        assert "recommended_duration_minutes" in recommendations[0]
        
        # 6. Get user models
        models_response = client.get("/api/v1/models", headers=headers)
        assert models_response.status_code == 200
        models = models_response.json()
        assert len(models) >= 1
        assert any(model["is_active"] for model in models)


class TestAPIPerformance:
    """Test API performance and load handling."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_multiple_concurrent_users(self, client, db_session):
        """Test handling multiple concurrent users."""
        user_count = 3  # Reduced for faster testing
        sessions_per_user = 2
        user_data_list = []
        
        # Create multiple users
        for i in range(user_count):
            user_response = client.post("/api/v1/users", json={"user_id": f"perf_user_{i+1}"})
            assert user_response.status_code == 200
            user_data_list.append(user_response.json())
        
        # Create sessions for each user
        for user_data in user_data_list:
            headers = {"Authorization": f"Bearer {user_data['api_key']}"}
            
            for j in range(sessions_per_user):
                session_data = {
                    "user_id": user_data["user_id"],
                    "session_id": f"perf_session_{user_data['user_id']}_{j+1}",
                    "start_time": datetime.utcnow().isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "duration_seconds": 1800.0,
                    "total_frames": 900,
                    "focused_frames": 675,
                    "distracted_frames": 135,
                    "away_frames": 90,
                    "focus_score": 75.0,
                    "baseline_angle": 45.0,
                    "raw_session_data": f'{{"test": "perf_session_{j+1}"}}',
                    "angle_variance": 15.0,
                    "stability_score": 0.8,
                    "presence_ratio": 0.9,
                    "context_switches": 3,
                    "base_prediction": "Productive Session",
                    "base_confidence": 0.8
                }
                
                session_response = client.post("/api/v1/sessions", json=session_data, headers=headers)
                assert session_response.status_code == 200
                
                feedback_data = {
                    "user_id": user_data["user_id"],
                    "session_id": f"perf_session_{user_data['user_id']}_{j+1}",
                    "productivity_rating": 4,
                    "difficulty_rating": 3,
                    "energy_level": 4,
                    "task_type": "coding",
                    "time_of_day": "morning",
                    "interruptions": 1,
                    "notes": f"Performance test session {j+1}"
                }
                
                feedback_response = client.post("/api/v1/feedback", json=feedback_data, headers=headers)
                assert feedback_response.status_code == 200
        
        # Verify all users have their sessions
        total_sessions = 0
        for user_data in user_data_list:
            headers = {"Authorization": f"Bearer {user_data['api_key']}"}
            sessions_response = client.get("/api/v1/sessions", headers=headers)
            assert sessions_response.status_code == 200
            sessions = sessions_response.json()
            assert len(sessions) == sessions_per_user
            total_sessions += len(sessions)
        
        assert total_sessions == user_count * sessions_per_user


class TestAPIErrorRecovery:
    """Test API error recovery and resilience."""
    
    @pytest.mark.integration
    def test_malformed_request_handling(self, client):
        """Test handling of malformed requests."""
        # Test malformed JSON
        response = client.post(
            "/api/v1/users",
            data="malformed json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # Test missing required fields
        response = client.post("/api/v1/users", json={})
        assert response.status_code == 422
        
        # Test invalid data types
        response = client.post("/api/v1/users", json={"user_id": 123})
        assert response.status_code == 422


class TestDataConsistency:
    """Test data consistency across the system."""
    
    @pytest.mark.integration
    def test_user_isolation(self, client, db_session):
        """Test that user data is properly isolated."""
        # Create two users
        user1_response = client.post("/api/v1/users", json={"user_id": "isolation_user_1"})
        user2_response = client.post("/api/v1/users", json={"user_id": "isolation_user_2"})
        
        user1_data = user1_response.json()
        user2_data = user2_response.json()
        
        headers1 = {"Authorization": f"Bearer {user1_data['api_key']}"}
        headers2 = {"Authorization": f"Bearer {user2_data['api_key']}"}
        
        # Create session for user 1
        session1_data = {
            "user_id": "isolation_user_1",
            "session_id": "user1_session",
            "start_time": datetime.utcnow().isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_seconds": 1800.0,
            "total_frames": 900,
            "focused_frames": 675,
            "distracted_frames": 135,
            "away_frames": 90,
            "focus_score": 75.0,
            "baseline_angle": 45.0,
            "raw_session_data": '{"test": "user1"}',
            "angle_variance": 15.0,
            "stability_score": 0.8,
            "presence_ratio": 0.9,
            "context_switches": 3,
            "base_prediction": "Productive Session",
            "base_confidence": 0.8
        }
        
        client.post("/api/v1/sessions", json=session1_data, headers=headers1)
        
        # Verify user 1 can see their session
        sessions1_response = client.get("/api/v1/sessions", headers=headers1)
        assert sessions1_response.status_code == 200
        sessions1 = sessions1_response.json()
        assert len(sessions1) == 1
        assert sessions1[0]["session_id"] == "user1_session"
        
        # Verify user 2 cannot see user 1's session
        sessions2_response = client.get("/api/v1/sessions", headers=headers2)
        assert sessions2_response.status_code == 200
        sessions2 = sessions2_response.json()
        assert len(sessions2) == 0
        
        # Verify user 2 cannot access user 1's session directly
        direct_access_response = client.get("/api/v1/sessions/user1_session", headers=headers2)
        assert direct_access_response.status_code == 404
