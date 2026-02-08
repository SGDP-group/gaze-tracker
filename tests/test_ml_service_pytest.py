"""
Pytest-based ML service tests.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.services.ml_service import PersonalizedMLService
from src.database.models import UserSession, UserFeedback, UserModel, FocusRecommendation


class TestPersonalizedMLService:
    """Test PersonalizedMLService functionality."""
    
    @pytest.fixture
    def ml_service(self):
        """Create ML service instance."""
        return PersonalizedMLService()
    
    @pytest.mark.unit
    def test_get_or_create_user_model_new_user(self, ml_service, db_session, test_user):
        """Test creating model for new user."""
        model = ml_service.get_or_create_user_model(db_session, test_user.user_id)
        
        assert model is not None
        assert model.user_id == test_user.user_id
        assert model.is_base_model is True
        assert model.model_version == 1
        assert model.is_active is True
    
    @pytest.mark.unit
    def test_get_or_create_user_model_existing_user(self, ml_service, db_session, test_user):
        """Test getting existing user model."""
        # Create initial model
        first_model = ml_service.get_or_create_user_model(db_session, test_user.user_id)
        
        # Get same model again
        second_model = ml_service.get_or_create_user_model(db_session, test_user.user_id)
        
        assert second_model.id == first_model.id
        assert second_model.model_version == first_model.model_version
    
    @pytest.mark.unit
    def test_prepare_training_data_insufficient_data(self, ml_service, db_session, test_user):
        """Test preparing training data with insufficient sessions."""
        X, y = ml_service.prepare_training_data(db_session, test_user.user_id)
        
        # Should return synthetic data
        assert X.shape == (100, 4)  # 100 samples, 4 features
        assert y.shape == (100,)
        assert len(set(y)) == 2  # Binary classification
    
    @pytest.mark.unit
    def test_prepare_training_data_with_feedback(self, ml_service, db_session, multiple_sessions_with_feedback):
        """Test preparing training data with real user feedback."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        X, y = ml_service.prepare_training_data(db_session, sessions[0].user_id)
        
        assert X.shape[0] == len(sessions)
        assert X.shape[1] == 4  # 4 features
        assert y.shape[0] == len(sessions)
        assert len(set(y)) == 2  # Binary classification
        
        # Check that ratings are properly converted to binary labels
        expected_labels = [1, 1, 1, 0, 0]  # First 3 are productive (rating >= 3)
        assert list(y) == expected_labels
    
    @pytest.mark.unit
    def test_train_personalized_model_insufficient_data(self, ml_service, db_session, test_user):
        """Test training model with insufficient data."""
        result = ml_service.train_personalized_model(db_session, test_user.user_id)
        
        assert result["message"] == "Not enough new data for retraining"
        assert "model_version" in result
    
    @pytest.mark.unit
    def test_train_personalized_model_success(self, ml_service, db_session, multiple_sessions_with_feedback):
        """Test successful model training."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        result = ml_service.train_personalized_model(db_session, sessions[0].user_id, force_retrain=True)
        
        assert result["model_version"] >= 1
        assert result["training_sessions_count"] == len(sessions)
        assert "training_accuracy" in result
        assert "feature_importance" in result
        assert "training_time_seconds" in result
        assert "Successfully trained" in result["message"]
    
    @pytest.mark.unit
    def test_predict_session_productivity_base_model(self, ml_service, db_session, test_user):
        """Test prediction using base model."""
        session_features = {
            'angle_variance': 15.0,
            'stability_score': 0.8,
            'presence_ratio': 0.9,
            'context_switches': 3
        }
        
        prediction, confidence = ml_service.predict_session_productivity(
            db_session, test_user.user_id, session_features
        )
        
        assert prediction in ["Productive Session", "Unproductive/Fragmented Session"]
        assert 0 <= confidence <= 1
    
    @pytest.mark.unit
    def test_predict_session_productivity_personalized_model(self, ml_service, db_session, multiple_sessions_with_feedback):
        """Test prediction using personalized model."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        # Train model first
        ml_service.train_personalized_model(db_session, sessions[0].user_id, force_retrain=True)
        
        session_features = {
            'angle_variance': 15.0,
            'stability_score': 0.8,
            'presence_ratio': 0.9,
            'context_switches': 3
        }
        
        prediction, confidence = ml_service.predict_session_productivity(
            db_session, sessions[0].user_id, session_features
        )
        
        assert prediction in ["Productive Session", "Unproductive/Fragmented Session"]
        assert 0 <= confidence <= 1
    
    @pytest.mark.unit
    def test_generate_focus_recommendations_insufficient_data(self, ml_service, db_session, test_user):
        """Test generating recommendations with insufficient data."""
        recommendations = ml_service.generate_focus_recommendations(db_session, test_user.user_id)
        
        assert len(recommendations) == 1
        assert recommendations[0]["recommended_time_of_day"] == "morning"
        assert recommendations[0]["recommended_duration_minutes"] == 45
        assert recommendations[0]["confidence_score"] == 0.3
        assert "general recommendation" in recommendations[0]["reasoning"].lower()
    
    @pytest.mark.unit
    def test_generate_focus_recommendations_with_data(self, ml_service, db_session, multiple_sessions_with_feedback):
        """Test generating recommendations with user data."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        recommendations = ml_service.generate_focus_recommendations(db_session, sessions[0].user_id)
        
        assert len(recommendations) >= 1
        rec = recommendations[0]
        assert rec["recommended_time_of_day"] in ["morning", "afternoon", "evening"]
        assert rec["recommended_duration_minutes"] > 0
        assert 0 <= rec["confidence_score"] <= 1
        assert "reasoning" in rec
        assert "based_on_sessions" in rec
    
    @pytest.mark.unit
    def test_get_user_statistics_no_sessions(self, ml_service, db_session, test_user):
        """Test getting statistics for user with no sessions."""
        stats = ml_service.get_user_statistics(db_session, test_user.user_id)
        
        assert stats["total_sessions"] == 0
        assert stats["total_duration_hours"] == 0
        assert stats["average_focus_score"] == 0
        assert stats["most_productive_time"] is None
        assert stats["productivity_trend"] == "stable"
    
    @pytest.mark.unit
    def test_get_user_statistics_with_sessions(self, ml_service, db_session, multiple_sessions_with_feedback):
        """Test getting statistics for user with sessions."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        stats = ml_service.get_user_statistics(db_session, sessions[0].user_id)
        
        assert stats["total_sessions"] == len(sessions)
        assert stats["total_duration_hours"] > 0
        assert stats["average_focus_score"] > 0
        assert stats["productivity_trend"] in ["improving", "declining", "stable"]
    
    @pytest.mark.unit
    def test_feature_importance_extraction(self, ml_service, db_session, multiple_sessions_with_feedback):
        """Test feature importance extraction."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        result = ml_service.train_personalized_model(db_session, sessions[0].user_id, force_retrain=True)
        
        feature_importance = result["feature_importance"]
        
        assert isinstance(feature_importance, dict)
        assert len(feature_importance) == 4  # 4 features
        assert all(0 <= importance <= 1 for importance in feature_importance.values())
        
        # Check feature names
        expected_features = ['angle_variance', 'stability_score', 'presence_ratio', 'context_switches']
        for feature in expected_features:
            assert feature in feature_importance
    
    @pytest.mark.unit
    def test_model_versioning(self, ml_service, db_session, multiple_sessions_with_feedback):
        """Test model versioning system."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        # Train first model
        result1 = ml_service.train_personalized_model(db_session, sessions[0].user_id, force_retrain=True)
        version1 = result1["model_version"]
        
        # Train second model
        result2 = ml_service.train_personalized_model(db_session, sessions[0].user_id, force_retrain=True)
        version2 = result2["model_version"]
        
        assert version2 == version1 + 1
        
        # Check that only latest model is active
        active_models = db_session.query(UserModel).filter(
            UserModel.user_id == sessions[0].user_id,
            UserModel.is_active == True
        ).all()
        
        assert len(active_models) == 1
        assert active_models[0].model_version == version2


class TestMLServiceEdgeCases:
    """Test ML service edge cases and error handling."""
    
    @pytest.fixture
    def ml_service(self):
        """Create ML service instance."""
        return PersonalizedMLService()
    
    @pytest.mark.unit
    def test_handle_missing_session_features(self, ml_service, db_session, test_user):
        """Test handling sessions with missing features."""
        # Create session with missing features
        session = UserSession(
            user_id=test_user.user_id,
            session_id="incomplete_session",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_seconds=1800.0,
            total_frames=900,
            focused_frames=675,
            distracted_frames=135,
            away_frames=90,
            focus_score=75.0,
            # Missing angle_variance, stability_score, etc.
        )
        db_session.add(session)
        
        # Create feedback
        feedback = UserFeedback(
            user_id=test_user.user_id,
            session_id="incomplete_session",
            productivity_rating=4
        )
        db_session.add(feedback)
        db_session.commit()
        
        # Should handle missing features gracefully
        X, y = ml_service.prepare_training_data(db_session, test_user.user_id)
        
        assert X.shape[0] == 1  # One session
        assert X.shape[1] == 4  # 4 features (with defaults)
    
    @pytest.mark.unit
    def test_extreme_rating_values(self, ml_service, db_session, test_user):
        """Test handling extreme rating values."""
        # Create session with extreme rating
        session = UserSession(
            user_id=test_user.user_id,
            session_id="extreme_session",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_seconds=1800.0,
            total_frames=900,
            focused_frames=675,
            distracted_frames=135,
            away_frames=90,
            focus_score=75.0,
            angle_variance=15.0,
            stability_score=0.8,
            presence_ratio=0.9,
            context_switches=3
        )
        db_session.add(session)
        
        # Create feedback with rating 1 (lowest)
        feedback = UserFeedback(
            user_id=test_user.user_id,
            session_id="extreme_session",
            productivity_rating=1
        )
        db_session.add(feedback)
        db_session.commit()
        
        X, y = ml_service.prepare_training_data(db_session, test_user.user_id)
        
        assert y[0] == 0  # Should be classified as unproductive
    
    @pytest.mark.unit
    def test_single_session_training(self, ml_service, db_session, test_user):
        """Test training with only one session."""
        # Create single session
        session = UserSession(
            user_id=test_user.user_id,
            session_id="single_session",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_seconds=1800.0,
            total_frames=900,
            focused_frames=675,
            distracted_frames=135,
            away_frames=90,
            focus_score=75.0,
            angle_variance=15.0,
            stability_score=0.8,
            presence_ratio=0.9,
            context_switches=3
        )
        db_session.add(session)
        
        feedback = UserFeedback(
            user_id=test_user.user_id,
            session_id="single_session",
            productivity_rating=4
        )
        db_session.add(feedback)
        db_session.commit()
        
        # Should fall back to synthetic data
        X, y = ml_service.prepare_training_data(db_session, test_user.user_id)
        
        assert X.shape[0] == 100  # Synthetic data
        assert y.shape[0] == 100
    
    @pytest.mark.unit
    def test_recommendation_time_analysis(self, ml_service, db_session, test_user):
        """Test time-based recommendation analysis."""
        # Create sessions at different times
        times = [
            datetime.utcnow().replace(hour=8),   # Morning
            datetime.utcnow().replace(hour=14),  # Afternoon
            datetime.utcnow().replace(hour=20),  # Evening
        ]
        
        for i, start_time in enumerate(times):
            session = UserSession(
                user_id=test_user.user_id,
                session_id=f"time_session_{i+1}",
                start_time=start_time,
                end_time=start_time + timedelta(minutes=30),
                duration_seconds=1800.0,
                total_frames=900,
                focused_frames=675,
                distracted_frames=135,
                away_frames=90,
                focus_score=75.0,
                angle_variance=15.0,
                stability_score=0.8,
                presence_ratio=0.9,
                context_switches=3
            )
            db_session.add(session)
            
            feedback = UserFeedback(
                user_id=test_user.user_id,
                session_id=f"time_session_{i+1}",
                productivity_rating=4 if i == 0 else 2  # Morning is most productive
            )
            db_session.add(feedback)
        
        db_session.commit()
        
        recommendations = ml_service.generate_focus_recommendations(db_session, test_user.user_id)
        
        assert len(recommendations) >= 1
        # Should recommend morning as most productive time
        assert recommendations[0]["recommended_time_of_day"] == "morning"
