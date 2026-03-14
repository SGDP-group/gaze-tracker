# Focus Algorithm Configuration Guide

## Overview

The focus tracking system uses configurable parameters that can be tuned for different user types and work environments. All algorithm parameters are centralized in `src/config.py`.

## Quick Configuration

```python
from src.config import config

# Adjust focus detection sensitivity
config.FOCUSED_ANGLE_THRESHOLD = 25  # More lenient
config.DISTRACTED_ANGLE_THRESHOLD = 35

# Make achievements easier to earn
config.ACHIEVEMENT_THRESHOLDS['dedicated_focus'] = 10
config.ACHIEVEMENT_THRESHOLDS['hour_power'] = 1

# Adjust inconsistency penalties
config.INCONSISTENCY_PENALTY_FACTOR = 0.05  # Mild penalty
config.MAX_INCONSISTENCY_PENALTY = 5.0  # Small impact

# Or disable penalties entirely
config.INCONSISTENCY_PENALTY_ENABLED = False
```

## Key Parameters

### Focus Detection
- **FOCUSED_ANGLE_THRESHOLD** (15-25°): Maximum angle for "focused" state
- **DISTRACTED_ANGLE_THRESHOLD** (25-35°): Minimum angle for "distracted" state
- **DISTRACTION_CONFIRMATION_TIME** (1-4s): Time to confirm distraction

### Realistic Scores
- **MAX_REALISTIC_FOCUS_SCORE** (90-98%): Maximum achievable focus score
- **HIGH_FOCUS_THRESHOLD** (80-90%): Threshold for "high focus" calculations
- **INCONSISTENCY_PENALTY_ENABLED** (True/False): Enable/disable inconsistency penalties
- **INCONSISTENCY_PENALTY_FACTOR** (0.05-0.2): Penalty for state changes
- **MAX_INCONSISTENCY_PENALTY** (5-20%): Maximum penalty percentage

### Analytics
- **CONTEXT_SWITCH_RECOVERY_MINUTES** (15-30): Minutes lost per interruption
- **MINIMUM_INTERUPTION_DURATION_SECONDS** (30-300): Minimum time for interruption counting

### Gamification
- **ACHIEVEMENT_THRESHOLDS**: Sessions/time needed for each achievement
- **STREAK_RESET_HOURS** (24-72): Hours without session to break streak

## Pre-configured Scenarios

### 1. Beginner-Friendly
```python
config.FOCUSED_ANGLE_THRESHOLD = 25
config.DISTRACTED_ANGLE_THRESHOLD = 35
config.DISTRACTION_CONFIRMATION_TIME = 3.0
config.MAX_REALISTIC_FOCUS_SCORE = 93
```

### 2. Power User (Strict)
```python
config.FOCUSED_ANGLE_THRESHOLD = 15
config.DISTRACTED_ANGLE_THRESHOLD = 25
config.DISTRACTION_CONFIRMATION_TIME = 1.0
config.MAX_REALISTIC_FOCUS_SCORE = 98
config.INCONSISTENCY_PENALTY_FACTOR = 0.2
config.MAX_INCONSISTENCY_PENALTY = 20.0
```

### 3. Creative Work (Natural Movement)
```python
config.FOCUSED_ANGLE_THRESHOLD = 30
config.DISTRACTED_ANGLE_THRESHOLD = 40
config.DISTRACTION_CONFIRMATION_TIME = 4.0
config.MINIMUM_INTERUPTION_DURATION_SECONDS = 120
config.CONTEXT_SWITCH_RECOVERY_MINUTES = 25
config.INCONSISTENCY_PENALTY_FACTOR = 0.05  # More lenient for creative thinking
```

## Tuning Process

1. **Start with defaults** - Use baseline values for new users
2. **Collect feedback** - Monitor user engagement and accuracy reports
3. **Adjust one parameter** - Change only one setting at a time
4. **Measure impact** - Track changes in user behavior and metrics
5. **Iterate** - Continue refining based on data

## Validation

```python
# Check if configuration is valid
validation = config.validate_config()
if not validation["valid"]:
    for warning in validation["warnings"]:
        print(f"Warning: {warning}")
```

## Complete Tuning Guide

For comprehensive guidance, run:
```python
print(config.get_tuning_guide())
```

This provides detailed explanations of each parameter, common tuning scenarios, and best practices for different user types.
