"""
GUI Demo Client for Focus Management System API.
Tests focus service and other endpoints with interactive buttons.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
import base64
import io
import threading
import time
from PIL import Image, ImageTk, ImageDraw
import cv2
import numpy as np
from datetime import datetime

class FocusAPIDemoClient:
    """GUI client for testing Focus Management System API."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Focus Management System API Demo")
        self.root.geometry("1200x800")
        
        # API configuration
        self.api_url = "http://localhost:8000"
        self.user_id = f"demo_user_{int(time.time())}"
        self.session_id = None
        self.camera_active = False
        self.cap = None
        
        # Create GUI
        self.create_widgets()
        
        # Initial status
        self.update_status("Ready. Click 'Health Check' to test API connection.")
        
    def create_widgets(self):
        """Create GUI widgets."""
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # === API Configuration ===
        config_frame = ttk.LabelFrame(main_frame, text="API Configuration", padding="10")
        config_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(config_frame, text="API URL:").grid(row=0, column=0, sticky=tk.W)
        self.api_url_var = tk.StringVar(value=self.api_url)
        ttk.Entry(config_frame, textvariable=self.api_url_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(config_frame, text="User ID:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.user_id_var = tk.StringVar(value=self.user_id)
        ttk.Entry(config_frame, textvariable=self.user_id_var, width=25).grid(row=0, column=3, sticky=(tk.W, tk.E))
        
        ttk.Button(config_frame, text="Update Config", command=self.update_config).grid(row=0, column=4, padx=(10, 0))
        
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)
        
        # === Focus Service Controls ===
        focus_frame = ttk.LabelFrame(main_frame, text="Focus Service", padding="10")
        focus_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Focus buttons
        focus_buttons = [
            ("Start Session", self.start_focus_session),
            ("Send Test Frame", self.send_test_frame),
            ("Get Session Data", self.get_session_data),
            ("End Session", self.end_focus_session),
            ("Get Active Users", self.get_active_users),
            ("Cleanup Sessions", self.cleanup_sessions)
        ]
        
        for i, (text, command) in enumerate(focus_buttons):
            row, col = i // 3, i % 3
            ttk.Button(focus_frame, text=text, command=command).grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        focus_frame.columnconfigure(0, weight=1)
        focus_frame.columnconfigure(1, weight=1)
        focus_frame.columnconfigure(2, weight=1)
        
        # === Other API Controls ===
        api_frame = ttk.LabelFrame(main_frame, text="Other API Endpoints", padding="10")
        api_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=(10, 0))
        
        # API buttons
        api_buttons = [
            ("Health Check", self.health_check),
            ("Create User", self.create_user),
            ("Get Current User", self.get_current_user),
            ("Get Statistics", self.get_statistics),
            ("Start Async Training", self.start_async_training),
            ("Get Training Status", self.get_training_status)
        ]
        
        for i, (text, command) in enumerate(api_buttons):
            ttk.Button(api_frame, text=text, command=command).grid(row=i, column=0, padx=5, pady=2, sticky=(tk.W, tk.E))
        
        api_frame.columnconfigure(0, weight=1)
        
        # === Camera Controls ===
        camera_frame = ttk.LabelFrame(main_frame, text="Camera Test", padding="10")
        camera_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.camera_button = ttk.Button(camera_frame, text="Start Camera", command=self.toggle_camera)
        self.camera_button.grid(row=0, column=0, padx=5)
        
        self.send_camera_frame_button = ttk.Button(camera_frame, text="Send Camera Frame", command=self.send_camera_frame, state=tk.DISABLED)
        self.send_camera_frame_button.grid(row=0, column=1, padx=5)
        
        self.auto_send_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(camera_frame, text="Auto Send (1/sec)", variable=self.auto_send_var).grid(row=0, column=2, padx=5)
        
        # === Video Display ===
        video_frame = ttk.LabelFrame(main_frame, text="Video Preview", padding="10")
        video_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.video_label = ttk.Label(video_frame, text="Camera feed will appear here", background="black", foreground="white")
        self.video_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        
        # === Response Display ===
        response_frame = ttk.LabelFrame(main_frame, text="API Responses", padding="10")
        response_frame.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=(10, 0))
        
        self.response_text = scrolledtext.ScrolledText(response_frame, height=20, width=50)
        self.response_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        response_frame.columnconfigure(0, weight=1)
        response_frame.rowconfigure(0, weight=1)
        
        # === Status Bar ===
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Status: Ready", relief=tk.SUNKEN)
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        # Auto-send timer
        self.auto_send_timer = None
        
    def update_config(self):
        """Update API configuration."""
        self.api_url = self.api_url_var.get().rstrip('/')
        self.user_id = self.user_id_var.get()
        self.update_status(f"Configuration updated: API={self.api_url}, User={self.user_id}")
        
    def update_status(self, message):
        """Update status bar."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_label.config(text=f"[{timestamp}] {message}")
        self.root.update_idletasks()
        
    def log_response(self, title, response_data):
        """Log API response to the text area."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if isinstance(response_data, dict):
            formatted_data = json.dumps(response_data, indent=2, default=str)
        else:
            formatted_data = str(response_data)
        
        log_entry = f"[{timestamp}] {title}:\n{formatted_data}\n{'='*50}\n"
        
        self.response_text.insert(tk.END, log_entry)
        self.response_text.see(tk.END)
        
    def make_api_request(self, method, endpoint, data=None, params=None):
        """Make API request and handle errors."""
        try:
            url = f"{self.api_url}/api/v1{endpoint}"
            
            if method == "GET":
                response = requests.get(url, params=params)
            elif method == "POST":
                response = requests.post(url, json=data, params=params)
            elif method == "PUT":
                response = requests.put(url, json=data)
            elif method == "DELETE":
                response = requests.delete(url, params=params)
            
            return response
            
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", f"Cannot connect to API at {self.api_url}")
            return None
        except Exception as e:
            messagebox.showerror("API Error", f"Request failed: {str(e)}")
            return None
    
    # === Focus Service Methods ===
    
    def start_focus_session(self):
        """Start focus tracking session."""
        data = {
            "user_id": self.user_id,
            "session_name": f"Demo Session {datetime.now().strftime('%H:%M:%S')}"
        }
        
        response = self.make_api_request("POST", "/focus/session/start", data)
        
        if response and response.status_code == 200:
            result = response.json()
            self.session_id = result["session_id"]
            self.update_status(f"Session started: {self.session_id}")
            self.log_response("Start Session", result)
        else:
            self.update_status("Failed to start session")
            
    def send_test_frame(self):
        """Send a test frame to focus service."""
        # Create a test image with a face-like pattern
        img = Image.new('RGB', (320, 240), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # Draw a simple face-like shape
        draw.ellipse([100, 80, 220, 160], fill='peachpuff', outline='black')
        draw.ellipse([120, 100, 140, 120], fill='black')  # Left eye
        draw.ellipse([180, 100, 200, 120], fill='black')  # Right eye
        draw.ellipse([145, 130, 175, 150], fill='red')    # Mouth
        
        # Convert to base64
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        frame_data = f"data:image/jpeg;base64,{img_base64}"
        
        data = {
            "user_id": self.user_id,
            "frame_data": frame_data,
            "image_width": 320,
            "image_height": 240
        }
        
        response = self.make_api_request("POST", "/focus/analyze", data)
        
        if response and response.status_code == 200:
            result = response.json()
            self.update_status(f"Frame analyzed: {result['current_state']} (Score: {result['focus_score']:.1f}%)")
            self.log_response("Frame Analysis", result)
        else:
            self.update_status("Failed to analyze frame")
            
    def get_session_data(self):
        """Get current session data."""
        response = self.make_api_request("GET", f"/focus/session/{self.user_id}")
        
        if response and response.status_code == 200:
            result = response.json()
            self.update_status(f"Session data retrieved: {result['total_frames']} frames")
            self.log_response("Session Data", result)
        else:
            self.update_status("Failed to get session data")
            
    def end_focus_session(self):
        """End focus tracking session."""
        response = self.make_api_request("POST", "/focus/session/end", params={"user_id": self.user_id})
        
        if response and response.status_code == 200:
            result = response.json()
            self.session_id = None
            self.update_status(f"Session ended: Final score {result['focus_score']:.1f}%")
            self.log_response("End Session", result)
        else:
            self.update_status("Failed to end session")
            
    def get_active_users(self):
        """Get list of active users."""
        response = self.make_api_request("GET", "/focus/users/active")
        
        if response and response.status_code == 200:
            result = response.json()
            self.update_status(f"Active users: {result['total_count']}")
            self.log_response("Active Users", result)
        else:
            self.update_status("Failed to get active users")
            
    def cleanup_sessions(self):
        """Cleanup inactive sessions."""
        response = self.make_api_request("POST", "/focus/cleanup")
        
        if response and response.status_code == 200:
            result = response.json()
            self.update_status(f"Cleanup completed: {result['active_users']} active users")
            self.log_response("Cleanup Sessions", result)
        else:
            self.update_status("Failed to cleanup sessions")
    
    # === Other API Methods ===
    
    def health_check(self):
        """Check API health."""
        # Check main health
        response = self.make_api_request("GET", "/health")
        if response:
            self.log_response("Main Health", response.json() if response.status_code == 200 else f"Error: {response.status_code}")
        
        # Check focus health
        response = self.make_api_request("GET", "/focus/health")
        if response:
            self.log_response("Focus Health", response.json() if response.status_code == 200 else f"Error: {response.status_code}")
            
        self.update_status("Health check completed")
        
    def create_user(self):
        """Create a new user."""
        data = {
            "user_id": f"test_user_{int(time.time())}"
        }
        
        response = self.make_api_request("POST", "/users", data)
        
        if response and response.status_code == 200:
            result = response.json()
            self.update_status(f"User created: {result['user_id']}")
            self.log_response("Create User", result)
        else:
            self.update_status("Failed to create user")
            
    def get_current_user(self):
        """Get current user info."""
        # This would need authentication in a real app
        self.update_status("Get current user requires authentication")
        self.log_response("Get User", "Authentication required for this endpoint")
        
    def get_statistics(self):
        """Get system statistics."""
        response = self.make_api_request("GET", "/analytics/statistics")
        
        if response and response.status_code == 200:
            result = response.json()
            self.update_status("Statistics retrieved")
            self.log_response("Statistics", result)
        else:
            self.update_status("Failed to get statistics")
            
    def start_async_training(self):
        """Start async training."""
        data = {
            "user_id": self.user_id,
            "training_config": {
                "model_type": "random_forest",
                "features": ["angle_variance", "stability_score", "presence_ratio", "context_switches"]
            }
        }
        
        response = self.make_api_request("POST", "/models/train/async", data)
        
        if response and response.status_code == 200:
            result = response.json()
            self.update_status(f"Training started: {result['task_id']}")
            self.log_response("Start Training", result)
        else:
            self.update_status("Failed to start training")
            
    def get_training_status(self):
        """Get training status."""
        # This would need a task_id, using a placeholder
        task_id = "test_task_123"
        response = self.make_api_request("GET", f"/models/train/status/{task_id}")
        
        if response:
            self.log_response("Training Status", response.json() if response.status_code == 200 else f"Error: {response.status_code}")
            self.update_status("Training status retrieved")
        else:
            self.update_status("Failed to get training status")
    
    # === Camera Methods ===
    
    def toggle_camera(self):
        """Toggle camera on/off."""
        if not self.camera_active:
            self.start_camera()
        else:
            self.stop_camera()
            
    def start_camera(self):
        """Start camera capture."""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Camera Error", "Cannot open camera")
                return
                
            self.camera_active = True
            self.camera_button.config(text="Stop Camera")
            self.send_camera_frame_button.config(state=tk.NORMAL)
            self.update_status("Camera started")
            
            # Start video loop
            self.video_loop()
            
        except Exception as e:
            messagebox.showerror("Camera Error", f"Failed to start camera: {str(e)}")
            
    def stop_camera(self):
        """Stop camera capture."""
        if self.cap:
            self.cap.release()
            
        self.camera_active = False
        self.camera_button.config(text="Start Camera")
        self.send_camera_frame_button.config(state=tk.DISABLED)
        self.update_status("Camera stopped")
        
        # Clear video display
        self.video_label.config(image="", text="Camera feed will appear here")
        
    def video_loop(self):
        """Main video capture loop."""
        if self.camera_active and self.cap:
            ret, frame = self.cap.read()
            if ret:
                # Convert frame for display
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                img = img.resize((320, 240), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image=img)
                
                # Update display
                self.video_label.config(image=photo, text="")
                self.video_label.image = photo  # Keep reference
                
                # Auto-send if enabled
                if self.auto_send_var.get():
                    self.auto_send_timer = self.root.after(1000, self.auto_send_frame)
            
            # Schedule next frame
            self.root.after(30, self.video_loop)
            
    def send_camera_frame(self):
        """Send current camera frame to focus service."""
        if self.camera_active and self.cap:
            ret, frame = self.cap.read()
            if ret:
                # Convert frame to base64
                _, buffer = cv2.imencode('.jpg', frame)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                frame_data = f"data:image/jpeg;base64,{frame_base64}"
                
                height, width = frame.shape[:2]
                
                data = {
                    "user_id": self.user_id,
                    "frame_data": frame_data,
                    "image_width": width,
                    "image_height": height
                }
                
                response = self.make_api_request("POST", "/focus/analyze", data)
                
                if response and response.status_code == 200:
                    result = response.json()
                    self.update_status(f"Camera frame: {result['current_state']} (Score: {result['focus_score']:.1f}%)")
                else:
                    self.update_status("Failed to send camera frame")
                    
    def auto_send_frame(self):
        """Auto-send camera frame (called by timer)."""
        if self.auto_send_var.get() and self.camera_active:
            self.send_camera_frame()
            
    def on_closing(self):
        """Handle window closing."""
        if self.camera_active:
            self.stop_camera()
        self.root.destroy()


def main():
    """Main function to run the GUI demo client."""
    root = tk.Tk()
    app = FocusAPIDemoClient(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the GUI
    root.mainloop()


if __name__ == "__main__":
    main()
