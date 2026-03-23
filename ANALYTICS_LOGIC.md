# Focus Analytics Logic Explained

This document explains the technical logic behind each session analytics metric, including the specific code calculations and thresholds used.

## Table of Contents
- [Deep Work Metrics](#deep-work-metrics)
- [Distraction Analytics](#distraction-analytics)
- [Biological Trends](#biological-trends)
- [Gamification Stats](#gamification-stats)
- [Focus States Logic](#focus-states-logic)
- [Raw Calculations](#raw-calculations)

---

## Deep Work Metrics

### Focus Duration

**What it measures**: Total time spent in focused state during the session.

**Code Logic**:
```python
# Calculate focus duration from frame data
focus_duration_seconds = (focused_frames / total_frames) * session_duration_seconds
focus_duration_hours = focus_duration_seconds / 3600
```

**Technical Details**:
- Uses frame-based time calculation
- `focused_frames`: Count of frames classified as "FOCUSED"
- `total_frames`: Total frames processed in session
- `session_duration_seconds`: Actual session time from timestamps
- Converts to hours for reporting

**Example**: 240 focused frames / 300 total frames = 80% focus ratio
If session duration is 60 seconds: 0.8 × 60 = 48 seconds focused

### Focus-to-Rest Ratio

**What it measures**: Ratio of focused time to non-focused (distracted + away) time.

**Code Logic**:
```python
# Calculate rest frames (distracted + away)
rest_frames = distracted_frames + away_frames
focus_to_rest_ratio = focused_frames / max(rest_frames, 1) if rest_frames > 0 else focused_frames
```

**Technical Details**:
- `rest_frames`: Combined distracted and away frames
- Division by max(rest_frames, 1) prevents division by zero
- If no rest frames, ratio equals focused_frames count
- Higher ratio = better focus consistency

**Example**: 240 focused / 60 rest = 4.0 ratio (4:1 focus to rest)

### Longest Focus Streak

**What it measures**: Longest continuous period without state changes.

**Code Logic**:
```python
def _calculate_longest_focus_streak(self, session_data):
    streaks = session_data.get("focus_streaks", [])
    if streaks:
        longest = max(streaks, key=lambda x: x.get("duration_seconds", 0))
        return longest.get("duration_seconds", 0)
    return 0
```

**Technical Details**:
- Tracks consecutive FOCUSED state periods
- `focus_streaks`: List of {start_time, end_time, duration_seconds}
- Finds maximum duration from all streaks
- Measured in seconds, converted to minutes for display

**Example**: Streak of 600 seconds = 10.0 minutes longest focus streak

### Session Completion Rate

**What it measures**: Percentage of sessions that reach completion vs abandonment.

**Code Logic**:
```python
def _calculate_completion_rate(self, historical_sessions):
    if not historical_sessions:
        return 100.0  # Default for new users
    
    completed_sessions = sum(1 for s in historical_sessions if s.get("completed", False))
    completion_rate = (completed_sessions / len(historical_sessions)) * 100
    return completion_rate
```

**Technical Details**:
- `completed`: Boolean flag set when session properly ends
- Analyzes historical session data
- 100% for new users (no history available)
- Higher rate = better session completion habits

### Focus Efficiency

**What it measures**: Overall focus percentage for the current session.

**Code Logic**:
```python
focus_efficiency = (focused_frames / max(total_frames, 1)) * 100
```

**Technical Details**:
- Simple percentage calculation
- Includes inconsistency penalties if enabled
- `max(total_frames, 1)` prevents division by zero
- Primary measure of session quality

---

## Distraction Analytics

### Interruption Count

**What it measures**: Number of significant interruptions (>1 minute) during session.

**Code Logic**:
```python
def _count_interruptions(self, focus_buffer, session_duration, total_frames):
    if not focus_buffer or total_frames == 0:
        return 0
    
    interruptions = 0
    in_distraction = False
    distraction_frames = 0
    
    # Calculate frames per minute for threshold
    frames_per_minute = total_frames / max(session_duration / 60, 1)
    min_interruption_frames = frames_per_minute * (MINIMUM_INTERUPTION_DURATION_SECONDS / 60)
    
    for state in focus_buffer:
        if state == "DISTRACTED":
            distraction_frames += 1
            in_distraction = True
        else:
            if in_distraction and distraction_frames >= min_interruption_frames:
                interruptions += 1
            distraction_frames = 0
            in_distraction = False
    
    return interruptions
```

**Technical Details**:
- `MINIMUM_INTERUPTION_DURATION_SECONDS`: 60 seconds default
- Counts consecutive DISTRACTED frames
- Only counts if distraction duration exceeds threshold
- Converts time threshold to frame count based on FPS

**Example**: At 5 FPS, 60 seconds = 300 frames minimum for interruption

### Context Switching Cost

**What it measures**: Total productivity loss in minutes due to interruptions.

**Code Logic**:
```python
context_switch_cost_minutes = interruption_count * CONTEXT_SWITCH_RECOVERY_MINUTES
```

**Technical Details**:
- `CONTEXT_SWITCH_RECOVERY_MINUTES`: 23 minutes default (research-based)
- Linear multiplication: interruptions × recovery time
- Based on studies showing 15-25 minutes to refocus after interruption
- Represents total time lost to context switching

**Example**: 2 interruptions × 23 minutes = 46 minutes total cost

### Distraction Patterns

**What it measures**: Analysis of distraction types and transitions.

**Code Logic**:
```python
def _analyze_distraction_patterns(self, focus_buffer):
    if not focus_buffer:
        return {}
    
    distraction_count = sum(1 for state in focus_buffer if state == "DISTRACTED")
    away_count = sum(1 for state in focus_buffer if state == "AWAY")
    total_states = len(focus_buffer)
    
    # Count transitions
    transitions = 0
    for i in range(1, len(focus_buffer)):
        if focus_buffer[i] != focus_buffer[i-1]:
            transitions += 1
    
    return {
        "distraction_percentage": (distraction_count / total_states) * 100,
        "away_percentage": (away_count / total_states) * 100,
        "common_distraction_types": {"DISTRACTED": distraction_count, "AWAY": away_count},
        "total_transitions": transitions
    }
```

**Technical Details**:
- Calculates percentage of each state type
- Tracks state transitions (changes between states)
- Identifies most common distraction types
- Helps understand user behavior patterns

### Recovery Metrics

**What it measures**: Time taken to return to focused state after distractions.

**Code Logic**:
```python
def _calculate_recovery_metrics(self, session_states):
    recovery_times = []
    
    for i, state in enumerate(session_states):
        if state.get("to_state") == "FOCUSED" and state.get("from_state") in ["DISTRACTED", "AWAY"]:
            # Find next state change to calculate recovery time
            if i + 1 < len(session_states):
                start_time = datetime.fromisoformat(state["timestamp"])
                end_time = datetime.fromisoformat(session_states[i + 1]["timestamp"])
                recovery_time = (end_time - start_time).total_seconds()
                recovery_times.append(recovery_time)
    
    if recovery_times:
        return {
            "average_recovery_time_seconds": sum(recovery_times) / len(recovery_times),
            "recovery_events": len(recovery_times)
        }
    return {"average_recovery_time_seconds": 0, "recovery_events": 0}
```

**Technical Details**:
- Tracks transitions back to FOCUSED state
- Measures time between state changes
- Calculates average recovery time
- Only counts actual recovery events

---

## Biological Trends

### Focus Heatmap

**What it measures**: Performance patterns by hour of day and day of week.

**Code Logic**:
```python
def _generate_focus_heatmap(self, historical_sessions):
    heatmap = []
    
    for day in range(7):  # 0=Monday, 6=Sunday
        for hour in range(24):  # 0-23 hours
            day_hour_sessions = [
                s for s in historical_sessions 
                if datetime.fromisoformat(s["session_start"]).weekday() == day and
                   datetime.fromisoformat(s["session_start"]).hour == hour
            ]
            
            if day_hour_sessions:
                avg_score = sum(s.get("focus_score", 0) for s in day_hour_sessions) / len(day_hour_sessions)
            else:
                avg_score = 0
            
            heatmap.append({
                "day_of_week": day,
                "hour": hour,
                "focus_score": avg_score,
                "session_count": len(day_hour_sessions)
            })
    
    return heatmap
```

**Technical Details**:
- Creates 24×7 grid (168 data points)
- Groups sessions by day of week and hour
- Calculates average focus score for each time slot
- Shows when user performs best/worst
- Requires `MIN_SESSIONS_FOR_PATTERNS` for meaningful data

### Peak Performance Times

**What it measures**: Best performing hours based on historical data.

**Code Logic**:
```python
def _find_peak_performance_times(self, heatmap):
    hour_performance = defaultdict(list)
    
    for point in heatmap:
        if point["focus_score"] > 0:  # Only include hours with data
            hour_performance[point["hour"]].append(point["focus_score"])
    
    peak_times = []
    for hour, scores in hour_performance.items():
        avg_score = sum(scores) / len(scores)
        performance_level = "PEAK" if avg_score >= 85 else "HIGH" if avg_score >= 75 else "NORMAL"
        
        peak_times.append({
            "hour": hour,
            "average_focus_score": avg_score,
            "session_count": len(scores),
            "performance_level": performance_level
        })
    
    return sorted(peak_times, key=lambda x: x["average_focus_score"], reverse=True)
```

**Technical Details**:
- Aggregates performance by hour across all days
- Categorizes performance levels (PEAK/HIGH/NORMAL)
- Sorts by average focus score
- Helps identify optimal work times

### Rhythmic Insights

**What it measures**: Patterns and consistency in user's focus behavior.

**Code Logic**:
```python
def _analyze_rhythmic_patterns(self, historical_sessions):
    if len(historical_sessions) < 5:
        return {"insufficient_data": True}
    
    # Best performance day
    day_performance = defaultdict(list)
    for session in historical_sessions:
        day = datetime.fromisoformat(session["session_start"]).weekday()
        day_performance[day].append(session.get("focus_score", 0))
    
    best_day = max(day_performance.items(), key=lambda x: sum(x[1]) / len(x[1]))
    
    # Pattern consistency (standard deviation)
    all_scores = [s.get("focus_score", 0) for s in historical_sessions]
    avg_score = sum(all_scores) / len(all_scores)
    variance = sum((score - avg_score) ** 2 for score in all_scores) / len(all_scores)
    std_dev = math.sqrt(variance)
    consistency = max(0, 100 - (std_dev / avg_score * 100))
    
    return {
        "best_performance_day": best_day[0],  # 0=Monday
        "pattern_consistency": consistency,
        "average_score": avg_score,
        "score_std_deviation": std_dev
    }
```

**Technical Details**:
- Calculates best performing day of week
- Measures consistency using standard deviation
- Higher consistency = more predictable patterns
- Requires minimum sessions for meaningful analysis

---

## Gamification Stats

### Focus Streaks

**What it measures**: Consecutive days with focus sessions.

**Code Logic**:
```python
def _calculate_focus_streaks(self, historical_sessions):
    if not historical_sessions:
        return {"current_streak": 0, "longest_streak": 0, "total_active_days": 0}
    
    # Get unique session dates
    session_dates = set()
    for session in historical_sessions:
        date = datetime.fromisoformat(session["session_start"]).date()
        session_dates.add(date)
    
    # Sort dates
    sorted_dates = sorted(session_dates)
    
    # Calculate streaks
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    for i, date in enumerate(sorted_dates):
        if i == 0:
            temp_streak = 1
        else:
            # Check if consecutive (within 48 hours for streak)
            days_diff = (date - sorted_dates[i-1]).days
            if days_diff <= 2:  # STREAK_RESET_HOURS / 24
                temp_streak += 1
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
    
    longest_streak = max(longest_streak, temp_streak)
    
    # Check if current streak is still active
    today = datetime.now().date()
    if sorted_dates and (today - sorted_dates[-1]).days <= 2:
        current_streak = temp_streak
    
    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_active_days": len(sorted_dates),
        "recent_session_dates": [d.isoformat() for d in sorted_dates[-10:]]
    }
```

**Technical Details**:
- Uses unique session dates (not times)
- `STREAK_RESET_HOURS`: 48 hours grace period
- Counts consecutive days within grace period
- Tracks current and longest historical streaks

### Peer Comparison

**What it measures**: User's performance relative to other users.

**Code Logic**:
```python
def _calculate_peer_comparison(self, user_focus_score, user_sessions, user_hours, all_users_data):
    if not all_users_data or len(all_users_data) < MIN_PEERS_FOR_COMPARISON:
        return {"insufficient_data": True}
    
    # Extract peer metrics
    peer_focus_scores = []
    peer_session_counts = []
    peer_focus_hours = []
    
    for user_data in all_users_data:
        if user_data.get("focus_score"):
            peer_focus_scores.append(user_data["focus_score"])
        if user_data.get("total_sessions"):
            peer_session_counts.append(user_data["total_sessions"])
        if user_data.get("total_focus_hours"):
            peer_focus_hours.append(user_data["total_focus_hours"])
    
    # Calculate percentiles
    focus_percentile = (sum(1 for score in peer_focus_scores if score < user_focus_score) / len(peer_focus_scores)) * 100
    sessions_percentile = (sum(1 for count in peer_session_counts if count < user_sessions) / len(peer_session_counts)) * 100
    hours_percentile = (sum(1 for hours in peer_focus_hours if hours < user_hours) / len(peer_focus_hours)) * 100
    
    return {
        "focus_score_percentile": focus_percentile,
        "session_count_percentile": sessions_percentile,
        "focus_hours_percentile": hours_percentile,
        "comparison_summary": f"You focused more than {focus_percentile:.0f}% of users",
        "total_peers": len(peer_focus_scores)
    }
```

**Technical Details**:
- `MIN_PEERS_FOR_COMPARISON`: 10 users minimum
- Calculates percentiles across multiple metrics
- Anonymous comparison (no user identification)
- Higher percentile = better relative performance

### Achievements

**What it measures**: Milestones and badges based on user accomplishments.

**Code Logic**:
```python
def _track_achievements(self, historical_sessions):
    achievements = []
    thresholds = config.ACHIEVEMENT_THRESHOLDS
    
    total_sessions = len(historical_sessions)
    total_focus_time = sum(
        (s.get("focused_frames", 0) / max(s.get("total_frames", 1), 1)) * s.get("session_duration_seconds", 0)
        for s in historical_sessions
    )
    
    # Session-based achievements
    if total_sessions >= thresholds["first_session"]:
        achievements.append({"id": "first_session", "name": "First Focus"})
    
    if total_sessions >= thresholds["dedicated_focus"]:
        achievements.append({"id": "dedicated_focus", "name": "Dedicated Focus"})
    
    # Time-based achievements
    focus_hours = total_focus_time / 3600
    if focus_hours >= thresholds["hour_power"]:
        achievements.append({"id": "hour_power", "name": "Hour Power"})
    
    # Performance-based achievements
    if total_sessions >= 5:
        avg_focus = sum(s.get("focus_score", 0) for s in historical_sessions) / total_sessions
        if avg_focus >= thresholds["high_performer"]:
            achievements.append({"id": "high_performer", "name": "High Performer"})
    
    return achievements
```

**Technical Details**:
- Uses configurable thresholds from `ACHIEVEMENT_THRESHOLDS`
- Tracks session count, time spent, and performance
- Multiple achievement categories (sessions, time, performance)
- Progressive difficulty levels

---

## Focus States Logic

### State Classification

**What it measures**: Classification of user's current focus state.

**Code Logic**:
```python
# Determine focus state using config parameters
if angle_diff < config.FOCUSED_ANGLE_THRESHOLD:  # Default: 20°
    session["current_state"] = "FOCUSED"
    session["focused_frames"] += 1
elif angle_diff > config.DISTRACTED_ANGLE_THRESHOLD:  # Default: 30°
    if session["distraction_start"] is None:
        session["distraction_start"] = now
    
    elapsed = (now - session["distraction_start"]).total_seconds()
    if elapsed >= config.DISTRACTION_CONFIRMATION_TIME:  # Default: 2.0s
        session["current_state"] = "DISTRACTED"
        session["distracted_frames"] += 1
    else:
        # Grace period: still considered focused
        session["current_state"] = "FOCUSED"
        session["focused_frames"] += 1
else:
    # Between thresholds: considered focused
    session["current_state"] = "FOCUSED"
    session["focused_frames"] += 1
```

**Technical Details**:
- **FOCUSED**: `angle_diff < 20°` (configurable)
- **DISTRACTED**: `angle_diff > 30°` for 2+ seconds (configurable)
- **AWAY**: No face detected
- **Grace Period**: Prevents false distraction detection
- **Baseline Calibration**: Weighted moving average (α=0.05)

### Angle Calculation

**What it measures**: Deviation of gaze from calibrated baseline.

**Code Logic**:
```python
# Update baseline with WMA using config alpha
session["baseline_angle"] = (
    config.BASELINE_ALPHA * current_angle + 
    (1 - config.BASELINE_ALPHA) * session["baseline_angle"]
)

# Calculate angle difference
angle_diff = abs(current_angle - session["baseline_angle"])
```

**Technical Details**:
- `BASELINE_ALPHA`: 0.05 (5% weight to new measurements)
- Exponential moving average for baseline
- Absolute difference from baseline
- Lower difference = better focus alignment

### Inconsistency Penalty

**What it measures**: Penalty for frequent state changes.

**Code Logic**:
```python
def _calculate_inconsistency_penalty(self, focus_buffer):
    if not config.INCONSISTENCY_PENALTY_ENABLED or len(focus_buffer) < 10:
        return 0.0
    
    # Count state changes
    state_changes = 0
    for i in range(1, len(focus_buffer)):
        if focus_buffer[i] != focus_buffer[i-1]:
            state_changes += 1
    
    # Calculate penalty based on change frequency
    max_possible_changes = len(focus_buffer) - 1
    change_frequency = state_changes / max_possible_changes
    
    # Apply penalty factor
    penalty = change_frequency * config.INCONSISTENCY_PENALTY_FACTOR * 100
    
    # Cap at maximum penalty
    penalty = min(penalty, config.MAX_INCONSISTENCY_PENALTY)
    
    return penalty
```

**Technical Details**:
- Counts state transitions in focus buffer
- `INCONSISTENCY_PENALTY_FACTOR`: 0.1 (default)
- `MAX_INCONSISTENCY_PENALTY`: 15.0% (default)
- Only applied with 10+ frames in buffer
- Penalizes "jumpy" attention patterns

---

## Raw Calculations

### Frame-Based Metrics

**What it measures**: All calculations based on frame processing.

**Code Logic**:
```python
# Basic frame counts
total_frames = session.get("total_frames", 0)
focused_frames = session.get("focused_frames", 0)
distracted_frames = session.get("distracted_frames", 0)
away_frames = session.get("away_frames", 0)

# Percentages
focus_percentage = (focused_frames / max(total_frames, 1)) * 100
distraction_percentage = (distracted_frames / max(total_frames, 1)) * 100
away_percentage = (away_frames / max(total_frames, 1)) * 100

# Time calculations (assuming consistent FPS)
session_duration_seconds = session.get("session_duration_seconds", 0)
frames_per_second = total_frames / max(session_duration_seconds, 1)
```

### Focus Score Calculation

**What it measures**: Final focus score with all adjustments.

**Code Logic**:
```python
# Calculate base focus score
focused_count = sum(1 for state in focus_buffer if state == "FOCUSED")
base_focus_score = (focused_count / len(focus_buffer)) * 100

# Apply inconsistency penalty
inconsistency_penalty = self._calculate_inconsistency_penalty(focus_buffer)
base_focus_score = max(0, base_focus_score - inconsistency_penalty)

# Apply realistic variation
if base_focus_score > config.MAX_REALISTIC_FOCUS_SCORE:
    focus_score = config.MAX_REALISTIC_FOCUS_SCORE + (base_focus_score - config.MAX_REALISTIC_FOCUS_SCORE) * 0.3
elif base_focus_score > config.HIGH_FOCUS_THRESHOLD:
    focus_score = base_focus_score - (config.MAX_REALISTIC_FOCUS_SCORE - base_focus_score) * 0.1
else:
    import random
    focus_score = max(0, base_focus_score + random.uniform(-2, 2))

focus_score = round(focus_score, 1)
```

**Technical Details**:
- Starts with frame-based percentage
- Subtracts inconsistency penalty
- Applies realistic score capping
- Adds small randomization for natural variation
- Final rounding to 1 decimal place

---

## Summary

All analytics are derived from fundamental frame-based measurements:

1. **Frame Classification**: Each frame classified as FOCUSED/DISTRACTED/AWAY
2. **State Tracking**: Continuous monitoring of focus states
3. **Time Calculations**: Frame counts converted to time metrics
4. **Pattern Analysis**: Historical data analysis for trends
5. **Comparative Metrics**: User performance vs. peers and goals
6. **Gamification**: Achievement tracking and streaks

The system uses configurable parameters to adjust sensitivity and behavior for different user types and work environments.
