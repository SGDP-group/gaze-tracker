# Focus Tracking API Documentation

## Overview

The Focus Management System now provides API-based focus tracking, allowing clients to send frames for server-side processing with user separation. This enables multi-user applications where focus tracking is performed centrally on the server.

## Architecture

```
Client Application → API Server → Focus Service
       ↓                    ↓              ↓
   Capture Frame    →   Process Frame   →   Analyze Focus
   Send to API      →   Extract Face    →   Update Session
   Receive Results  →   Calculate Angle →   Return State
```

## API Endpoints

### 1. Start Focus Session
```http
POST /api/v1/focus/session/start
```

**Request Body:**
```json
{
  "user_id": "user123",
  "session_name": "Morning Work Session",
  "settings": {
    "focus_threshold": 20,
    "distraction_threshold": 30
  }
}
```

**Response:**
```json
{
  "user_id": "user123",
  "session_id": "session_abc123",
  "session_start": "2024-01-01T10:00:00Z",
  "status": "active",
  "message": "Focus tracking session started for user user123"
}
```

### 2. Analyze Frame
```http
POST /api/v1/focus/analyze
```

**Request Body:**
```json
{
  "user_id": "user123",
  "frame_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABA...",
  "image_width": 640,
  "image_height": 480,
  "timestamp": "2024-01-01T10:00:01Z"
}
```

**Response:**
```json
{
  "user_id": "user123",
  "current_state": "FOCUSED",
  "focus_score": 85.5,
  "baseline_angle": 12.3,
  "face_metrics": {
    "centroid": {"x": 320, "y": 240},
    "angle": 15.7,
    "magnitude": 25.4,
    "eye_gap": 45.2,
    "confidence": 0.92,
    "timestamp": "2024-01-01T10:00:01Z"
  },
  "session_stats": {
    "total_frames": 150,
    "focused_frames": 128,
    "distracted_frames": 15,
    "away_frames": 7,
    "session_duration": 5.0
  },
  "timestamp": "2024-01-01T10:00:01Z"
}
```

### 3. Get Session Data
```http
GET /api/v1/focus/session/{user_id}
```

**Response:**
```json
{
  "user_id": "user123",
  "session_start": "2024-01-01T10:00:00Z",
  "session_end": "2024-01-01T10:05:00Z",
  "total_frames": 9000,
  "focused_frames": 7650,
  "distracted_frames": 900,
  "away_frames": 450,
  "focus_score": 85.0,
  "baseline_angle": 12.3
}
```

### 4. End Session
```http
POST /api/v1/focus/session/end?user_id=user123
```

**Response:** Same as Get Session Data with final results.

### 5. Get Active Users
```http
GET /api/v1/focus/users/active
```

**Response:**
```json
{
  "active_users": ["user123", "user456", "user789"],
  "total_count": 3,
  "timestamp": "2024-01-01T10:05:00Z"
}
```

### 6. Health Check
```http
GET /api/v1/focus/health
```

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 3,
  "service_version": "1.0.0",
  "timestamp": "2024-01-01T10:05:00Z"
}
```

## Focus States

| State | Description | Trigger |
|-------|-------------|---------|
| **FOCUSED** | User is attentive and focused | Angle < 20° from baseline |
| **DISTRACTED** | User is looking away | Angle > 30° for 2+ seconds |
| **AWAY** | No face detected | No face in frame |

## Client Integration

### Python Client Example

```python
import requests
import base64
import cv2

class FocusTrackingClient:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.user_id = None
    
    def start_session(self, user_id):
        response = requests.post(
            f"{self.api_url}/api/v1/focus/session/start",
            json={"user_id": user_id}
        )
        self.user_id = user_id
        return response.json()
    
    def send_frame(self, frame):
        # Convert OpenCV frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        frame_data = f"data:image/jpeg;base64,{frame_base64}"
        
        height, width = frame.shape[:2]
        
        response = requests.post(
            f"{self.api_url}/api/v1/focus/analyze",
            json={
                "user_id": self.user_id,
                "frame_data": frame_data,
                "image_width": width,
                "image_height": height
            }
        )
        
        return response.json()
    
    def end_session(self):
        response = requests.post(
            f"{self.api_url}/api/v1/focus/session/end",
            params={"user_id": self.user_id}
        )
        return response.json()

# Usage
client = FocusTrackingClient()
client.start_session("user123")

# Process frames from webcam
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    result = client.send_frame(frame)
    print(f"Focus state: {result['current_state']}")
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

final_data = client.end_session()
print(f"Final focus score: {final_data['focus_score']:.1f}%")
```

### JavaScript Client Example

```javascript
class FocusTrackingClient {
    constructor(apiUrl = 'http://localhost:8000') {
        this.apiUrl = apiUrl;
        this.userId = null;
    }
    
    async startSession(userId) {
        const response = await fetch(`${this.apiUrl}/api/v1/focus/session/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        this.userId = userId;
        return await response.json();
    }
    
    async sendFrame(canvas) {
        const frameData = canvas.toDataURL('image/jpeg');
        const response = await fetch(`${this.apiUrl}/api/v1/focus/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: this.userId,
                frame_data: frameData,
                image_width: canvas.width,
                image_height: canvas.height
            })
        });
        return await response.json();
    }
    
    async endSession() {
        const response = await fetch(`${this.apiUrl}/api/v1/focus/session/end?user_id=${this.userId}`, {
            method: 'POST'
        });
        return await response.json();
    }
}

// Usage with video element
const client = new FocusTrackingClient();
await client.startSession('web_user_123');

const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

setInterval(async () => {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const result = await client.sendFrame(canvas);
    console.log('Focus state:', result.current_state);
}, 100); // Send frame every 100ms
```

## Frame Format Requirements

### Supported Formats
- **JPEG**: Recommended for size/quality balance
- **PNG**: Higher quality, larger file size
- **Base64 encoding**: Required for API transmission

### Resolution Guidelines
- **Minimum**: 320x240 pixels
- **Recommended**: 640x480 pixels
- **Maximum**: 1920x1080 pixels

### Frame Rate
- **Client sending**: 10-30 FPS
- **Server processing**: Real-time per frame
- **Recommended**: Send every 3rd frame for performance

## User Session Management

### Session Isolation
- Each user_id maintains separate session data
- Baseline angles are tracked per user
- Focus buffers are independent per user

### Session Lifecycle
1. **Start**: Initialize session with user_id
2. **Active**: Process frames and update state
3. **End**: Finalize session and return results
4. **Cleanup**: Automatic cleanup after 30 minutes inactivity

### Concurrent Users
- **Maximum**: Limited by server resources
- **Memory**: ~1MB per active session
- **CPU**: ~5-10% per active user at 10 FPS

## Performance Considerations

### Client Side
- **Frame compression**: Use JPEG quality 80-90%
- **Frame rate**: 10-15 FPS for real-time
- **Batch processing**: Send frames in batches if needed

### Server Side
- **Processing time**: ~50-100ms per frame
- **Memory usage**: Proportional to active users
- **Scalability**: Horizontal scaling with load balancers

### Optimization Tips
```python
# Send every 3rd frame for performance
if frame_count % 3 == 0:
    result = client.send_frame(frame)

# Use lower resolution for better performance
small_frame = cv2.resize(frame, (320, 240))

# Compress frames before sending
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
_, buffer = cv2.imencode('.jpg', frame, encode_param)
```

## Error Handling

### Common Errors
| Error Code | Description | Solution |
|------------|-------------|----------|
| 400 | Invalid frame data | Check base64 encoding |
| 404 | Session not found | Start session first |
| 422 | Missing fields | Include all required fields |
| 500 | Server error | Check server logs |

### Error Response Format
```json
{
  "error": "ValidationError",
  "message": "Missing required field: user_id",
  "details": {
    "field": "user_id",
    "expected": "string"
  },
  "timestamp": "2024-01-01T10:00:00Z"
}
```

## Security Considerations

### Authentication
- API key authentication recommended for production
- Rate limiting to prevent abuse
- User ID validation

### Data Privacy
- Frames are processed in memory only
- No persistent storage of frame data
- Session data retention configurable

### Network Security
- HTTPS for production deployments
- CORS configuration for web clients
- Request size limits

## Deployment

### Docker Setup
```yaml
version: '3.8'
services:
  focus-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Environment Variables
```bash
export API_HOST=0.0.0.0
export API_PORT=8000
export REDIS_URL=redis://localhost:6379
export LOG_LEVEL=INFO
```

## Monitoring

### Metrics
- Active sessions count
- Frames processed per second
- Average processing time
- Error rates

### Health Checks
```bash
# Service health
curl http://localhost:8000/api/v1/focus/health

# Active users
curl http://localhost:8000/api/v1/focus/users/active
```

### Logging
- Session start/end events
- Frame processing errors
- Performance metrics
- User activity logs

## Testing

### Unit Tests
```bash
# Run focus API tests
uv run pytest tests/test_focus_api.py -v
```

### Integration Tests
```bash
# Run example client
python examples/focus_client_example.py
```

### Load Testing
```bash
# Test with multiple concurrent users
python examples/multi_user_demo.py
```

## Migration from Webcam

### Changes Required
1. **Remove webcam code** from main.py
2. **Add API client** integration
3. **Convert frames** to base64
4. **Handle responses** from API
5. **Update UI** for remote processing

### Benefits
- **Multi-user support**: Server-side processing
- **Scalability**: Horizontal scaling possible
- **Resource sharing**: Centralized face detection
- **Data persistence**: Server-side session storage

This API-based approach enables robust, multi-user focus tracking applications with centralized processing and management.
