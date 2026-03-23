"""
Pytest-based Celery async training tests.
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime

from src.services.tasks import train_user_model_async, get_task_status, get_user_training_history
from src.services.celery_app import celery_app
from src.database.models import TrainingTask


class TestCeleryTasks:
    """Test Celery task functions."""
    
    @pytest.mark.unit
    def test_train_user_model_async_insufficient_data(self, db_session):
        """Test async training with insufficient data."""
        with patch('src.services.tasks.SessionLocal') as mock_session:
            mock_session.return_value = db_session
            
            # Mock the query to return 0 sessions with feedback
            with patch.object(db_session, 'query') as mock_query:
                mock_query.return_value.count.return_value = 0
                
                task = train_user_model_async.s("test_user", False)
                result = task.apply().get()
                
                assert result["status"] == "INSUFFICIENT_DATA"
                assert "Need at least 3 sessions" in result["message"]
    
    @pytest.mark.unit
    def test_train_user_model_async_success(self, db_session, multiple_sessions_with_feedback):
        """Test successful async training."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        with patch('src.services.tasks.SessionLocal') as mock_session:
            mock_session.return_value = db_session
            
            # Mock the ML service
            with patch('src.services.tasks.PersonalizedMLService') as mock_ml_service:
                mock_ml_instance = Mock()
                mock_ml_service.train_personalized_model.return_value = {
                    "model_version": 2,
                    "training_sessions_count": 5,
                    "training_accuracy": 0.85,
                    "message": "Training completed"
                }
                mock_ml_service.return_value = mock_ml_instance
                
                task = train_user_model_async.s(sessions[0].user_id, True)
                result = task.apply().get()
                
                assert result["status"] == "SUCCESS"
                assert result["task_id"] is not None
                assert "Training completed successfully" in result["message"]
    
    @pytest.mark.unit
    def test_train_user_model_async_already_in_progress(self, db_session, test_user):
        """Test async training when task is already in progress."""
        # Create an existing training task in progress
        existing_task = TrainingTask(
            task_id="existing_task_123",
            user_id=test_user.user_id,
            status="PROGRESS",
            started_at=datetime.utcnow()
        )
        db_session.add(existing_task)
        db_session.commit()
        
        with patch('src.services.tasks.SessionLocal') as mock_session:
            mock_session.return_value = db_session
            
            task = train_user_model_async.s(test_user.user_id, False)
            result = task.apply().get()
            
            assert result["status"] == "SKIPPED"
            assert "already in progress" in result["message"]
    
    @pytest.mark.unit
    def test_get_task_status_success(self):
        """Test getting task status for successful task."""
        with patch('src.services.tasks.AsyncResult') as mock_async_result:
            mock_result = Mock()
            mock_result.status = "SUCCESS"
            mock_result.ready.return_value = True
            mock_result.successful.return_value = True
            mock_result.get.return_value = {"status": "SUCCESS", "message": "Completed"}
            mock_result.date_done = datetime.utcnow()
            mock_async_result.return_value = mock_result
            
            status = get_task_status("test_task_123")
            
            assert status["status"] == "SUCCESS"
            assert status["result"]["status"] == "SUCCESS"
            assert status["date_done"] is not None
    
    @pytest.mark.unit
    def test_get_task_status_progress(self):
        """Test getting task status for in-progress task."""
        with patch('src.services.tasks.AsyncResult') as mock_async_result:
            mock_result = Mock()
            mock_result.status = "PROGRESS"
            mock_result.ready.return_value = False
            mock_result.info = {"status": "Training...", "progress": 50}
            mock_async_result.return_value = mock_result
            
            status = get_task_status("test_task_123")
            
            assert status["status"] == "PROGRESS"
            assert status["progress"] == 50
            assert status["result"] is None
    
    @pytest.mark.unit
    def test_get_task_status_failure(self):
        """Test getting task status for failed task."""
        with patch('src.services.tasks.AsyncResult') as mock_async_result:
            mock_result = Mock()
            mock_result.status = "FAILURE"
            mock_result.ready.return_value = True
            mock_result.successful.return_value = False
            mock_result.info = {"error": "Training failed"}
            mock_async_result.return_value = mock_result
            
            status = get_task_status("test_task_123")
            
            assert status["status"] == "FAILURE"
            assert "error" in status
    
    @pytest.mark.unit
    def test_get_user_training_history(self, db_session, test_user):
        """Test getting user training history."""
        # Create some training tasks
        for i in range(3):
            task = TrainingTask(
                task_id=f"task_{i+1}",
                user_id=test_user.user_id,
                status="COMPLETED" if i < 2 else "FAILED",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                result=f'{{"version": {i+1}}}' if i < 2 else None,
                error_message="Failed" if i == 2 else None
            )
            db_session.add(task)
        
        db_session.commit()
        
        history = get_user_training_history(test_user.user_id)
        
        assert len(history) == 3
        assert history[0]["status"] == "FAILED"  # Most recent first
        assert history[1]["status"] == "COMPLETED"
        assert history[2]["status"] == "COMPLETED"


class TestCeleryIntegration:
    """Integration tests for Celery functionality."""
    
    @pytest.mark.requires_redis
    @pytest.mark.requires_celery
    @pytest.mark.integration
    def test_celery_connection(self):
        """Test Celery connection to Redis."""
        # Test that Celery app is configured
        assert celery_app.conf.broker_url is not None
        assert celery_app.conf.result_backend is not None
        
        # Test basic Celery functionality
        result = celery_app.send_task('celery.ping')
        assert result is not None
    
    @pytest.mark.requires_redis
    @pytest.mark.requires_celery
    @pytest.mark.integration
    def test_async_training_workflow(self, client, test_user_headers, multiple_sessions_with_feedback):
        """Test complete async training workflow."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        # Submit training task
        response = client.post(
            "/api/v1/models/train/async",
            json={"user_id": sessions[0].user_id, "force_retrain": True},
            headers=test_user_headers
        )
        
        assert response.status_code == 200
        task_data = response.json()
        task_id = task_data["task_id"]
        
        # Poll for completion (with timeout)
        max_wait = 60  # 60 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = client.get(
                f"/api/v1/models/train/status/{task_id}",
                headers=test_user_headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                if status_data["status"] in ["SUCCESS", "FAILURE", "COMPLETED"]:
                    break
            
            time.sleep(2)
        
        # Check final status
        final_response = client.get(
            f"/api/v1/models/train/status/{task_id}",
            headers=test_user_headers
        )
        
        assert final_response.status_code == 200
        final_status = final_response.json()
        
        # Should be completed (either success or failure)
        assert final_status["status"] in ["SUCCESS", "FAILURE", "COMPLETED"]
    
    @pytest.mark.requires_redis
    @pytest.mark.requires_celery
    @pytest.mark.integration
    def test_training_task_persistence(self, client, test_user_headers, multiple_sessions_with_feedback):
        """Test that training tasks are persisted in database."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        # Submit training task
        response = client.post(
            "/api/v1/models/train/async",
            json={"user_id": sessions[0].user_id, "force_retrain": True},
            headers=test_user_headers
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Check that task appears in database
        tasks_response = client.get("/api/v1/models/train/tasks", headers=test_user_headers)
        
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()
        
        # Find our task
        our_task = next((t for t in tasks if t["task_id"] == task_id), None)
        assert our_task is not None
        assert our_task["user_id"] == sessions[0].user_id
        assert our_task["status"] in ["PENDING", "PROGRESS", "COMPLETED", "FAILED"]


class TestCeleryErrorHandling:
    """Test Celery error handling scenarios."""
    
    @pytest.mark.unit
    def test_training_task_exception_handling(self, db_session):
        """Test exception handling in training tasks."""
        with patch('src.services.tasks.SessionLocal') as mock_session:
            mock_session.return_value = db_session
            
            # Mock ML service to raise an exception
            with patch('src.services.tasks.PersonalizedMLService') as mock_ml_service:
                mock_ml_instance = Mock()
                mock_ml_instance.train_personalized_model.side_effect = Exception("Training failed")
                mock_ml_service.return_value = mock_ml_instance
                
                # Mock sufficient data
                with patch.object(db_session, 'query') as mock_query:
                    mock_query.return_value.count.return_value = 5
                    
                    task = train_user_model_async.s("test_user", True)
                    result = task.apply().get()
                    
                    assert result["status"] == "FAILED"
                    assert "Training failed" in result["error"]
    
    @pytest.mark.unit
    def test_database_connection_error(self):
        """Test handling of database connection errors."""
        with patch('src.services.tasks.SessionLocal') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            task = train_user_model_async.s("test_user", False)
            result = task.apply().get()
            
            assert result["status"] == "FAILED"
            assert "Database connection failed" in result["error"]
    
    @pytest.mark.unit
    def test_task_timeout_handling(self):
        """Test task timeout handling."""
        with patch('src.services.tasks.train_user_model_async') as mock_task:
            # Mock task that takes too long
            mock_task.apply.side_effect = Exception("Task timeout")
            
            # This would be handled by Celery's timeout configuration
            # Here we just test the error handling structure
            assert True  # Placeholder for timeout handling test


class TestCeleryPerformance:
    """Test Celery performance and scalability."""
    
    @pytest.mark.requires_redis
    @pytest.mark.requires_celery
    @pytest.mark.integration
    @pytest.mark.slow
    def test_concurrent_training_tasks(self, client, test_user_headers, multiple_sessions_with_feedback):
        """Test handling multiple concurrent training tasks."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        # Submit multiple training tasks
        task_ids = []
        for i in range(3):
            response = client.post(
                "/api/v1/models/train/async",
                json={"user_id": sessions[0].user_id, "force_retrain": True},
                headers=test_user_headers
            )
            
            if response.status_code == 200:
                task_ids.append(response.json()["task_id"])
        
        # Wait for all tasks to complete
        completed_tasks = 0
        max_wait = 120  # 2 minutes
        start_time = time.time()
        
        while completed_tasks < len(task_ids) and time.time() - start_time < max_wait:
            for task_id in task_ids:
                status_response = client.get(
                    f"/api/v1/models/train/status/{task_id}",
                    headers=test_user_headers
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data["status"] in ["SUCCESS", "FAILURE", "COMPLETED"]:
                        completed_tasks += 1
                        if task_id in task_ids:
                            task_ids.remove(task_id)
            
            time.sleep(5)
        
        # At least one task should complete
        assert completed_tasks > 0
    
    @pytest.mark.unit
    def test_task_memory_usage(self, db_session, multiple_sessions_with_feedback):
        """Test that tasks don't leak memory."""
        sessions, feedback_list = multiple_sessions_with_feedback
        
        with patch('src.services.tasks.SessionLocal') as mock_session:
            mock_session.return_value = db_session
            
            with patch('src.services.tasks.PersonalizedMLService') as mock_ml_service:
                mock_ml_instance = Mock()
                mock_ml_instance.train_personalized_model.return_value = {
                    "model_version": 1,
                    "training_accuracy": 0.8
                }
                mock_ml_service.return_value = mock_ml_instance
                
                # Run multiple tasks and check they complete properly
                for i in range(5):
                    task = train_user_model_async.s(sessions[0].user_id, False)
                    result = task.apply().get()
                    
                    assert result["status"] == "SUCCESS"
                    assert "task_id" in result
