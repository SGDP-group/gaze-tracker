"""
Test script for Celery async training functionality.
"""

import requests
import time
import json
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000/api/v1"


class CeleryAPITester:
    """Test client for Celery async training endpoints."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.api_key = None
        self.user_id = None
    
    def get_headers(self) -> dict:
        """Get authentication headers."""
        if not self.api_key:
            raise Exception("No API key available")
        return {"Authorization": f"Bearer {self.api_key}"}
    
    def create_user(self, user_id: str) -> dict:
        """Create a test user."""
        response = requests.post(f"{self.base_url}/users", json={"user_id": user_id})
        if response.status_code == 200:
            user_data = response.json()
            self.api_key = user_data["api_key"]
            self.user_id = user_data["user_id"]
            return user_data
        else:
            raise Exception(f"Failed to create user: {response.text}")
    
    def create_sample_sessions(self, count: int = 5):
        """Create sample sessions with feedback for training."""
        headers = self.get_headers()
        
        for i in range(count):
            # Create session
            session_data = {
                "user_id": self.user_id,
                "session_id": f"celery_test_session_{i+1}",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration_seconds": 1800,  # 30 minutes
                "total_frames": 900,
                "focused_frames": int(900 * 0.75),
                "distracted_frames": int(900 * 0.15),
                "away_frames": int(900 * 0.10),
                "focus_score": 75.0,
                "baseline_angle": 45.0,
                "raw_session_data": json.dumps({"test": f"session_{i+1}"}),
                "angle_variance": 15.0 + (i * 2),
                "stability_score": 0.8 - (i * 0.05),
                "presence_ratio": 0.9,
                "context_switches": i + 1,
                "base_prediction": "Productive Session",
                "base_confidence": 0.8
            }
            
            session_response = requests.post(
                f"{self.base_url}/sessions",
                json=session_data,
                headers=headers
            )
            
            if session_response.status_code != 200:
                print(f"Failed to create session {i+1}: {session_response.text}")
                continue
            
            # Create feedback
            feedback_data = {
                "user_id": self.user_id,
                "session_id": f"celery_test_session_{i+1}",
                "productivity_rating": 4 if i < 3 else 2,  # First 3 productive
                "difficulty_rating": 3,
                "energy_level": 4,
                "task_type": "coding",
                "time_of_day": "morning",
                "interruptions": i,
                "notes": f"Test session {i+1}"
            }
            
            feedback_response = requests.post(
                f"{self.base_url}/feedback",
                json=feedback_data,
                headers=headers
            )
            
            if feedback_response.status_code != 200:
                print(f"Failed to create feedback for session {i+1}: {feedback_response.text}")
            else:
                print(f"✅ Created session {i+1} with feedback")
    
    def submit_async_training(self, force_retrain: bool = False) -> dict:
        """Submit async training task."""
        headers = self.get_headers()
        
        training_request = {
            "user_id": self.user_id,
            "force_retrain": force_retrain
        }
        
        response = requests.post(
            f"{self.base_url}/models/train/async",
            json=training_request,
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to submit training task: {response.text}")
    
    def check_training_status(self, task_id: str) -> dict:
        """Check training task status."""
        headers = self.get_headers()
        
        response = requests.get(
            f"{self.base_url}/models/train/status/{task_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get task status: {response.text}")
    
    def get_training_history(self) -> list:
        """Get user training history."""
        headers = self.get_headers()
        
        response = requests.get(
            f"{self.base_url}/models/train/history",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get training history: {response.text}")
    
    def monitor_training_progress(self, task_id: str, timeout: int = 300) -> dict:
        """Monitor training progress until completion or timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.check_training_status(task_id)
            print(f"   Status: {status['status']}")
            
            if status['status'] in ['SUCCESS', 'FAILURE', 'COMPLETED']:
                return status
            
            if status.get('progress'):
                print(f"   Progress: {status['progress']}%")
            
            time.sleep(5)
        
        raise TimeoutError(f"Training task {task_id} did not complete within {timeout} seconds")
    
    def run_full_test(self):
        """Run complete Celery async training test."""
        print("=" * 60)
        print("CELERY ASYNC TRAINING TEST")
        print("=" * 60)
        
        try:
            # 1. Create user
            print("\n1. Creating test user...")
            user_id = f"celery_test_user_{int(time.time())}"
            user = self.create_user(user_id)
            print(f"   ✅ User created: {user['user_id']}")
            
            # 2. Create sample sessions
            print("\n2. Creating sample sessions with feedback...")
            self.create_sample_sessions(5)
            
            # 3. Submit async training
            print("\n3. Submitting async training task...")
            training_task = self.submit_async_training(force_retrain=True)
            task_id = training_task['task_id']
            print(f"   ✅ Training task submitted: {task_id}")
            print(f"   Status: {training_task['status']}")
            
            # 4. Monitor training progress
            print("\n4. Monitoring training progress...")
            final_status = self.monitor_training_progress(task_id)
            print(f"   Final Status: {final_status['status']}")
            
            if final_status['status'] == 'SUCCESS':
                result = final_status.get('result', {})
                print(f"   Model Version: {result.get('model_version')}")
                print(f"   Training Accuracy: {result.get('training_accuracy', 0):.1%}")
                print(f"   Training Time: {result.get('training_time_seconds', 0):.2f}s")
            else:
                print(f"   Error: {final_status.get('error', 'Unknown error')}")
            
            # 5. Check training history
            print("\n5. Getting training history...")
            history = self.get_training_history()
            print(f"   Total training tasks: {len(history)}")
            
            for task in history[:3]:  # Show last 3 tasks
                print(f"   Task {task['task_id'][:8]}... - {task['status']}")
            
            print("\n" + "=" * 60)
            print("CELERY TEST COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {str(e)}")
            return False


def main():
    """Main test function."""
    print("Starting Celery async training test...")
    print("Make sure:")
    print("1. Redis server is running on localhost:6379")
    print("2. Celery worker is running: uv run celery -A src.services.celery_app worker --loglevel=info")
    print("3. API server is running: uv run server.py")
    print()
    
    input("Press Enter to start the test...")
    
    tester = CeleryAPITester()
    success = tester.run_full_test()
    
    if success:
        print("\n✅ All Celery tests passed!")
    else:
        print("\n❌ Some tests failed!")


if __name__ == "__main__":
    main()
