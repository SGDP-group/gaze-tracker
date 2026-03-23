"""
Example client for focus tracking API.
Shows how to send frames from client side to the API.
"""

import base64
import io
import cv2
import requests
import json
import time
from PIL import Image
import numpy as np

class FocusTrackingClient:
    """Client for focus tracking API."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """Initialize client with API base URL."""
        self.api_url = api_url.rstrip('/')
        self.user_id = None
        self.session_id = None
    
    def start_session(self, user_id: str, session_name: str = None) -> bool:
        """Start a focus tracking session."""
        self.user_id = user_id
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/focus/session/start",
                json={
                    "user_id": user_id,
                    "session_name": session_name or f"Session_{int(time.time())}"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data["session_id"]
                print(f"✅ Session started: {self.session_id}")
                return True
            else:
                print(f"❌ Failed to start session: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting session: {e}")
            return False
    
    def send_frame(self, frame: np.ndarray) -> dict:
        """
        Send a frame to the API for analysis.
        
        Args:
            frame: OpenCV frame (numpy array)
            
        Returns:
            Focus analysis results
        """
        try:
            # Convert frame to base64
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            frame_data = f"data:image/jpeg;base64,{frame_base64}"
            
            # Get frame dimensions
            height, width = frame.shape[:2]
            
            # Send to API
            response = requests.post(
                f"{self.api_url}/api/v1/focus/analyze",
                json={
                    "user_id": self.user_id,
                    "frame_data": frame_data,
                    "image_width": width,
                    "image_height": height
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Frame analysis failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error sending frame: {e}")
            return None
    
    def get_session_data(self) -> dict:
        """Get current session data."""
        try:
            response = requests.get(f"{self.api_url}/api/v1/focus/session/{self.user_id}")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get session data: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting session data: {e}")
            return None
    
    def end_session(self) -> dict:
        """End the current session and return final data."""
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/focus/session/end",
                params={"user_id": self.user_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Session ended for user {self.user_id}")
                return data
            else:
                print(f"❌ Failed to end session: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error ending session: {e}")
            return None
    
    def get_active_users(self) -> dict:
        """Get list of active users."""
        try:
            response = requests.get(f"{self.api_url}/api/v1/focus/users/active")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get active users: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting active users: {e}")
            return None


def webcam_demo():
    """Demo using webcam with focus tracking API."""
    print("🎥 Starting webcam focus tracking demo...")
    
    # Initialize client
    client = FocusTrackingClient("http://localhost:8000")
    
    # Start session
    user_id = f"webcam_user_{int(time.time())}"
    if not client.start_session(user_id, "Webcam Demo Session"):
        return
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open webcam")
        return
    
    print("📹 Webcam started. Press 'q' to quit, 's' to show stats")
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Send frame for analysis every 5 frames
            if frame_count % 5 == 0:
                result = client.send_frame(frame)
                
                if result:
                    # Display focus info on frame
                    state = result["current_state"]
                    score = result["focus_score"]
                    
                    # Color code based on state
                    color = (0, 255, 0) if state == "FOCUSED" else (0, 0, 255) if state == "DISTRACTED" else (128, 128, 128)
                    
                    # Add text overlay
                    cv2.putText(frame, f"State: {state}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    cv2.putText(frame, f"Score: {score:.1f}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    cv2.putText(frame, f"Frames: {frame_count}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # Show face metrics if available
                    if result["face_metrics"]:
                        centroid = result["face_metrics"]["centroid"]
                        angle = result["face_metrics"]["angle"]
                        cv2.circle(frame, (centroid["x"], centroid["y"]), 5, (0, 255, 255), -1)
                        cv2.putText(frame, f"Angle: {angle:.1f}°", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Show frame
            cv2.imshow('Focus Tracking Demo', frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Show session stats
                session_data = client.get_session_data()
                if session_data:
                    print(f"\n📊 Session Stats:")
                    print(f"   Total Frames: {session_data['total_frames']}")
                    print(f"   Focused Frames: {session_data['focused_frames']}")
                    print(f"   Focus Score: {session_data['focus_score']:.1f}%")
                    print(f"   Session Duration: {session_data['total_frames'] / 30:.1f}s")
    
    finally:
        # End session
        final_data = client.end_session()
        if final_data:
            duration = time.time() - start_time
            print(f"\n🎯 Final Session Results:")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Total Frames: {final_data['total_frames']}")
            print(f"   Focus Score: {final_data['focus_score']:.1f}%")
            print(f"   Focused: {final_data['focused_frames']}")
            print(f"   Distracted: {final_data['distracted_frames']}")
            print(f"   Away: {final_data['away_frames']}")
        
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()


def image_demo():
    """Demo with static images."""
    print("🖼️ Starting image focus tracking demo...")
    
    # Create a test image
    img = Image.new('RGB', (640, 480), color='blue')
    img_array = np.array(img)
    
    # Initialize client
    client = FocusTrackingClient("http://localhost:8000")
    
    # Start session
    user_id = f"image_user_{int(time.time())}"
    if not client.start_session(user_id, "Image Demo Session"):
        return
    
    # Send multiple test frames
    for i in range(10):
        result = client.send_frame(img_array)
        if result:
            print(f"Frame {i+1}: State={result['current_state']}, Score={result['focus_score']:.1f}%")
        time.sleep(0.1)
    
    # Get final session data
    final_data = client.end_session()
    if final_data:
        print(f"\n🎯 Image Demo Results:")
        print(f"   Total Frames: {final_data['total_frames']}")
        print(f"   Focus Score: {final_data['focus_score']:.1f}%")


def multi_user_demo():
    """Demo with multiple concurrent users."""
    print("👥 Starting multi-user demo...")
    
    clients = []
    users = []
    
    # Create multiple clients
    for i in range(3):
        client = FocusTrackingClient("http://localhost:8000")
        user_id = f"multi_user_{i}_{int(time.time())}"
        
        if client.start_session(user_id, f"Multi-User Session {i}"):
            clients.append(client)
            users.append(user_id)
            print(f"✅ Started session for {user_id}")
    
    # Send frames for each user
    img = Image.new('RGB', (320, 240), color='green')
    img_array = np.array(img)
    
    for round_num in range(5):
        print(f"\n🔄 Round {round_num + 1}:")
        
        for i, client in enumerate(clients):
            result = client.send_frame(img_array)
            if result:
                print(f"   User {i}: {result['current_state']} ({result['focus_score']:.1f}%)")
    
    # Check active users
    active_users = clients[0].get_active_users()
    if active_users:
        print(f"\n👥 Active Users: {active_users['total_count']}")
        for user in active_users['active_users']:
            print(f"   - {user}")
    
    # End all sessions
    print(f"\n🏁 Ending sessions...")
    for i, client in enumerate(clients):
        final_data = client.end_session()
        if final_data:
            print(f"   User {i}: {final_data['focus_score']:.1f}% focus score")


def api_health_check():
    """Check if API is running."""
    try:
        response = requests.get("http://localhost:8000/api/v1/focus/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ API is healthy")
            print(f"   Status: {data['status']}")
            print(f"   Active Sessions: {data['active_sessions']}")
            print(f"   Version: {data['service_version']}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False


if __name__ == "__main__":
    print("🎯 Focus Tracking Client Demo")
    print("=" * 40)
    
    # Check API health
    if not api_health_check():
        print("\n❌ Please start the API server first:")
        print("   uv run server.py")
        exit(1)
    
    print("\n📋 Choose demo:")
    print("1. Webcam demo (requires camera)")
    print("2. Image demo (static images)")
    print("3. Multi-user demo (concurrent sessions)")
    print("4. Health check only")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        webcam_demo()
    elif choice == "2":
        image_demo()
    elif choice == "3":
        multi_user_demo()
    elif choice == "4":
        api_health_check()
    else:
        print("❌ Invalid choice")
