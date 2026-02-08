"""
API client service for integrating the focus tracker with the backend API.
"""

import json
import requests
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import os


class FocusTrackerAPIClient:
    """Client for communicating with the Focus Management System API."""
    
    def __init__(self, base_url: str = None, api_key: str = None, user_id: str = None):
        self.base_url = base_url or os.getenv("FOCUS_API_URL", "http://localhost:8000/api/v1")
        self.api_key = api_key or os.getenv("FOCUS_API_KEY")
        self.user_id = user_id or os.getenv("FOCUS_USER_ID")
        
        if not self.api_key or not self.user_id:
            print("Warning: API key or user ID not provided. Some features may not work.")
    
    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if not self.api_key:
            raise Exception("No API key available")
        return {"Authorization": f"Bearer {self.api_key}"}
    
    def create_user_if_needed(self, user_id: str) -> Dict[str, Any]:
        """Create a user if they don't exist."""
        try:
            headers = self.get_headers()
            response = requests.get(f"{self.base_url}/users/me", headers=headers)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        # Create new user
        response = requests.post(f"{self.base_url}/users", json={"user_id": user_id})
        if response.status_code == 200:
            user_data = response.json()
            self.api_key = user_data["api_key"]
            self.user_id = user_data["user_id"]
            return user_data
        else:
            raise Exception(f"Failed to create user: {response.text}")
    
    def send_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send session data to the API."""
        if not self.api_key or not self.user_id:
            raise Exception("API key and user ID required")
        
        # Generate session ID if not provided
        if "session_id" not in session_data:
            session_data["session_id"] = str(uuid.uuid4())
        
        # Ensure user_id is set
        session_data["user_id"] = self.user_id
        
        headers = self.get_headers()
        response = requests.post(
            f"{self.base_url}/sessions",
            json=session_data,
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to send session data: {response.text}")
    
    def send_feedback(self, session_id: str, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send feedback for a session."""
        if not self.api_key or not self.user_id:
            raise Exception("API key and user ID required")
        
        feedback_data["user_id"] = self.user_id
        feedback_data["session_id"] = session_id
        
        headers = self.get_headers()
        response = requests.post(
            f"{self.base_url}/feedback",
            json=feedback_data,
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to send feedback: {response.text}")
    
    def get_recommendations(self) -> Dict[str, Any]:
        """Get focus recommendations."""
        if not self.api_key:
            raise Exception("API key required")
        
        headers = self.get_headers()
        response = requests.get(f"{self.base_url}/recommendations", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get recommendations: {response.text}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get user statistics."""
        if not self.api_key:
            raise Exception("API key required")
        
        headers = self.get_headers()
        response = requests.get(f"{self.base_url}/statistics", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get statistics: {response.text}")
    
    def train_model(self, force_retrain: bool = False) -> Dict[str, Any]:
        """Train personalized model."""
        if not self.api_key or not self.user_id:
            raise Exception("API key and user ID required")
        
        headers = self.get_headers()
        response = requests.post(
            f"{self.base_url}/models/train",
            json={"user_id": self.user_id, "force_retrain": force_retrain},
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to train model: {response.text}")


def collect_user_feedback_interactive(session_id: str) -> Dict[str, Any]:
    """Collect user feedback interactively from command line."""
    print("\n" + "=" * 50)
    print("SESSION FEEDBACK")
    print("=" * 50)
    
    feedback = {}
    
    # Productivity rating
    while True:
        try:
            rating = int(input("Rate your productivity (1-5, where 5=Very Productive): "))
            if 1 <= rating <= 5:
                feedback["productivity_rating"] = rating
                break
            else:
                print("Please enter a number between 1 and 5.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Optional ratings
    try:
        difficulty = int(input("Rate difficulty (1-5, where 5=Very Hard) [optional]: "))
        if 1 <= difficulty <= 5:
            feedback["difficulty_rating"] = difficulty
    except ValueError:
        pass
    
    try:
        energy = int(input("Rate energy level (1-5, where 5=Very High) [optional]: "))
        if 1 <= energy <= 5:
            feedback["energy_level"] = energy
    except ValueError:
        pass
    
    # Task type
    task = input("Task type (coding, reading, meeting, etc.) [optional]: ").strip()
    if task:
        feedback["task_type"] = task
    
    # Time of day
    hour = datetime.now().hour
    if 6 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 18:
        time_of_day = "afternoon"
    else:
        time_of_day = "evening"
    
    feedback["time_of_day"] = time_of_day
    
    # Interruptions
    try:
        interruptions = int(input("Number of interruptions [default 0]: ") or "0")
        feedback["interruptions"] = max(0, interruptions)
    except ValueError:
        feedback["interruptions"] = 0
    
    # Notes
    notes = input("Any additional notes [optional]: ").strip()
    if notes:
        feedback["notes"] = notes
    
    return feedback
