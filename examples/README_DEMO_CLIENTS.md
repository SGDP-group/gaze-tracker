# Demo Clients for Focus Management System

This directory contains demo clients to test the Focus Management System API endpoints with interactive interfaces.

## Available Demo Clients

### 1. GUI Demo Client (Python/Tkinter)
**File:** `gui_demo_client.py`

A desktop application with buttons to test all API endpoints, including camera integration.

**Features:**
- 🎯 Focus Service endpoints (start/stop sessions, frame analysis)
- 🔧 Other API endpoints (health check, user management, training)
- 📹 Camera integration with real-time frame sending
- 📊 Response logging and status updates
- ⚙️ Configurable API URL and user ID

**Requirements:**
```bash
# Install GUI dependencies
pip install pillow requests opencv-python

# tkinter usually comes with Python, but if needed:
# Ubuntu/Debian: sudo apt-get install python3-tk
# macOS: Usually included with Python
# Windows: Usually included with Python
```

**Usage:**
```bash
cd examples
python gui_demo_client.py
```

**Screenshot Preview:**
```
┌─────────────────────────────────────────────────────────────┐
│ Focus Management System API Demo                           │
├─────────────────────────────────────────────────────────────┤
│ ⚙️ API Configuration                                        │
│ API URL: [http://localhost:8000________] User ID: [demo_user]│
│                                                             │
│ 🎯 Focus Service              🔧 Other API Endpoints        │
│ [Start Session] [Send Test]    [Health Check] [Create User] │
│ [Get Session] [End Session]    [Get Stats] [Start Training] │
│ [Active Users] [Cleanup]       [Training Status] [Test All] │
│                                                             │
│ 📹 Video Test                                               │
│ [Start Camera] [Stop Camera] [Send Frame] ☑ Auto Send      │
│ ┌─────────────┐ ┌─────────────┐                           │
│ │ Camera Feed │ │ Focus Info  │                           │
│ └─────────────┘ └─────────────┘                           │
│                                                             │
│ 📋 API Responses                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [12:34:56] Start Session:                                │ │
│ │ {"user_id": "demo_user", "session_id": "abc123"}        │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ ● Ready                                     12:34:56       │
└─────────────────────────────────────────────────────────────┘
```

### 2. Web Demo Client (HTML/JavaScript)
**File:** `web_demo_client.html`

A modern web interface for testing API endpoints from any browser.

**Features:**
- 🎨 Modern responsive design with gradient backgrounds
- 📱 Mobile-friendly interface
- 📹 WebRTC camera integration
- 🔄 Auto-send frames functionality
- 📊 Real-time focus information display
- 🎯 All API endpoints accessible via buttons

**Usage:**
```bash
# Simply open in your browser
open examples/web_demo_client.html

# Or serve with a simple HTTP server
cd examples
python -m http.server 8080
# Then visit http://localhost:8080/web_demo_client.html
```

**Browser Features:**
- Camera access via WebRTC
- Canvas-based frame processing
- Responsive grid layout
- Real-time status updates
- Color-coded focus states

### 3. Command Line Client (Python)
**File:** `focus_client_example.py`

A programmatic client showing how to integrate with the API.

**Features:**
- 📹 Webcam integration
- 👥 Multi-user demo
- 🖼️ Static image demo
- 📊 Session management
- 🔄 Frame processing loop

**Usage:**
```bash
cd examples
python focus_client_example.py

# Choose demo:
# 1. Webcam demo (requires camera)
# 2. Image demo (static images)
# 3. Multi-user demo (concurrent sessions)
```

## API Testing Workflow

### 1. Start the API Server
```bash
# In the main project directory
uv run python -m src.api.main
```

### 2. Test with Demo Client

**GUI Client:**
1. Launch `python gui_demo_client.py`
2. Click "Health Check" to verify connection
3. Click "Start Session" to begin tracking
4. Use "Send Test Frame" or camera to test focus analysis
5. Monitor responses in the log area

**Web Client:**
1. Open `web_demo_client.html` in browser
2. Verify API URL configuration
3. Click "Health Check" to test connection
4. Start camera and enable auto-send for real-time testing
5. Watch focus information update in real-time

**Command Line:**
1. Run `python focus_client_example.py`
2. Select webcam demo for real-time testing
3. Follow on-screen instructions

## Testing Scenarios

### Basic Focus Tracking
1. **Start Session** → Initialize user session
2. **Send Test Frame** → Test with synthetic face image
3. **Get Session Data** → Check session statistics
4. **End Session** → Finalize and get results

### Real-time Camera Testing
1. **Start Camera** → Initialize webcam
2. **Enable Auto-Send** → Send frames automatically
3. **Monitor Focus** → Watch state changes in real-time
4. **Stop Camera** → End camera session

### Multi-User Testing
1. **Multiple Sessions** → Start sessions for different users
2. **Concurrent Frames** → Send frames from multiple users
3. **Active Users** → Check user separation
4. **Cleanup** → Remove inactive sessions

### API Health Testing
1. **Health Check** → Verify service status
2. **Create User** → Test user management
3. **Get Statistics** → Check system metrics
4. **Start Training** → Test async operations

## Expected Results

### Successful Response Example
```json
{
  "user_id": "demo_user_123",
  "current_state": "FOCUSED",
  "focus_score": 85.5,
  "baseline_angle": 12.3,
  "face_metrics": {
    "centroid": {"x": 320, "y": 240},
    "angle": 15.7,
    "magnitude": 25.4,
    "confidence": 0.92
  },
  "session_stats": {
    "total_frames": 150,
    "focused_frames": 128,
    "distracted_frames": 15,
    "away_frames": 7
  }
}
```

### Focus States
- **FOCUSED** (Green): User looking at screen
- **DISTRACTED** (Red): User looking away for >2 seconds
- **AWAY** (Gray): No face detected

## Troubleshooting

### Common Issues

**API Connection Failed:**
- Verify API server is running: `uv run python -m src.api.main`
- Check API URL in client configuration
- Ensure no firewall blocking port 8000

**Camera Not Working:**
- Grant camera permissions in browser/system
- Check if camera is being used by another application
- Verify camera drivers are installed

**Frame Analysis Fails:**
- Check MediaPipe model file: `detector.tflite`
- Verify frame format (JPEG base64)
- Check image dimensions (minimum 320x240)

**Session Not Found:**
- Start session before sending frames
- Verify user ID consistency
- Check session hasn't expired (30min timeout)

### Debug Mode

**Enable Debug Logging:**
```bash
# Set log level
export LOG_LEVEL=DEBUG

# Start API server
uv run python -m src.api.main
```

**Browser Console:**
- Open Developer Tools (F12)
- Check Network tab for API requests
- Monitor Console for JavaScript errors

## Performance Tips

### Client Side
- Send frames every 3rd frame for better performance
- Use JPEG quality 80-90 for balance
- Limit concurrent users for testing

### Server Side
- Monitor active sessions count
- Use cleanup for inactive sessions
- Check memory usage with multiple users

## Next Steps

### Custom Integration
Use the command-line client as a template for your own integration:

```python
from focus_client_example import FocusTrackingClient

client = FocusTrackingClient("http://your-api-server.com")
client.start_session("your_user_id")
result = client.send_frame(frame)
final_data = client.end_session()
```

### Production Deployment
- Add authentication to API endpoints
- Implement rate limiting
- Use HTTPS for secure communication
- Add monitoring and logging

These demo clients provide comprehensive testing capabilities for the Focus Management System API with user-friendly interfaces! 🎯
