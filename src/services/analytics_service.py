"""
Advanced Analytics Service for Focus Management System.
Provides comprehensive session analytics including deep work metrics, 
distraction analysis, biological trends, and gamification stats.
"""

import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

# Import configuration
from src.config import config

class AnalyticsService:
    """Advanced analytics service for focus tracking sessions."""
    
    def __init__(self):
        """Initialize analytics service with config parameters."""
        self.context_switch_recovery_time = config.CONTEXT_SWITCH_RECOVERY_MINUTES * 60  # Convert to seconds
        
    def calculate_deep_work_metrics(self, session_data: Dict, historical_sessions: List[Dict] = None) -> Dict:
        """
        Calculate Core Deep Work Metrics.
        
        Args:
            session_data: Current session data
            historical_sessions: List of user's previous sessions for context
            
        Returns:
            Dictionary containing deep work metrics
        """
        try:
            total_frames = session_data.get("total_frames", 0)
            focused_frames = session_data.get("focused_frames", 0)
            distracted_frames = session_data.get("distracted_frames", 0)
            away_frames = session_data.get("away_frames", 0)
            session_duration = session_data.get("session_duration_seconds", 0)
            
            # Focus Duration (Total & Average)
            focus_duration_seconds = (focused_frames / max(total_frames, 1)) * session_duration
            focus_duration_hours = focus_duration_seconds / 3600
            
            # Focus-to-Rest Ratio - Fixed calculation
            rest_frames = distracted_frames + away_frames
            focus_to_rest_ratio = focused_frames / max(rest_frames, 1) if rest_frames > 0 else focused_frames
            
            # Longest Focus Streak (from focus buffer)
            longest_streak_frames = self._calculate_longest_focus_streak(session_data)
            longest_streak_seconds = (longest_streak_frames / max(total_frames, 1)) * session_duration
            
            # Session Completion Rate (from historical data)
            completion_rate = self._calculate_completion_rate(historical_sessions or [])
            
            # Daily/Weekly focus duration (if historical data available)
            daily_focus = self._calculate_daily_focus_duration(historical_sessions or [])
            weekly_focus = self._calculate_weekly_focus_duration(historical_sessions or [])
            
            return {
                "focus_duration": {
                    "current_session_hours": round(focus_duration_hours, 3),
                    "current_session_seconds": round(focus_duration_seconds, 1),
                    "daily_total_hours": round(daily_focus, 2),
                    "weekly_total_hours": round(weekly_focus, 2),
                    "average_session_hours": round(self._calculate_average_session_duration(historical_sessions or []), 3)
                },
                "focus_to_rest_ratio": round(focus_to_rest_ratio, 2),
                "longest_focus_streak": {
                    "seconds": round(longest_streak_seconds, 1),
                    "minutes": round(longest_streak_seconds / 60, 2),
                    "frames": longest_streak_frames
                },
                "session_completion_rate": completion_rate,
                "focus_efficiency": round((focused_frames / max(total_frames, 1)) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating deep work metrics: {e}")
            return {}
    
    def calculate_distraction_analytics(self, session_data: Dict) -> Dict:
        """
        Calculate Distraction & Interference Analytics.
        
        Args:
            session_data: Current session data
            
        Returns:
            Dictionary containing distraction analytics
        """
        try:
            total_frames = session_data.get("total_frames", 0)
            distracted_frames = session_data.get("distracted_frames", 0)
            session_duration = session_data.get("session_duration_seconds", 0)
            focus_buffer = session_data.get("focus_buffer", [])
            
            # Interruption Count (significant distractions > 1 minute)
            interruption_count = self._count_interruptions(focus_buffer, session_duration, total_frames)
            
            # Context Switching Cost (23 minutes per interruption)
            context_switching_cost_seconds = interruption_count * self.context_switch_recovery_time
            context_switching_cost_minutes = context_switching_cost_seconds / 60
            
            # Distraction Pattern Analysis
            distraction_patterns = self._analyze_distraction_patterns(focus_buffer)
            
            # Recovery Time Analysis
            recovery_metrics = self._analyze_recovery_times(focus_buffer, session_duration, total_frames)
            
            return {
                "interruption_count": interruption_count,
                "context_switching_cost": {
                    "total_seconds": context_switching_cost_seconds,
                    "total_minutes": context_switching_cost_minutes,
                    "cost_per_interruption_minutes": self.context_switch_recovery_time / 60
                },
                "distraction_patterns": distraction_patterns,
                "recovery_metrics": recovery_metrics,
                "distraction_frequency": round((distracted_frames / max(total_frames, 1)) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating distraction analytics: {e}")
            return {}
    
    def calculate_biological_trends(self, historical_sessions: List[Dict]) -> Dict:
        """
        Calculate Biological & Rhythmic Trends.
        
        Args:
            historical_sessions: List of user's previous sessions
            
        Returns:
            Dictionary containing biological trends and heatmap data
        """
        try:
            if not historical_sessions:
                return {"heatmap_data": [], "peak_times": [], "rhythmic_insights": {}}
            
            # Focus Heatmap by hour and day of week
            heatmap_data = self._generate_focus_heatmap(historical_sessions)
            
            # Peak Performance Times
            peak_times = self._identify_peak_performance_times(historical_sessions)
            
            # Rhythmic Insights
            rhythmic_insights = self._analyze_rhythmic_patterns(historical_sessions)
            
            return {
                "focus_heatmap": heatmap_data,
                "peak_performance_times": peak_times,
                "rhythmic_insights": rhythmic_insights
            }
            
        except Exception as e:
            logger.error(f"Error calculating biological trends: {e}")
            return {}
    
    def calculate_gamification_stats(self, user_id: str, historical_sessions: List[Dict], all_users_data: List[Dict] = None) -> Dict:
        """
        Calculate Gamification & Retention Stats.
        
        Args:
            user_id: Current user ID
            historical_sessions: List of user's previous sessions
            all_users_data: Optional data from all users for peer comparison
            
        Returns:
            Dictionary containing gamification and retention statistics
        """
        try:
            # Focus Streaks (consecutive days with sessions)
            focus_streaks = self._calculate_focus_streaks(historical_sessions)
            
            # Peer Comparison (if data available)
            peer_comparison = self._calculate_peer_comparison(user_id, historical_sessions, all_users_data or [])
            
            # Achievement Tracking
            achievements = self._track_achievements(historical_sessions)
            
            # Retention Metrics
            retention_metrics = self._calculate_retention_metrics(historical_sessions)
            
            return {
                "focus_streaks": focus_streaks,
                "peer_comparison": peer_comparison,
                "achievements": achievements,
                "retention_metrics": retention_metrics
            }
            
        except Exception as e:
            logger.error(f"Error calculating gamification stats: {e}")
            return {}
    
    def generate_comprehensive_session_report(self, user_id: str, session_data: Dict, historical_sessions: List[Dict] = None, all_users_data: List[Dict] = None) -> Dict:
        """
        Generate comprehensive session analytics report.
        
        Args:
            user_id: User identifier
            session_data: Current session data
            historical_sessions: List of user's previous sessions
            all_users_data: Optional data from all users for peer comparison
            
        Returns:
            Comprehensive analytics report
        """
        try:
            report = {
                "user_id": user_id,
                "session_id": session_data.get("session_id", "unknown"),
                "report_generated_at": datetime.now().isoformat(),
                "session_summary": {
                    "duration_seconds": session_data.get("session_duration_seconds", 0),
                    "focus_score": session_data.get("focus_score", 0),
                    "productivity_level": session_data.get("productivity_level", "UNKNOWN")
                }
            }
            
            # Core Deep Work Metrics
            report["deep_work_metrics"] = self.calculate_deep_work_metrics(session_data, historical_sessions)
            
            # Distraction & Interference Analytics
            report["distraction_analytics"] = self.calculate_distraction_analytics(session_data)
            
            # Biological & Rhythmic Trends
            report["biological_trends"] = self.calculate_biological_trends(historical_sessions or [])
            
            # Gamification & Retention Stats
            report["gamification_stats"] = self.calculate_gamification_stats(user_id, historical_sessions or [], all_users_data)
            
            # Personalized Insights
            report["insights"] = self._generate_personalized_insights(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating comprehensive session report: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    def _calculate_longest_focus_streak(self, session_data: Dict) -> int:
        """Calculate longest consecutive focus frames streak."""
        focus_buffer = session_data.get("focus_buffer", [])
        max_streak = 0
        current_streak = 0
        
        for state in focus_buffer:
            if state == "FOCUSED":
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def _calculate_completion_rate(self, historical_sessions: List[Dict]) -> float:
        """Calculate session completion rate from historical data."""
        if not historical_sessions:
            return 100.0  # Default for new users
        
        completed_sessions = sum(1 for session in historical_sessions if session.get("completed", True))
        return round((completed_sessions / len(historical_sessions)) * 100, 2)
    
    def _calculate_daily_focus_duration(self, historical_sessions: List[Dict]) -> float:
        """Calculate total focus duration for today."""
        today = datetime.now().date()
        today_focus = 0.0
        
        for session in historical_sessions:
            try:
                session_date = datetime.fromisoformat(session.get("session_start", "")).date()
                if session_date == today:
                    focus_ratio = session.get("focused_frames", 0) / max(session.get("total_frames", 1), 1)
                    session_duration = session.get("session_duration_seconds", 0)
                    today_focus += (focus_ratio * session_duration) / 3600  # Convert to hours
            except (ValueError, TypeError):
                continue
        
        return round(today_focus, 2)
    
    def _calculate_weekly_focus_duration(self, historical_sessions: List[Dict]) -> float:
        """Calculate total focus duration for this week."""
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        weekly_focus = 0.0
        
        for session in historical_sessions:
            try:
                session_date = datetime.fromisoformat(session.get("session_start", ""))
                if session_date >= week_start:
                    focus_ratio = session.get("focused_frames", 0) / max(session.get("total_frames", 1), 1)
                    session_duration = session.get("session_duration_seconds", 0)
                    weekly_focus += (focus_ratio * session_duration) / 3600  # Convert to hours
            except (ValueError, TypeError):
                continue
        
        return round(weekly_focus, 2)
    
    def _calculate_average_session_duration(self, historical_sessions: List[Dict]) -> float:
        """Calculate average session duration in hours."""
        if not historical_sessions:
            return 0.0
        
        total_duration = 0.0
        for session in historical_sessions:
            focus_ratio = session.get("focused_frames", 0) / max(session.get("total_frames", 1), 1)
            session_duration = session.get("session_duration_seconds", 0)
            total_duration += (focus_ratio * session_duration) / 3600  # Convert to hours
        
        return round(total_duration / len(historical_sessions), 2)
    
    def _count_interruptions(self, focus_buffer: List[str], session_duration: float, total_frames: int) -> int:
        """Count significant interruptions using config parameters."""
        if not focus_buffer or total_frames == 0:
            return 0
        
        interruptions = 0
        in_distraction = False
        distraction_frames = 0
        frames_per_minute = total_frames / max(session_duration / 60, 1)  # Frames per minute
        min_interruption_frames = frames_per_minute * (config.MINIMUM_INTERUPTION_DURATION_SECONDS / 60)
        
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
    
    def _analyze_distraction_patterns(self, focus_buffer: List[str]) -> Dict:
        """Analyze patterns in distractions."""
        if not focus_buffer:
            return {}
        
        total_states = len(focus_buffer)
        distracted_count = sum(1 for state in focus_buffer if state == "DISTRACTED")
        away_count = sum(1 for state in focus_buffer if state == "AWAY")
        
        # Find most common distraction transitions
        transitions = []
        for i in range(len(focus_buffer) - 1):
            if focus_buffer[i] != "FOCUSED" and focus_buffer[i + 1] == "FOCUSED":
                transitions.append(focus_buffer[i])
        
        distraction_types = defaultdict(int)
        for transition in transitions:
            distraction_types[transition] += 1
        
        return {
            "distraction_percentage": round((distracted_count / max(total_states, 1)) * 100, 2),
            "away_percentage": round((away_count / max(total_states, 1)) * 100, 2),
            "common_distraction_types": dict(distraction_types),
            "total_transitions": len(transitions)
        }
    
    def _analyze_recovery_times(self, focus_buffer: List[str], session_duration: float, total_frames: int) -> Dict:
        """Analyze recovery times after distractions."""
        if not focus_buffer or total_frames == 0:
            return {}
        
        recovery_times = []
        in_distraction = False
        distraction_start = 0
        frames_per_second = total_frames / max(session_duration, 1)
        
        for i, state in enumerate(focus_buffer):
            if state == "DISTRACTED" and not in_distraction:
                in_distraction = True
                distraction_start = i
            elif state == "FOCUSED" and in_distraction:
                recovery_frames = i - distraction_start
                recovery_seconds = recovery_frames / frames_per_second
                recovery_times.append(recovery_seconds)
                in_distraction = False
        
        if not recovery_times:
            return {"average_recovery_time_seconds": 0, "recovery_events": 0}
        
        return {
            "average_recovery_time_seconds": round(sum(recovery_times) / len(recovery_times), 2),
            "fastest_recovery_time_seconds": round(min(recovery_times), 2),
            "slowest_recovery_time_seconds": round(max(recovery_times), 2),
            "recovery_events": len(recovery_times)
        }
    
    def _generate_focus_heatmap(self, historical_sessions: List[Dict]) -> List[Dict]:
        """Generate focus heatmap data by hour and day."""
        heatmap_data = []
        
        # Initialize 24x7 grid (hours x days)
        for day in range(7):  # 0=Monday, 6=Sunday
            for hour in range(24):
                heatmap_data.append({
                    "day_of_week": day,
                    "hour": hour,
                    "focus_score": 0,
                    "session_count": 0
                })
        
        # Populate with session data
        for session in historical_sessions:
            try:
                start_time = datetime.fromisoformat(session.get("session_start", ""))
                focus_score = session.get("focus_score", 0)
                
                day_idx = start_time.weekday()
                hour_idx = start_time.hour
                
                # Find corresponding heatmap entry
                for entry in heatmap_data:
                    if entry["day_of_week"] == day_idx and entry["hour"] == hour_idx:
                        entry["focus_score"] = (entry["focus_score"] * entry["session_count"] + focus_score) / (entry["session_count"] + 1)
                        entry["session_count"] += 1
                        break
            except (ValueError, TypeError):
                continue
        
        return heatmap_data
    
    def _identify_peak_performance_times(self, historical_sessions: List[Dict]) -> List[Dict]:
        """Identify peak performance times."""
        if not historical_sessions:
            return []
        
        # Group sessions by hour of day
        hourly_performance = defaultdict(list)
        
        for session in historical_sessions:
            try:
                start_time = datetime.fromisoformat(session.get("session_start", ""))
                hour = start_time.hour
                focus_score = session.get("focus_score", 0)
                hourly_performance[hour].append(focus_score)
            except (ValueError, TypeError):
                continue
        
        # Calculate average performance by hour
        peak_times = []
        for hour, scores in hourly_performance.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                peak_times.append({
                    "hour": hour,
                    "average_focus_score": round(avg_score, 2),
                    "session_count": len(scores),
                    "performance_level": self._classify_performance_level(avg_score)
                })
        
        # Sort by performance
        peak_times.sort(key=lambda x: x["average_focus_score"], reverse=True)
        
        return peak_times[:3]  # Top 3 peak times
    
    def _classify_performance_level(self, score: float) -> str:
        """Classify performance level based on focus score."""
        if score >= 85:
            return "PEAK"
        elif score >= 70:
            return "HIGH"
        elif score >= 50:
            return "MODERATE"
        else:
            return "LOW"
    
    def _analyze_rhythmic_patterns(self, historical_sessions: List[Dict]) -> Dict:
        """Analyze rhythmic patterns in focus performance."""
        if len(historical_sessions) < 5:  # Need sufficient data
            return {"insufficient_data": True}
        
        # Analyze by day of week
        daily_patterns = defaultdict(list)
        weekly_trends = []
        
        for session in historical_sessions:
            try:
                start_time = datetime.fromisoformat(session.get("session_start", ""))
                day_name = start_time.strftime("%A")
                focus_score = session.get("focus_score", 0)
                daily_patterns[day_name].append(focus_score)
                weekly_trends.append((start_time, focus_score))
            except (ValueError, TypeError):
                continue
        
        # Calculate daily averages
        daily_averages = {}
        for day, scores in daily_patterns.items():
            if scores:
                daily_averages[day] = round(sum(scores) / len(scores), 2)
        
        # Find best and worst days
        if daily_averages:
            best_day = max(daily_averages, key=daily_averages.get)
            worst_day = min(daily_averages, key=daily_averages.get)
        else:
            best_day = worst_day = None
        
        return {
            "daily_averages": daily_averages,
            "best_performance_day": best_day,
            "worst_performance_day": worst_day,
            "pattern_consistency": round(self._calculate_pattern_consistency(daily_averages), 2) if daily_averages else 0
        }
    
    def _calculate_pattern_consistency(self, daily_averages: Dict) -> float:
        """Calculate consistency of daily patterns."""
        if len(daily_averages) < 2:
            return 0.0
        
        values = list(daily_averages.values())
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        # Lower variance = higher consistency (scale 0-100)
        consistency = max(0, 100 - (variance / 100))
        return consistency
    
    def _calculate_focus_streaks(self, historical_sessions: List[Dict]) -> Dict:
        """Calculate focus streaks (consecutive days with sessions)."""
        if not historical_sessions:
            return {"current_streak": 0, "longest_streak": 0, "streak_history": []}
        
        # Group sessions by date
        session_dates = set()
        for session in historical_sessions:
            try:
                session_date = datetime.fromisoformat(session.get("session_start", "")).date()
                session_dates.add(session_date)
            except (ValueError, TypeError):
                continue
        
        if not session_dates:
            return {"current_streak": 0, "longest_streak": 0, "streak_history": []}
        
        # Sort dates and calculate streaks
        sorted_dates = sorted(session_dates)
        current_streak = 0
        longest_streak = 0
        temp_streak = 0
        
        today = datetime.now().date()
        
        for i, date in enumerate(sorted_dates):
            if i == 0 or (date - sorted_dates[i-1]).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
                
                # Check if this is part of current streak
                if (today - date).days < temp_streak:
                    current_streak = temp_streak
            else:
                temp_streak = 1
        
        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_active_days": len(session_dates),
            "recent_session_dates": sorted_dates[-10:]  # Last 10 session dates
        }
    
    def _calculate_peer_comparison(self, user_id: str, historical_sessions: List[Dict], all_users_data: List[Dict]) -> Dict:
        """Calculate peer comparison metrics."""
        if not all_users_data or not historical_sessions:
            return {"insufficient_data": True}
        
        # Calculate user metrics
        user_avg_focus = sum(s.get("focus_score", 0) for s in historical_sessions) / len(historical_sessions)
        user_total_sessions = len(historical_sessions)
        user_total_focus_hours = sum(
            (s.get("focused_frames", 0) / max(s.get("total_frames", 1), 1)) * s.get("session_duration_seconds", 0) / 3600
            for s in historical_sessions
        )
        
        # Calculate peer metrics
        peer_focus_scores = []
        peer_session_counts = []
        peer_focus_hours = []
        
        for user_data in all_users_data:
            if user_data.get("user_id") == user_id:
                continue  # Skip current user
            
            sessions = user_data.get("sessions", [])
            if sessions:
                peer_focus_scores.append(sum(s.get("focus_score", 0) for s in sessions) / len(sessions))
                peer_session_counts.append(len(sessions))
                peer_focus_hours.append(sum(
                    (s.get("focused_frames", 0) / max(s.get("total_frames", 1), 1)) * s.get("session_duration_seconds", 0) / 3600
                    for s in sessions
                ))
        
        if not peer_focus_scores:
            return {"insufficient_data": True}
        
        # Calculate percentiles
        focus_percentile = (sum(1 for score in peer_focus_scores if score < user_avg_focus) / len(peer_focus_scores)) * 100
        sessions_percentile = (sum(1 for count in peer_session_counts if count < user_total_sessions) / len(peer_session_counts)) * 100
        hours_percentile = (sum(1 for hours in peer_focus_hours if hours < user_total_focus_hours) / len(peer_focus_hours)) * 100
        
        return {
            "focus_score_percentile": round(focus_percentile, 1),
            "session_count_percentile": round(sessions_percentile, 1),
            "focus_hours_percentile": round(hours_percentile, 1),
            "comparison_summary": f"You focused more than {focus_percentile:.0f}% of users",
            "total_peers": len(peer_focus_scores)
        }
    
    def _track_achievements(self, historical_sessions: List[Dict]) -> List[Dict]:
        """Track user achievements with config-defined thresholds."""
        achievements = []
        
        if not historical_sessions:
            return achievements
        
        total_sessions = len(historical_sessions)
        total_focus_time = sum(
            (s.get("focused_frames", 0) / max(s.get("total_frames", 1), 1)) * s.get("session_duration_seconds", 0)
            for s in historical_sessions
        )
        
        # Session-based achievements using config thresholds
        thresholds = config.ACHIEVEMENT_THRESHOLDS
        if total_sessions >= thresholds["first_session"]:
            achievements.append({"id": "first_session", "name": "First Focus", "description": "Completed your first focus session"})
        if total_sessions >= thresholds["dedicated_focus"]:
            achievements.append({"id": "dedicated_focus", "name": "Dedicated Focus", "description": f"Completed {thresholds['dedicated_focus']} focus sessions"})
        if total_sessions >= thresholds["focus_master"]:
            achievements.append({"id": "focused_master", "name": "Focus Master", "description": f"Completed {thresholds['focus_master']} focus sessions"})
        if total_sessions >= thresholds.get("focus_legend", 500):
            achievements.append({"id": "focus_legend", "name": "Focus Legend", "description": f"Completed {thresholds['focus_legend']} focus sessions"})
        
        # Time-based achievements using config thresholds
        focus_hours = total_focus_time / 3600
        if focus_hours >= thresholds["hour_power"]:
            achievements.append({"id": "hour_power", "name": "Hour Power", "description": f"Accumulated {thresholds['hour_power']} hours of focused time"})
        if focus_hours >= thresholds["deep_work_expert"]:
            achievements.append({"id": "deep_work_expert", "name": "Deep Work Expert", "description": f"Accumulated {thresholds['deep_work_expert']} hours of focused time"})
        if focus_hours >= thresholds["century_club"]:
            achievements.append({"id": "century_club", "name": "Century Club", "description": f"Accumulated {thresholds['century_club']} hours of focused time"})
        if focus_hours >= thresholds.get("focus_marathon", 500):
            achievements.append({"id": "focus_marathon", "name": "Focus Marathon", "description": f"Accumulated {thresholds['focus_marathon']} hours of focused time"})
        
        # Performance-based achievements using config thresholds
        if total_sessions >= 5:  # Need multiple sessions for meaningful average
            avg_focus = sum(s.get("focus_score", 0) for s in historical_sessions) / total_sessions
            if avg_focus >= thresholds["high_performer"]:
                achievements.append({"id": "high_performer", "name": "High Performer", "description": f"Average focus score above {thresholds['high_performer']}%"})
            if avg_focus >= thresholds.get("elite_focus", 90):
                achievements.append({"id": "elite_focus", "name": "Elite Focus", "description": f"Average focus score above {thresholds['elite_focus']}%"})
        
        # Streak-based achievements
        if total_sessions >= 7:  # Need at least a week of potential streak
            # This would be calculated based on actual streak data
            pass
        
        return achievements
    
    def _calculate_retention_metrics(self, historical_sessions: List[Dict]) -> Dict:
        """Calculate user retention metrics."""
        if len(historical_sessions) < 2:
            return {"insufficient_data": True}
        
        # Calculate session frequency
        session_dates = []
        for session in historical_sessions:
            try:
                session_date = datetime.fromisoformat(session.get("session_start", "")).date()
                session_dates.append(session_date)
            except (ValueError, TypeError):
                continue
        
        if len(session_dates) < 2:
            return {"insufficient_data": True}
        
        session_dates.sort()
        
        # Calculate average days between sessions
        days_between = []
        for i in range(1, len(session_dates)):
            days_diff = (session_dates[i] - session_dates[i-1]).days
            days_between.append(days_diff)
        
        avg_days_between = sum(days_between) / len(days_between) if days_between else 0
        
        # Calculate retention rate (sessions in last 30 days vs total)
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        recent_sessions = sum(1 for date in session_dates if date >= thirty_days_ago)
        retention_rate = (recent_sessions / len(session_dates)) * 100
        
        return {
            "average_days_between_sessions": round(avg_days_between, 1),
            "retention_rate_30_days": round(retention_rate, 2),
            "total_active_days": len(set(session_dates)),
            "session_frequency_score": self._calculate_frequency_score(avg_days_between)
        }
    
    def _calculate_frequency_score(self, avg_days_between: float) -> str:
        """Calculate session frequency score."""
        if avg_days_between <= 1:
            return "DAILY"
        elif avg_days_between <= 3:
            return "FREQUENT"
        elif avg_days_between <= 7:
            return "WEEKLY"
        else:
            return "OCCASIONAL"
    
    def _generate_personalized_insights(self, report: Dict) -> List[str]:
        """Generate personalized insights based on analytics."""
        insights = []
        
        try:
            deep_work = report.get("deep_work_metrics", {})
            distraction = report.get("distraction_analytics", {})
            bio_trends = report.get("biological_trends", {})
            gamification = report.get("gamification_stats", {})
            
            # Deep work insights
            focus_efficiency = deep_work.get("focus_efficiency", 0)
            if focus_efficiency >= 80:
                insights.append("Excellent focus efficiency! You're maintaining deep work concentration.")
            elif focus_efficiency >= 60:
                insights.append("Good focus efficiency. Consider minimizing distractions to improve further.")
            else:
                insights.append("Your focus efficiency could improve. Try identifying and removing distractions.")
            
            # Distraction insights
            interruption_count = distraction.get("interruption_count", 0)
            if interruption_count > 5:
                insights.append(f"High interruption count ({interruption_count}). Consider blocking focus time.")
            elif interruption_count == 0:
                insights.append("Zero interruptions! Perfect deep work session.")
            
            # Context switching cost
            context_cost = distraction.get("context_switching_cost", {}).get("total_minutes", 0)
            if context_cost > 60:
                insights.append(f"High context switching cost ({context_cost:.0f} minutes). Batch similar tasks together.")
            
            # Streak insights
            current_streak = gamification.get("focus_streaks", {}).get("current_streak", 0)
            if current_streak >= 7:
                insights.append(f"Incredible {current_streak}-day focus streak! Keep the momentum going.")
            elif current_streak >= 3:
                insights.append(f"Nice {current_streak}-day focus streak. You're building a great habit.")
            
            # Peer comparison insights
            peer_comp = gamification.get("peer_comparison", {})
            if "focus_score_percentile" in peer_comp:
                percentile = peer_comp["focus_score_percentile"]
                if percentile >= 80:
                    insights.append(f"You're in the top {100-percentile:.0f}% of users for focus performance!")
                elif percentile >= 50:
                    insights.append("You're performing above average compared to other users.")
            
            # Peak time insights
            peak_times = bio_trends.get("peak_performance_times", [])
            if peak_times:
                best_hour = peak_times[0].get("hour", 0)
                insights.append(f"Your peak focus time is around {best_hour}:00. Schedule important tasks then.")
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            insights.append("Unable to generate personalized insights at this time.")
        
        return insights


# Global analytics service instance
analytics_service = AnalyticsService()
