"""
Configuration parameters for the Focus Management System.
Contains all tunable algorithm parameters with detailed tuning guidance.
"""

import os
from typing import Dict, Any

class FocusConfig:
    """Configuration class for focus tracking algorithms."""
    
    # ==================== FOCUS DETECTION THRESHOLDS ====================
    
    # Gaze angle thresholds for focus state classification
    # Lower values = more sensitive to gaze deviations
    # Higher values = more tolerant of gaze movements
    FOCUSED_ANGLE_THRESHOLD = 20.0  # degrees - Max angle deviation for "FOCUSED" state
    DISTRACTED_ANGLE_THRESHOLD = 30.0  # degrees - Min angle deviation for "DISTRACTED" state
    """
    TUNING GUIDANCE - Angle Thresholds:
    - FOCUSED_ANGLE_THRESHOLD (15-25 degrees):
      * Lower (15): Very strict focus detection, good for precision tasks
      * Higher (25): More lenient, better for natural movement
      * Adjust based on user's natural head movement patterns
    
    - DISTRACTED_ANGLE_THRESHOLD (25-35 degrees):
      * Should be 5-10 degrees higher than FOCUSED_THRESHOLD
      * Lower gap (25-30): More sensitive to distraction detection
      * Higher gap (30-35): Allows more natural look-away behavior
    """
    
    # Time-based thresholds for state transitions
    DISTRACTION_CONFIRMATION_TIME = 2.0  # seconds - Time to confirm distraction state
    """
    TUNING GUIDANCE - Distraction Confirmation:
    - 1.0-2.0 seconds: Quick distraction detection (good for high-intensity work)
    - 2.0-3.0 seconds: Balanced (default, prevents false positives)
    - 3.0-5.0 seconds: Lenient (good for casual work environments)
    
    Consider user's work style:
    * Programmers/writers: May need longer confirmation (natural thinking pauses)
    * Data entry: Shorter confirmation (maintain flow)
    """
    
    # ==================== BASELINE CALIBRATION ====================
    
    # Weighted Moving Average for baseline angle calculation
    BASELINE_ALPHA = 0.05  # Weight for new angle measurements (0.01-0.2)
    """
    TUNING GUIDANCE - Baseline Alpha:
    - Lower (0.01-0.03): Very stable baseline, slow to adapt
      * Good for consistent posture users
      * Resistant to temporary posture changes
    
    - Medium (0.05-0.1): Balanced adaptation (default)
      * Adapts to gradual posture shifts
      * Still filters out noise
    
    - Higher (0.15-0.2): Fast adaptation
      * Good for users who change positions frequently
      * May be too sensitive to noise
    
    Formula: new_baseline = (α * current_angle) + ((1-α) * old_baseline)
    """
    
    # ==================== FOCUS SCORE CALCULATION ====================
    
    # Buffer size for rolling focus score calculation
    FOCUS_BUFFER_SIZE = 50  # Number of recent frames to consider
    """
    TUNING GUIDANCE - Focus Buffer Size:
    - Smaller (20-30): More responsive to immediate changes
      * Good for real-time feedback
      * May show frequent fluctuations
    
    - Medium (40-60): Balanced (default)
      * Smooths out brief distractions
      * Still responsive to meaningful changes
    
    - Larger (80-100): Very smooth
      * Good for overall session analysis
      * May miss short focus improvements
    """
    
    # Realistic focus score parameters
    MAX_REALISTIC_FOCUS_SCORE = 99.0  # Maximum achievable focus score
    HIGH_FOCUS_THRESHOLD = 85.0  # Threshold for "high focus" calculations
    
    # Inconsistency penalties
    INCONSISTENCY_PENALTY_ENABLED = True  # Enable/disable inconsistency penalties
    INCONSISTENCY_PENALTY_FACTOR = 0.1  # Penalty factor for state changes (0.05-0.2)
    MAX_INCONSISTENCY_PENALTY = 15.0  # Maximum penalty percentage (5-20)
    """
    TUNING GUIDANCE - Realistic Focus Scores:
    - MAX_REALISTIC_FOCUS_SCORE (90-98):
      * Lower (90-93): Very strict, promotes continuous improvement
      * Higher (96-98): More lenient, better for user motivation
      * Prevents unrealistic "perfect" scores
    
    - HIGH_FOCUS_THRESHOLD (80-90):
      * Lower (80): More users get "high performer" status
      * Higher (88): Elite status reserved for exceptional focus
      * Affects achievement unlocking and insights
    
    TUNING GUIDANCE - Inconsistency Penalties:
    - INCONSISTENCY_PENALTY_FACTOR (0.05-0.2):
      * Lower (0.05): Mild penalty for frequent state changes
      * Higher (0.2): Strong penalty for inconsistent focus
      * Affects users who frequently switch between states
    
    - MAX_INCONSISTENCY_PENALTY (5-20):
      * Lower (5): Small impact on overall score
      * Higher (20): Significant impact for very inconsistent users
      * Caps the maximum penalty to prevent overly harsh scores
    
    Inconsistency is measured by:
    * Number of state changes in focus buffer
    * Frequency of FOCUSED ↔ DISTRACTED/AWAY transitions
    * Penalizes "jumpy" focus patterns
    """
    
    # ==================== DISTRACTION ANALYTICS ====================
    
    # Context switching recovery time (based on research)
    CONTEXT_SWITCH_RECOVERY_MINUTES = 23  # Minutes lost per interruption
    """
    TUNING GUIDANCE - Context Switching:
    - Research-based: Studies show 15-25 minutes to refocus after interruption
    - 15-20 minutes: For highly focused workers
    - 23 minutes: Standard research-based value (default)
    - 25-30 minutes: For complex, creative work
    
    Adjust based on:
    * Task complexity (creative work > analytical work)
    * User experience (experienced users recover faster)
    * Work environment (quiet office > open workspace)
    """
    
    # Minimum interruption duration (in frames/seconds)
    MINIMUM_INTERUPTION_DURATION_SECONDS = 60  # 1 minute
    """
    TUNING GUIDANCE - Interruption Detection:
    - 30-60 seconds: Detect brief interruptions
      * Good for high-intensity work sessions
      * May count natural pauses as interruptions
    
    - 60-120 seconds: Standard interruptions (default)
      * Filters out brief look-aways
      * Counts meaningful breaks
    
    - 180-300 seconds: Major interruptions only
      * Good for creative/deep work analysis
      * May miss smaller distractions
    """
    
    # ==================== BIOLOGICAL TRENDS ====================
    
    # Heatmap data collection parameters
    HEATMAP_HOURS = 24  # Hours in a day
    HEATMAP_DAYS = 7  # Days in a week
    """
    TUNING GUIDANCE - Biological Trends:
    - Standard 24x7 grid provides comprehensive patterns
    - Can be reduced to 12x7 for morning/evening focus only
    - Can be expanded to 48x7 for half-hour granularity
    
    Consider:
    * User's work schedule (9-5 vs flexible)
    * Data storage requirements
    * Processing time for analytics
    """
    
    # Minimum sessions for meaningful pattern analysis
    MIN_SESSIONS_FOR_PATTERNS = 5  # Sessions needed for pattern detection
    """
    TUNING GUIDANCE - Pattern Analysis:
    - 3-5 sessions: Basic pattern detection (default)
    - 7-10 sessions: More reliable patterns
    - 15+ sessions: High confidence in patterns
    
    Fewer sessions = faster insights but less accuracy
    More sessions = slower insights but higher reliability
    """
    
    # ==================== GAMIFICATION PARAMETERS ====================
    
    # Achievement thresholds
    ACHIEVEMENT_THRESHOLDS = {
        "first_session": 1,
        "dedicated_focus": 25,  # Was 10, increased for meaningful progression
        "focus_master": 100,  # Was 50, doubled for long-term engagement
        "focus_legend": 500,
        "hour_power": 2,  # Was 1, doubled for first achievement
        "deep_work_expert": 25,  # Was 10, increased significantly
        "century_club": 100,
        "focus_marathon": 500,
        "high_performer": 85,  # Focus score threshold
        "elite_focus": 90
    }
    """
    TUNING GUIDANCE - Achievement Thresholds:
    - Early achievements (1-5 sessions): Welcome new users
    - Mid achievements (25-100 sessions): Encourage consistency
    - Late achievements (500+ sessions): Reward long-term users
    
    Balance between:
    * Attainability (users should feel progress is possible)
    * Exclusivity (achievements should feel meaningful)
    * Engagement (spread achievements across user journey)
    
    Time-based achievements should align with:
    * Daily usage patterns (2 hours = reasonable daily goal)
    * Weekly habits (25 hours = full work week of focus)
    * Long-term goals (100+ hours = serious commitment)
    """
    
    # Focus streak calculations
    STREAK_RESET_HOURS = 48  # Hours without session to break streak
    """
    TUNING GUIDANCE - Streak Reset:
    - 24 hours: Daily streak (strict, encourages daily usage)
    - 48 hours: Every-other-day streak (balanced, default)
    - 72 hours: 3-day grace period (lenient, reduces pressure)
    
    Consider user psychology:
    * Strict (24h): High engagement but high abandonment risk
    * Balanced (48h): Maintains habit without excessive pressure
    * Lenient (72h): Lower pressure but less motivation for consistency
    """
    
    # ==================== PEER COMPARISON ====================
    
    # Minimum peers for meaningful comparison
    MIN_PEERS_FOR_COMPARISON = 10  # Minimum users for percentile calculation
    """
    TUNING GUIDANCE - Peer Comparison:
    - 5-10 peers: Basic comparison (faster, less accurate)
    - 10-20 peers: Standard comparison (default)
    - 50+ peers: High accuracy comparison
    
    Trade-offs:
    * Fewer peers: Faster calculations, but percentiles may be skewed
    * More peers: Accurate percentiles, but requires larger user base
    
    For new deployments: Start with lower threshold, increase as user base grows
    """
    
    # ==================== PERFORMANCE TUNING ====================
    
    # FPS calculation parameters
    FPS_CALCULATION_WINDOW = 10.0  # Seconds for rolling FPS average
    FPS_BUFFER_SIZE = 10  # Number of FPS calculations to buffer
    """
    TUNING GUIDANCE - Performance Metrics:
    - FPS_WINDOW (5-15 seconds):
      * Shorter (5s): More responsive to performance changes
      * Longer (15s): Smoother FPS readings
    
    - FPS_BUFFER (5-20 calculations):
      * Smaller: More responsive to immediate performance
      * Larger: More stable performance metrics
    
    Balance between responsiveness and stability
    """
    
    # Session cleanup parameters
    SESSION_TIMEOUT_MINUTES = 30  # Minutes before inactive session cleanup
    """
    TUNING GUIDANCE - Session Management:
    - 15-30 minutes: Standard timeout (default)
    - 45-60 minutes: For users who take long breaks
    - 5-10 minutes: For high-security environments
    
    Consider:
    * User's typical work patterns
    * Server resource constraints
    * Data retention requirements
    """
    
    @classmethod
    def get_tuning_guide(cls) -> str:
        """Return comprehensive tuning guide."""
        return """
        FOCUS ALGORITHM TUNING GUIDE
        ============================
        
        QUICK TUNING SCENARIOS:
        
        1. FOR NEW USERS (Beginner-friendly):
           - FOCUSED_ANGLE_THRESHOLD: 25 (more lenient)
           - DISTRACTION_CONFIRMATION_TIME: 3.0 (slower confirmation)
           - BASELINE_ALPHA: 0.1 (faster adaptation)
           - MAX_REALISTIC_FOCUS_SCORE: 93 (easier achievements)
        
        2. FOR POWER USERS (Strict tracking):
           - FOCUSED_ANGLE_THRESHOLD: 15 (very strict)
           - DISTRACTION_CONFIRMATION_TIME: 1.0 (quick detection)
           - BASELINE_ALPHA: 0.03 (stable baseline)
           - MAX_REALISTIC_FOCUS_SCORE: 98 (challenging)
        
        3. FOR CREATIVE WORK (Natural movement):
           - FOCUSED_ANGLE_THRESHOLD: 30 (very lenient)
           - DISTRACTION_CONFIRMATION_TIME: 4.0 (slow confirmation)
           - MINIMUM_INTERUPTION_DURATION_SECONDS: 120 (ignore brief pauses)
           - CONTEXT_SWITCH_RECOVERY_MINUTES: 25 (creative work recovery)
        
        4. FOR DATA ENTRY (High precision):
           - FOCUSED_ANGLE_THRESHOLD: 12 (extremely strict)
           - DISTRACTION_CONFIRMATION_TIME: 0.5 (immediate detection)
           - FOCUS_BUFFER_SIZE: 20 (very responsive)
           - STREAK_RESET_HOURS: 24 (daily consistency)
        
        TUNING PROCESS:
        1. Start with default values
        2. Collect user feedback on accuracy
        3. Adjust one parameter at a time
        4. Monitor impact on user engagement
        5. Iterate based on user behavior
        
        COMMON TUNING MISTAKES:
        - Making thresholds too strict (high false positives)
        - Making thresholds too lenient (missed distractions)
        - Changing multiple parameters at once
        - Not considering user's natural work patterns
        - Ignoring the psychological impact of achievements
        """
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration parameters and return warnings."""
        warnings = []
        
        # Validate angle thresholds
        if cls.FOCUSED_ANGLE_THRESHOLD >= cls.DISTRACTED_ANGLE_THRESHOLD:
            warnings.append("FOCUSED_ANGLE_THRESHOLD should be less than DISTRACTED_ANGLE_THRESHOLD")
        
        # Validate realistic scores
        if cls.MAX_REALISTIC_FOCUS_SCORE < 90 or cls.MAX_REALISTIC_FOCUS_SCORE > 99:
            warnings.append("MAX_REALISTIC_FOCUS_SCORE should be between 90-99")
        
        # Validate achievement progression
        if cls.ACHIEVEMENT_THRESHOLDS["dedicated_focus"] <= cls.ACHIEVEMENT_THRESHOLDS["first_session"]:
            warnings.append("Achievement thresholds should be progressive")
        
        # Validate buffer sizes
        if cls.FOCUS_BUFFER_SIZE < 10 or cls.FOCUS_BUFFER_SIZE > 200:
            warnings.append("FOCUS_BUFFER_SIZE should be between 10-200")
        
        return {
            "valid": len(warnings) == 0,
            "warnings": warnings
        }


# Global configuration instance
config = FocusConfig()
