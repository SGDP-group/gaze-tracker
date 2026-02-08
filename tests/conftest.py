"""
Pytest configuration and fixtures for the Focus Management System.
"""

import pytest
import tempfile
import os
from datetime import datetime
from typing import Generator, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import Mock

from src.database.database import get_db, Base
from src.database.models import User, UserSession, UserFeedback, UserModel, TrainingTask
from src.api.main import app
from src.services.auth import generate_api_key


@pytest.fixture(scope="session")
def test_db() -> Generator:
    """Create a test database."""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestingSessionLocal
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def db_session(test_db) -> Generator:
    """Get a database session for testing."""
    session = test_db()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def override_get_db(test_db):
    """Override database dependency for testing."""
    def _override_get_db():
        session = test_db()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db) -> Generator:
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user."""
    user = User(
        user_id="test_user_123",
        api_key=generate_api_key()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_headers(test_user) -> Dict[str, str]:
    """Get authentication headers for test user."""
    return {"Authorization": f"Bearer {test_user.api_key}"}


@pytest.fixture
def sample_session_data(test_user) -> Dict[str, Any]:
    """Sample session data for testing."""
    return {
        "user_id": test_user.user_id,
        "session_id": "test_session_123",
        "start_time": datetime.utcnow().isoformat(),
        "end_time": datetime.utcnow().isoformat(),
        "duration_seconds": 1800.0,
        "total_frames": 900,
        "focused_frames": 675,
        "distracted_frames": 135,
        "away_frames": 90,
        "focus_score": 75.0,
        "baseline_angle": 45.0,
        "raw_session_data": '{"test": "data"}',
        "angle_variance": 15.5,
        "stability_score": 0.82,
        "presence_ratio": 0.90,
        "context_switches": 3,
        "base_prediction": "Productive Session",
        "base_confidence": 0.85
    }


@pytest.fixture
def sample_feedback_data(test_user) -> Dict[str, Any]:
    """Sample feedback data for testing."""
    return {
        "user_id": test_user.user_id,
        "session_id": "test_session_123",
        "productivity_rating": 4,
        "difficulty_rating": 3,
        "energy_level": 4,
        "task_type": "coding",
        "time_of_day": "morning",
        "interruptions": 2,
        "notes": "Good focus session"
    }


@pytest.fixture
def multiple_sessions_with_feedback(db_session, test_user) -> tuple:
    """Create multiple sessions with feedback for testing."""
    sessions = []
    feedback_list = []
    
    for i in range(5):
        # Create session
        session = UserSession(
            user_id=test_user.user_id,
            session_id=f"test_session_{i+1}",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_seconds=1800.0,
            total_frames=900,
            focused_frames=int(900 * (0.8 - i * 0.05)),
            distracted_frames=int(900 * 0.15),
            away_frames=int(900 * 0.05),
            focus_score=80.0 - (i * 5),
            baseline_angle=45.0,
            raw_session_data=f'{{"test": "session_{i+1}"}}',
            angle_variance=15.0 + (i * 2),
            stability_score=0.85 - (i * 0.05),
            presence_ratio=0.90,
            context_switches=i + 1,
            base_prediction="Productive Session" if i < 3 else "Unproductive Session",
            base_confidence=0.8
        )
        db_session.add(session)
        sessions.append(session)
        
        # Create feedback
        feedback = UserFeedback(
            user_id=test_user.user_id,
            session_id=f"test_session_{i+1}",
            productivity_rating=4 if i < 3 else 2,
            difficulty_rating=3,
            energy_level=4,
            task_type="coding",
            time_of_day="morning",
            interruptions=i,
            notes=f"Test session {i+1}"
        )
        db_session.add(feedback)
        feedback_list.append(feedback)
    
    db_session.commit()
    
    # Refresh objects
    for session in sessions:
        db_session.refresh(session)
    for feedback in feedback_list:
        db_session.refresh(feedback)
    
    return sessions, feedback_list


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    mock_task = Mock()
    mock_task.id = "test_task_123"
    mock_task.status = "SUCCESS"
    mock_task.get.return_value = {
        "status": "SUCCESS",
        "message": "Training completed",
        "model_version": 1,
        "training_accuracy": 0.85
    }
    mock_task.ready.return_value = True
    mock_task.successful.return_value = True
    mock_task.date_done = datetime.utcnow()
    return mock_task


@pytest.fixture
def redis_available():
    """Check if Redis is available for integration tests."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        return True
    except:
        return False


@pytest.fixture
def celery_worker_available():
    """Check if Celery worker is available for integration tests."""
    try:
        from src.services.celery_app import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        return bool(stats)
    except:
        return False


# Skip markers for conditional testing
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "requires_redis: Skip test if Redis is not available"
    )
    config.addinivalue_line(
        "markers", "requires_celery: Skip test if Celery worker is not available"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add skip markers."""
    redis_available = True
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
    except:
        redis_available = False
    
    celery_available = True
    try:
        from src.services.celery_app import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        celery_available = bool(stats)
    except:
        celery_available = False
    
    # Add skip markers
    for item in items:
        if "requires_redis" in item.keywords and not redis_available:
            item.add_marker(pytest.mark.skip(reason="Redis not available"))
        if "requires_celery" in item.keywords and not celery_available:
            item.add_marker(pytest.mark.skip(reason="Celery worker not available"))
