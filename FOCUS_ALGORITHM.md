# Focus Tracking Algorithm Flowchart

## System Overview

The Focus Management System uses a multi-layered approach to track user focus through real-time face detection, temporal analysis, and machine learning classification.

## Algorithm Flowchart

```mermaid
flowchart TD
    A[Start Camera] --> B[Capture Frame]
    B --> C{Face Detected?}
    
    C -->|No| D[State = AWAY]
    C -->|Yes| E[Extract Face Metrics]
    
    E --> F[Calculate Face Angle]
    F --> G[Update Baseline Angle<br/>WMA: alpha=0.05]
    G --> H[Calculate Angle Difference]
    
    H --> I{Angle Difference}
    
    I -->|< 20deg| J[State = FOCUSED]
    I -->|20deg-30deg| K[State = FOCUSED<br/>Continue Monitoring]
    I -->|> 30deg| L[Start Distraction Timer]
    
    L --> M{Timer > 2 seconds?}
    M -->|No| K
    M -->|Yes| N[State = DISTRACTED]
    
    D --> O[Update Focus Buffer]
    J --> O
    K --> O
    N --> O
    
    O --> P[Calculate Focus Score]
    P --> Q[Update Session Data]
    Q --> R{Session End?}
    
    R -->|No| B
    R -->|Yes| S[Generate Session Features]
    
    S --> T[Session-Level Features:<br/>• Angle Variance<br/>• Stability Score<br/>• Presence Ratio<br/>• Context Switches]
    T --> U[ML Classification]
    
    U --> V[Random Forest Model]
    V --> W{Prediction}
    
    W -->|Productive| X[Display: Productive Session]
    W -->|Unproductive| Y[Display: Unproductive Session]
    
    X --> Z[Generate Heatmap]
    Y --> Z
    Z --> AA[Save Session Data]
    AA --> BB[End]
    
    %% API Integration Path
    Q --> CC{API Available?}
    CC -->|Yes| DD[Send Session to API]
    CC -->|No| EE[Local Storage Only]
    
    DD --> FF[Collect User Feedback]
    FF --> GG[Update Personalized Model]
    GG --> HH[Generate Recommendations]
    HH --> R
    EE --> R
```

## Detailed Component Breakdown

### 1. Real-Time Face Detection

```mermaid
flowchart LR
    A[Camera Frame] --> B[MediaPipe Face Detector]
    B --> C[Face Landmarks]
    C --> D[Calculate Centroid]
    D --> E[Compute Yaw Angle]
    E --> F[Extract Eye Gap]
    F --> G[Face Metrics Dictionary]
```

### 2. Tri-State Focus Classifier

```mermaid
stateDiagram-v2
    [*] --> FOCUSED
    FOCUSED --> AWAY: No face detected
    AWAY --> FOCUSED: Face detected
    
    FOCUSED --> DISTRACTED: Angle > 30deg for 2s
    DISTRACTED --> FOCUSED: Angle < 20deg
    
    FOCUSED --> FOCUSED: Angle 20deg-30deg
    DISTRACTED --> DISTRACTED: Angle > 30deg
```

### 3. Baseline Angle Calibration

```mermaid
flowchart LR
    A[Current Angle] --> B[Weighted Moving Average]
    B --> C[New Baseline = alpha*Current + (1-alpha)*Old]
    C --> D[alpha = 0.05 (Slow Adaptation)]
    D --> E[Handles Natural Head Movement]
    E --> F[Reduces False Positives]
```

### 4. Session Feature Extraction

```mermaid
flowchart TD
    A[Session Data] --> B[Angle Variance]
    A --> C[Stability Score]
    A --> D[Presence Ratio]
    A --> E[Context Switches]
    
    B --> F[variance(angles)]
    C --> G[1 - CV(angle)]
    D --> H[frames_with_face / total_frames]
    E --> I[state_changes / time]
    
    F --> J[Feature Vector]
    G --> J
    H --> J
    I --> J
    
    J --> K[4-Dimensional Input]
```

### 5. Machine Learning Pipeline

```mermaid
flowchart TD
    A[Feature Vector] --> B[Random Forest Classifier]
    B --> C[Productivity Prediction]
    C --> D[Confidence Score]
    
    E[User Feedback] --> F[Label Assignment]
    F --> G[Rating ≥ 3 → Productive]
    F --> H[Rating < 3 → Unproductive]
    
    I[Training Data] --> J[Model Training]
    G --> J
    H --> J
    
    J --> K[Personalized Model]
    K --> L[Future Predictions]
```

### 6. API Integration Flow

```mermaid
sequenceDiagram
    participant M as Main.py
    participant A as API Client
    participant S as FastAPI Server
    participant C as Celery Worker
    participant R as Redis
    
    M->>A: Create Session Data
    A->>S: POST /sessions
    S-->>A: Session Created
    
    M->>A: Collect Feedback
    A->>S: POST /feedback
    S-->>A: Feedback Saved
    
    M->>A: Request Training
    A->>S: POST /models/train/async
    S->>C: Queue Training Task
    C->>R: Store Task Status
    
    loop Progress Monitoring
        M->>A: GET /models/train/status/{id}
        A->>S: Check Task Status
        S-->>A: Progress Update
    end
    
    C->>S: Training Complete
    S-->>A: Model Ready
    A-->>M: Recommendations Available
```

## Algorithm Parameters

### Real-Time Tracking
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Frame Rate | 30 FPS | Smooth video processing |
| Detection Interval | Every frame | Real-time analysis |
| WMA Alpha | 0.05 | Slow baseline adaptation |
| Focus Threshold | 20deg | Focused angle limit |
| Distraction Threshold | 30deg | Distraction trigger |
| Distraction Timer | 2.0 seconds | Confirmation delay |

### Session Analysis
| Feature | Formula | Interpretation |
|---------|---------|-------------|
| Angle Variance | variance(angles) | Movement consistency |
| Stability Score | 1 - CV(angle) | Focus stability |
| Presence Ratio | face_frames / total | Engagement level |
| Context Switches | state_changes / time | Attention shifts |

### ML Classification
| Parameter | Value | Description |
|-----------|-------|-------------|
| Model Type | Random Forest | Ensemble classifier |
| Features | 4 dimensions | Session metrics |
| Training Data | Synthetic + Real | Hybrid approach |
| Personalization | Per-user models | Adaptive learning |

## State Transitions

### Focus State Machine
```mermaid
stateDiagram-v2
    [*] --> Initializing
    Initializing --> Calibrating: Camera Ready
    Calibrating --> Tracking: Baseline Set
    
    Tracking --> Focused: |angle| < 20deg
    Tracking --> Distracted: |angle| > 30deg for 2s
    Tracking --> Away: No face detected
    
    Focused --> Tracking: Continuous monitoring
    Distracted --> Tracking: |angle| < 20deg
    Away --> Tracking: Face detected
    
    Tracking --> SessionEnd: Duration complete
    SessionEnd --> [*]: Cleanup
```

### Error Handling
```mermaid
flowchart TD
    A[Operation] --> B{Error?}
    B -->|No| C[Continue]
    B -->|Yes| D[Log Error]
    D --> E{Recoverable?}
    E -->|Yes| F[Retry/Default]
    E -->|No| G[Graceful Degradation]
    F --> C
    G --> H[Continue with Limited Features]
```

## Performance Considerations

### Optimization Points
1. **Frame Processing**: Skip frames if CPU > 80%
2. **Memory Management**: Circular buffers for session data
3. **Model Caching**: Load ML models once per session
4. **Async Operations**: Non-blocking API calls

### Resource Usage
| Component | CPU | Memory | I/O |
|-----------|-----|--------|-----|
| Face Detection | 40-60% | 100-200MB | Camera |
| Feature Extraction | 10-20% | 50-100MB | Minimal |
| ML Inference | 5-15% | 50-150MB | Model loading |
| API Calls | 5-10% | 20-50MB | Network |

This algorithm provides robust focus tracking through real-time computer vision, temporal analysis, and adaptive machine learning.
