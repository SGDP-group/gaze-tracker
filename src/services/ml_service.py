"""
Personalized ML service with progressive learning and recommendations.
"""

import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report

from src.database.models import UserSession, UserFeedback, UserModel, FocusRecommendation
from src.utils import compute_session_features, SessionClassifier


class PersonalizedMLService:
    """Service for managing personalized ML models and recommendations."""
    
    def __init__(self):
        self.base_classifier = SessionClassifier()
        self.feature_names = [
            'angle_variance', 'stability_score', 'presence_ratio', 'context_switches'
        ]
    
    def get_or_create_user_model(self, db: Session, user_id: str) -> UserModel:
        """Get existing user model or create base model."""
        model = db.query(UserModel).filter(
            UserModel.user_id == user_id,
            UserModel.is_active == True
        ).order_by(UserModel.model_version.desc()).first()
        
        if not model:
            # Create base model
            model = UserModel(
                user_id=user_id,
                model_version=1,
                model_type="random_forest",
                training_sessions_count=0,
                last_trained=datetime.utcnow(),
                is_base_model=True,
                model_parameters=json.dumps({
                    'n_estimators': 100,
                    'max_depth': 5,
                    'random_state': 42
                })
            )
            db.add(model)
            db.commit()
            db.refresh(model)
        
        return model
    
    def prepare_training_data(self, db: Session, user_id: str) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data from user sessions with feedback."""
        # Get sessions with feedback
        sessions_with_feedback = db.query(UserSession).join(UserFeedback).filter(
            UserSession.user_id == user_id,
            UserFeedback.productivity_rating.isnot(None)
        ).all()
        
        if len(sessions_with_feedback) < 3:
            # Not enough data, use synthetic data
            return self._generate_synthetic_training_data()
        
        X = []
        y = []
        
        for session in sessions_with_feedback:
            # Extract features
            features = [
                session.angle_variance or 0,
                session.stability_score or 0,
                session.presence_ratio or 0,
                session.context_switches or 0
            ]
            X.append(features)
            
            # Convert rating to binary label (1-2 = Unproductive, 3-5 = Productive)
            rating = session.feedback[0].productivity_rating
            label = 1 if rating >= 3 else 0
            y.append(label)
        
        return np.array(X), np.array(y)
    
    def _generate_synthetic_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data for cold start."""
        np.random.seed(42)
        
        # Productive sessions
        productive_samples = []
        for _ in range(50):
            productive_samples.append([
                np.random.uniform(5, 20),    # angle_variance
                np.random.uniform(0.7, 1.0), # stability_score
                np.random.uniform(0.8, 1.0), # presence_ratio
                np.random.randint(0, 5)      # context_switches
            ])
        
        # Unproductive sessions
        unproductive_samples = []
        for _ in range(50):
            unproductive_samples.append([
                np.random.uniform(25, 60),   # angle_variance
                np.random.uniform(0.2, 0.6), # stability_score
                np.random.uniform(0.4, 0.8), # presence_ratio
                np.random.randint(8, 25)     # context_switches
            ])
        
        X = np.array(productive_samples + unproductive_samples)
        y = np.array([1] * 50 + [0] * 50)  # 1 = Productive, 0 = Unproductive
        
        return X, y
    
    def train_personalized_model(self, db: Session, user_id: str, force_retrain: bool = False) -> Dict:
        """Train personalized model for user."""
        start_time = datetime.utcnow()
        
        # Check if retraining is needed
        current_model = self.get_or_create_user_model(db, user_id)
        
        if not force_retrain and not current_model.is_base_model:
            # Check if we have enough new data to retrain
            new_sessions_count = db.query(UserSession).join(UserFeedback).filter(
                UserSession.user_id == user_id,
                UserFeedback.productivity_rating.isnot(None),
                UserSession.created_at > current_model.last_trained
            ).count()
            
            if new_sessions_count < 3:  # Need at least 3 new sessions
                return {
                    "message": "Not enough new data for retraining",
                    "model_version": current_model.model_version,
                    "training_sessions_count": current_model.training_sessions_count
                }
        
        # Prepare training data
        X, y = self.prepare_training_data(db, user_id)
        
        # Split data for validation
        if len(X) > 10:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
        else:
            X_train, X_val, y_train, y_val = X, np.array([]), y, np.array([])
        
        # Train model
        model_params = json.loads(current_model.model_parameters)
        model = RandomForestClassifier(**model_params)
        model.fit(X_train, y_train)
        
        # Calculate metrics
        training_accuracy = accuracy_score(y_train, model.predict(X_train))
        validation_accuracy = None
        if len(X_val) > 0:
            validation_accuracy = accuracy_score(y_val, model.predict(X_val))
        
        # Feature importance
        feature_importance = dict(zip(self.feature_names, model.feature_importances_))
        
        # Create new model version
        new_version = current_model.model_version + 1 if not current_model.is_base_model else 1
        
        # Deactivate old model
        current_model.is_active = False
        
        # Save new model
        new_model = UserModel(
            user_id=user_id,
            model_version=new_version,
            model_type="random_forest",
            training_sessions_count=len(X),
            last_trained=datetime.utcnow(),
            training_accuracy=training_accuracy,
            validation_accuracy=validation_accuracy,
            model_parameters=json.dumps(model_params),
            feature_importance=json.dumps(feature_importance),
            is_active=True,
            is_base_model=False
        )
        
        db.add(new_model)
        db.commit()
        db.refresh(new_model)
        
        training_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "model_version": new_version,
            "training_sessions_count": len(X),
            "training_accuracy": training_accuracy,
            "validation_accuracy": validation_accuracy,
            "feature_importance": feature_importance,
            "training_time_seconds": training_time,
            "message": f"Successfully trained model version {new_version}"
        }
    
    def predict_session_productivity(self, db: Session, user_id: str, session_features: Dict) -> Tuple[str, float]:
        """Predict session productivity using personalized model."""
        # Get user's active model
        model = db.query(UserModel).filter(
            UserModel.user_id == user_id,
            UserModel.is_active == True
        ).first()
        
        if not model or model.is_base_model:
            # Use base model
            return self.base_classifier.predict(session_features)
        
        # Load model parameters and create classifier
        model_params = json.loads(model.model_parameters)
        classifier = RandomForestClassifier(**model_params)
        
        # Load training data and retrain (simplified approach)
        X, y = self.prepare_training_data(db, user_id)
        classifier.fit(X, y)
        
        # Predict
        features = np.array([[
            session_features['angle_variance'],
            session_features['stability_score'],
            session_features['presence_ratio'],
            session_features['context_switches']
        ]])
        
        prediction = classifier.predict(features)[0]
        probabilities = classifier.predict_proba(features)[0]
        confidence = max(probabilities)
        
        label = "Productive Session" if prediction == 1 else "Unproductive/Fragmented Session"
        return label, confidence
    
    def generate_focus_recommendations(self, db: Session, user_id: str) -> List[Dict]:
        """Generate personalized focus time recommendations."""
        # Get user's successful sessions (high productivity rating)
        successful_sessions = db.query(UserSession).join(UserFeedback).filter(
            UserSession.user_id == user_id,
            UserFeedback.productivity_rating >= 4,  # High productivity
            UserSession.created_at >= datetime.utcnow() - timedelta(days=30)  # Last 30 days
        ).all()
        
        if len(successful_sessions) < 3:
            # Not enough data, provide general recommendations
            return self._get_general_recommendations()
        
        recommendations = []
        
        # Analyze time patterns
        time_patterns = {}
        duration_patterns = []
        
        for session in successful_sessions:
            # Extract time of day
            hour = session.start_time.hour
            if 6 <= hour < 12:
                time_period = "morning"
            elif 12 <= hour < 18:
                time_period = "afternoon"
            else:
                time_period = "evening"
            
            time_patterns[time_period] = time_patterns.get(time_period, 0) + 1
            duration_patterns.append(session.duration_seconds / 60)  # Convert to minutes
        
        # Find best time period
        best_time = max(time_patterns, key=time_patterns.get)
        
        # Calculate optimal duration (median of successful sessions)
        optimal_duration = int(np.median(duration_patterns))
        
        # Calculate confidence based on data consistency
        confidence = min(len(successful_sessions) / 10.0, 1.0)  # Max confidence at 10 sessions
        
        reasoning = f"Based on {len(successful_sessions)} successful sessions. " \
                   f"You perform best during {best_time} with sessions around {optimal_duration} minutes."
        
        recommendation = {
            "recommended_time_of_day": best_time,
            "recommended_duration_minutes": optimal_duration,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "based_on_sessions": [s.session_id for s in successful_sessions],
            "valid_from": datetime.utcnow(),
            "valid_until": datetime.utcnow() + timedelta(days=7)
        }
        
        recommendations.append(recommendation)
        
        # Save to database
        self._save_recommendations(db, user_id, recommendations)
        
        return recommendations
    
    def _get_general_recommendations(self) -> List[Dict]:
        """Get general recommendations when no user data available."""
        return [{
            "recommended_time_of_day": "morning",
            "recommended_duration_minutes": 45,
            "confidence_score": 0.3,
            "reasoning": "General recommendation based on typical productivity patterns. Collect more session data for personalized recommendations.",
            "based_on_sessions": [],
            "valid_from": datetime.utcnow(),
            "valid_until": datetime.utcnow() + timedelta(days=7)
        }]
    
    def _save_recommendations(self, db: Session, user_id: str, recommendations: List[Dict]):
        """Save recommendations to database."""
        # Deactivate old recommendations
        db.query(FocusRecommendation).filter(
            FocusRecommendation.user_id == user_id,
            FocusRecommendation.is_active == True
        ).update({"is_active": False})
        
        # Save new recommendations
        for rec in recommendations:
            db_rec = FocusRecommendation(
                user_id=user_id,
                recommended_time_of_day=rec["recommended_time_of_day"],
                recommended_duration_minutes=rec["recommended_duration_minutes"],
                confidence_score=rec["confidence_score"],
                reasoning=rec["reasoning"],
                based_on_sessions=json.dumps(rec["based_on_sessions"]),
                valid_from=rec["valid_from"],
                valid_until=rec["valid_until"],
                is_active=True
            )
            db.add(db_rec)
        
        db.commit()
    
    def get_user_statistics(self, db: Session, user_id: str) -> Dict:
        """Get comprehensive user statistics."""
        sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()
        
        if not sessions:
            return {
                "total_sessions": 0,
                "total_duration_hours": 0,
                "average_focus_score": 0,
                "most_productive_time": None,
                "average_session_duration_minutes": 0,
                "total_focused_hours": 0,
                "productivity_trend": "stable"
            }
        
        # Basic statistics
        total_sessions = len(sessions)
        total_duration = sum(s.duration_seconds for s in sessions) / 3600  # Convert to hours
        avg_focus_score = np.mean([s.focus_score for s in sessions])
        avg_duration = np.mean([s.duration_seconds for s in sessions]) / 60  # Convert to minutes
        total_focused_hours = sum(s.focused_frames for s in sessions) / max(1, sum(s.total_frames for s in sessions)) * total_duration
        
        # Most productive time (based on sessions with feedback)
        sessions_with_feedback = [s for s in sessions if hasattr(s, 'feedback') and s.feedback]
        if sessions_with_feedback:
            time_productivity = {}
            for session in sessions_with_feedback:
                hour = session.start_time.hour
                if 6 <= hour < 12:
                    time_period = "morning"
                elif 12 <= hour < 18:
                    time_period = "afternoon"
                else:
                    time_period = "evening"
                
                if time_period not in time_productivity:
                    time_productivity[time_period] = []
                time_productivity[time_period].append(session.feedback[0].productivity_rating)
            
            # Find time with highest average rating
            best_time = None
            best_rating = 0
            for time_period, ratings in time_productivity.items():
                avg_rating = np.mean(ratings)
                if avg_rating > best_rating:
                    best_rating = avg_rating
                    best_time = time_period
            
            most_productive_time = best_time
        else:
            most_productive_time = None
        
        # Productivity trend (last 10 sessions vs previous 10)
        if len(sessions) >= 20:
            recent_sessions = sorted(sessions, key=lambda x: x.created_at)[-10:]
            previous_sessions = sorted(sessions, key=lambda x: x.created_at)[-20:-10]
            
            recent_avg = np.mean([s.focus_score for s in recent_sessions])
            previous_avg = np.mean([s.focus_score for s in previous_sessions])
            
            if recent_avg > previous_avg + 5:
                trend = "improving"
            elif recent_avg < previous_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "total_sessions": total_sessions,
            "total_duration_hours": round(total_duration, 2),
            "average_focus_score": round(avg_focus_score, 1),
            "most_productive_time": most_productive_time,
            "average_session_duration_minutes": round(avg_duration, 1),
            "total_focused_hours": round(total_focused_hours, 2),
            "productivity_trend": trend
        }
