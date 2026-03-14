#!/usr/bin/env python3
"""
Script to populate focus_tracker.db with dummy data for testing and demonstration.
Creates sample users, sessions, and comprehensive analytics data.
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta
import random
import json

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.models import UserSession, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import config

def create_dummy_data():
    """Create comprehensive dummy data for the focus tracking system."""
    
    print("🗄️  Creating dummy data for focus_tracker.db...")
    
    # Database setup
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'focus_tracker.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    engine = create_engine(f'sqlite:///{db_path}')
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    from database.models import Base
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Create sample users
        users = create_sample_users(db)
        print(f"✅ Created {len(users)} sample users")
        
        # Create sample sessions for each user
        sessions = create_sample_sessions(db, users)
        print(f"✅ Created {len(sessions)} sample sessions")
        
        # Create comprehensive analytics data
        analytics_data = create_sample_analytics(sessions)
        print(f"✅ Created analytics data for {len(analytics_data)} sessions")
        
        # Update sessions with analytics data
        update_sessions_with_analytics(db, sessions, analytics_data)
        print("✅ Updated sessions with comprehensive analytics")
        
        # Print summary
        print("\n📊 Database Summary:")
        print(f"   • Total Users: {len(users)}")
        print(f"   • Total Sessions: {len(sessions)}")
        print(f"   • Database Location: {db_path}")
        print(f"   • Size: {os.path.getsize(db_path) / 1024:.1f} KB")
        
        print("\n🎯 Sample Data Created:")
        print("   • Users with different focus patterns")
        print("   • Sessions with realistic focus scores")
        print("   • Comprehensive analytics including:")
        print("     - Deep work metrics")
        print("     - Distraction analytics")
        print("     - Biological trends")
        print("     - Gamification stats")
        print("     - Personalized insights")
        
    except Exception as e:
        print(f"❌ Error creating dummy data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_sample_users(db):
    """Create sample users with different characteristics."""
    
    users_data = [
        {
            "user_id": "demo_user_001",
            "api_key": "demo_key_001",
            "created_at": datetime.now() - timedelta(days=30)
        },
        {
            "user_id": "demo_user_002", 
            "api_key": "demo_key_002",
            "created_at": datetime.now() - timedelta(days=25)
        },
        {
            "user_id": "demo_user_003",
            "api_key": "demo_key_003",
            "created_at": datetime.now() - timedelta(days=20)
        },
        {
            "user_id": "demo_user_004",
            "api_key": "demo_key_004",
            "created_at": datetime.now() - timedelta(days=15)
        },
        {
            "user_id": "demo_user_005",
            "api_key": "demo_key_005",
            "created_at": datetime.now() - timedelta(days=10)
        }
    ]
    
    users = []
    for user_data in users_data:
        # Check if user already exists
        existing_user = db.query(User).filter(User.user_id == user_data["user_id"]).first()
        if existing_user:
            users.append(existing_user)
            continue
            
        user = User(**user_data)
        db.add(user)
        users.append(user)
    
    db.commit()
    return users

def create_sample_sessions(db, users):
    """Create sample sessions with realistic focus patterns."""
    
    sessions = []
    session_id_counter = 1
    
    for user in users:
        # Each user has different session patterns
        num_sessions = random.randint(5, 15)
        
        for i in range(num_sessions):
            # Generate session date within last 30 days
            days_ago = random.randint(0, 29)
            session_start = datetime.now() - timedelta(days=days_ago)
            
            # Random session duration (30 minutes to 3 hours)
            duration_minutes = random.randint(30, 180)
            session_end = session_start + timedelta(minutes=duration_minutes)
            duration_seconds = duration_minutes * 60
            
            # Generate realistic focus scores based on user characteristics
            base_focus_score = get_user_base_focus_score(user.user_id)
            focus_score = generate_realistic_focus_score(base_focus_score)
            
            # Calculate frame counts based on duration
            fps = 10  # 10 FPS
            total_frames = duration_seconds * fps
            focused_frames = int(total_frames * (focus_score / 100))
            distracted_frames = int(total_frames * random.uniform(0.05, 0.15))
            away_frames = total_frames - focused_frames - distracted_frames
            
            session = UserSession(
                session_id=f"session_{session_id_counter:06d}",
                user_id=user.user_id,
                start_time=session_start,
                end_time=session_end,
                duration_seconds=duration_seconds,
                total_frames=total_frames,
                focused_frames=focused_frames,
                distracted_frames=distracted_frames,
                away_frames=away_frames,
                focus_score=focus_score,
                baseline_angle=random.uniform(10, 25),
                angle_variance=random.uniform(5, 15),
                stability_score=random.uniform(0.6, 0.9),
                presence_ratio=random.uniform(0.8, 0.95),
                context_switches=random.randint(3, 12),
                base_prediction="FOCUSED" if focus_score > 70 else "DISTRACTED",
                base_confidence=random.uniform(0.7, 0.95),
                personalized_prediction="FOCUSED" if focus_score > 75 else "DISTRACTED",
                personalized_confidence=random.uniform(0.8, 0.98)
            )
            
            db.add(session)
            sessions.append(session)
            session_id_counter += 1
    
    db.commit()
    return sessions

def get_user_base_focus_score(user_id):
    """Get base focus score for different user types."""
    
    user_profiles = {
        "demo_user_001": 85,  # Alice - High performer
        "demo_user_002": 72,  # Bob - Average performer  
        "demo_user_003": 91,  # Carol - Excellent performer
        "demo_user_004": 68,  # David - Below average
        "demo_user_005": 78   # Emma - Good performer
    }
    
    return user_profiles.get(user_id, 75)

def get_session_type():
    """Get random session type for naming."""
    session_types = [
        "Morning Focus",
        "Deep Work", 
        "Afternoon Session",
        "Evening Study",
        "Project Work",
        "Reading Session",
        "Coding Session",
        "Research Work",
        "Creative Work",
        "Planning Session"
    ]
    
    return random.choice(session_types)

def generate_realistic_focus_score(base_score):
    """Generate realistic focus score with variation."""
    
    # Add some random variation
    variation = random.uniform(-5, 5)
    score = base_score + variation
    
    # Apply realistic constraints
    score = max(45, min(98, score))  # Between 45% and 98%
    
    # Add small decimal for realism
    score += random.uniform(0, 0.9)
    
    return round(score, 1)

def create_sample_analytics(sessions):
    """Create comprehensive analytics data for sessions."""
    
    analytics_data = {}
    
    for session in sessions:
        analytics = generate_comprehensive_analytics(session)
        analytics_data[session.session_id] = analytics
    
    return analytics_data

def generate_comprehensive_analytics(session):
    """Generate comprehensive analytics for a session."""
    
    duration_hours = session.duration_seconds / 3600
    
    # Deep Work Metrics
    deep_work_metrics = {
        "focus_duration": {
            "current_session_hours": round(duration_hours, 2),
            "daily_total_hours": round(duration_hours * random.uniform(1.5, 3.0), 2),
            "weekly_total_hours": round(duration_hours * random.uniform(8.0, 15.0), 2),
            "monthly_total_hours": round(duration_hours * random.uniform(25.0, 45.0), 2)
        },
        "focus_efficiency": session.focus_score,
        "focus_to_rest_ratio": round(session.focused_frames / max(session.distracted_frames + session.away_frames, 1), 1),
        "longest_focus_streak": {
            "minutes": round(random.uniform(5, 25), 1),
            "start_time": (session.start_time + timedelta(minutes=random.randint(5, 30))).isoformat(),
            "end_time": (session.start_time + timedelta(minutes=random.randint(40, 90))).isoformat(),
            "quality_score": round(random.uniform(7.5, 9.5), 1)  # 1-10 scale
        },
        "session_completion_rate": 95.0,  # Assuming high completion for demo data
        "focus_consistency": round(random.uniform(70, 95), 1),
        "productivity_score": round(session.focus_score * random.uniform(0.9, 1.1), 1)
    }
    
    # Enhanced Distraction Analytics
    interruption_count = random.randint(0, 8)
    distraction_analytics = {
        "interruption_count": interruption_count,
        "context_switching_cost": {
            "total_minutes": interruption_count * config.CONTEXT_SWITCH_RECOVERY_MINUTES,
            "interruption_count": interruption_count,
            "cost_per_interruption": config.CONTEXT_SWITCH_RECOVERY_MINUTES,
            "productivity_loss_percentage": round((interruption_count * config.CONTEXT_SWITCH_RECOVERY_MINUTES) / (duration_hours * 60) * 100, 1)
        },
        "distraction_frequency": round((session.distracted_frames / session.total_frames) * 100, 1),
        "distraction_patterns": {
            "distraction_percentage": round((session.distracted_frames / session.total_frames) * 100, 1),
            "away_percentage": round((session.away_frames / session.total_frames) * 100, 1),
            "common_distraction_types": {
                "DISTRACTED": session.distracted_frames,
                "AWAY": session.away_frames,
                "PHONE_CHECK": random.randint(0, 3),
                "NOTIFICATION": random.randint(0, 5),
                "ENVIRONMENTAL": random.randint(0, 2)
            },
            "total_transitions": session.context_switches,
            "average_distraction_duration": round(random.uniform(30, 180), 1),
            "peak_distraction_times": [f"{random.randint(9, 17)}:00", f"{random.randint(9, 17)}:30"]
        },
        "recovery_metrics": {
            "average_recovery_time_seconds": round(random.uniform(20, 90), 1),
            "recovery_events": interruption_count,
            "recovery_efficiency": round(random.uniform(60, 95), 1),
            "quick_recovery_rate": round(random.uniform(0.3, 0.8), 2)  # % of quick recoveries (<30s)
        },
        "distraction_sources": {
            "internal": round(random.uniform(20, 60), 1),  # % from internal factors
            "external": round(random.uniform(40, 80), 1),  # % from external factors
            "digital": round(random.uniform(30, 70), 1)   # % from digital distractions
        }
    }
    
    # Enhanced Biological Trends
    biological_trends = {
        "focus_heatmap": generate_focus_heatmap(),
        "peak_performance_times": generate_peak_performance_times(),
        "rhythmic_insights": {
            "best_performance_day": random.randint(0, 6),
            "pattern_consistency": round(random.uniform(65, 92), 1),
            "average_score": session.focus_score,
            "score_std_deviation": round(random.uniform(5, 12), 1),
            "circadian_alignment": round(random.uniform(70, 95), 1),  # How well aligned with natural rhythm
            "energy_patterns": {
                "morning_energy": round(random.uniform(60, 90), 1),
                "afternoon_energy": round(random.uniform(50, 85), 1),
                "evening_energy": round(random.uniform(40, 75), 1)
            }
        },
        "biological_markers": {
            "focus_endurance": round(random.uniform(6.5, 8.5), 1),  # Hours before fatigue
            "recovery_needs": round(random.uniform(15, 45), 1),  # Minutes needed between sessions
            "optimal_session_length": round(random.uniform(45, 120), 1),  # Ideal session duration
            "sleep_impact_score": round(random.uniform(75, 95), 1)  # How sleep affects focus
        },
        "weekly_patterns": {
            "monday_avg": round(session.focus_score + random.uniform(-10, 10), 1),
            "tuesday_avg": round(session.focus_score + random.uniform(-5, 5), 1),
            "wednesday_avg": round(session.focus_score + random.uniform(-8, 8), 1),
            "thursday_avg": round(session.focus_score + random.uniform(-5, 5), 1),
            "friday_avg": round(session.focus_score + random.uniform(-12, 2), 1),
            "weekend_avg": round(session.focus_score + random.uniform(-15, 5), 1)
        }
    }
    
    # Enhanced Gamification Stats
    gamification_stats = {
        "focus_streaks": generate_focus_streaks(session.user_id),
        "achievements": generate_achievements(session),
        "peer_comparison": generate_peer_comparison(session.focus_score),
        "level_progress": {
            "current_level": random.randint(1, 25),
            "experience_points": random.randint(100, 5000),
            "points_to_next_level": random.randint(50, 500),
            "total_sessions_needed": random.randint(1, 10),
            "focus_hours_needed": random.uniform(0.5, 5.0)
        },
        "challenges": {
            "active_challenges": [
                {
                    "name": "Focus Master",
                    "description": "Maintain >85% focus for 5 sessions",
                    "progress": round(random.uniform(0.2, 0.9), 2),
                    "reward_points": random.randint(50, 200)
                },
                {
                    "name": "Distraction Fighter",
                    "description": "Reduce interruptions by 50%",
                    "progress": round(random.uniform(0.1, 0.8), 2),
                    "reward_points": random.randint(30, 150)
                }
            ],
            "completed_challenges": random.randint(0, 15)
        },
        "social_features": {
            "team_ranking": random.randint(1, 50),
            "team_members": random.randint(3, 12),
            "shared_goals": random.randint(0, 5),
            "collaboration_score": round(random.uniform(60, 95), 1)
        }
    }
    
    # Enhanced Personalized Insights
    insights = generate_insights(session, deep_work_metrics, distraction_analytics, biological_trends)
    
    # Additional Analytics Categories
    performance_metrics = {
        "productivity_index": round(random.uniform(70, 95), 1),
        "efficiency_score": round(random.uniform(65, 90), 1),
        "quality_rating": round(random.uniform(7.0, 9.5), 1),
        "improvement_rate": round(random.uniform(-5, 15), 1),  # % change from previous
        "goal_completion": round(random.uniform(60, 95), 1)
    }
    
    environmental_factors = {
        "workspace_optimal": random.choice([True, False]),
        "noise_level": random.choice(["Quiet", "Moderate", "Noisy"]),
        "lighting_conditions": random.choice(["Good", "Fair", "Poor"]),
        "ergonomics_score": round(random.uniform(6.0, 9.0), 1),
        "interruption_sources": random.randint(0, 5)
    }
    
    recommendations = generate_recommendations(session, deep_work_metrics, distraction_analytics, biological_trends)
    
    return {
        "deep_work_metrics": deep_work_metrics,
        "distraction_analytics": distraction_analytics,
        "biological_trends": biological_trends,
        "gamification_stats": gamification_stats,
        "performance_metrics": performance_metrics,
        "environmental_factors": environmental_factors,
        "insights": insights,
        "recommendations": recommendations,
        "session_metadata": {
            "session_quality": random.choice(["Excellent", "Good", "Fair", "Poor"]),
            "data_completeness": round(random.uniform(85, 100), 1),
            "analysis_confidence": round(random.uniform(0.8, 0.98), 2),
            "generated_at": datetime.now().isoformat()
        }
    }

def generate_focus_heatmap():
    """Generate sample focus heatmap data."""
    
    heatmap = []
    for day in range(7):  # 0-6 (Monday to Sunday)
        for hour in range(24):  # 0-23
            # Higher probability of good focus during work hours (9-17)
            if 9 <= hour <= 17:
                base_score = random.uniform(75, 95)
            elif 18 <= hour <= 21:
                base_score = random.uniform(60, 80)
            else:
                base_score = random.uniform(40, 70)
            
            # Add some randomness
            score = base_score + random.uniform(-10, 10)
            score = max(20, min(98, score))
            
            # Random session count
            session_count = random.randint(0, 5) if 9 <= hour <= 17 else random.randint(0, 2)
            
            if session_count > 0:
                heatmap.append({
                    "day_of_week": day,
                    "hour": hour,
                    "focus_score": round(score, 1),
                    "session_count": session_count
                })
    
    return heatmap

def generate_peak_performance_times():
    """Generate sample peak performance times."""
    
    peak_times = []
    
    # Generate 3-5 peak hours
    for hour in random.sample(range(8, 19), random.randint(3, 5)):
        score = random.uniform(85, 96)
        
        if score >= 92:
            level = "PEAK"
        elif score >= 88:
            level = "HIGH"
        else:
            level = "NORMAL"
        
        peak_times.append({
            "hour": hour,
            "average_focus_score": round(score, 1),
            "session_count": random.randint(3, 8),
            "performance_level": level
        })
    
    return sorted(peak_times, key=lambda x: x["average_focus_score"], reverse=True)

def generate_focus_streaks(user_id):
    """Generate focus streak data for a user."""
    
    # Different streak patterns for different users
    user_streak_data = {
        "demo_user_001": {"current": 7, "longest": 15, "total": 45},
        "demo_user_002": {"current": 3, "longest": 8, "total": 28},
        "demo_user_003": {"current": 12, "longest": 22, "total": 67},
        "demo_user_004": {"current": 1, "longest": 4, "total": 15},
        "demo_user_005": {"current": 5, "longest": 11, "total": 38}
    }
    
    streak_data = user_streak_data.get(user_id, {"current": 2, "longest": 6, "total": 25})
    
    # Generate recent session dates
    recent_dates = []
    for i in range(streak_data["current"]):
        date = datetime.now() - timedelta(days=i)
        recent_dates.append(date.date().isoformat())
    
    return {
        "current_streak": streak_data["current"],
        "longest_streak": streak_data["longest"],
        "total_active_days": streak_data["total"],
        "recent_session_dates": recent_dates
    }

def generate_achievements(session):
    """Generate achievements based on session data."""
    
    achievements = []
    
    # Session-based achievements
    total_sessions = random.randint(5, 50)
    if total_sessions >= 1:
        achievements.append({
            "id": "first_session",
            "name": "First Focus",
            "description": "Completed your first focus session"
        })
    
    if total_sessions >= 10:
        achievements.append({
            "id": "dedicated_focus",
            "name": "Dedicated Focus", 
            "description": "Completed 10 focus sessions"
        })
    
    if total_sessions >= 25:
        achievements.append({
            "id": "focus_master",
            "name": "Focus Master",
            "description": "Completed 25 focus sessions"
        })
    
    # Time-based achievements
    total_hours = random.uniform(5, 100)
    if total_hours >= 1:
        achievements.append({
            "id": "hour_power",
            "name": "Hour Power",
            "description": "Accumulated 1 hour of focused time"
        })
    
    if total_hours >= 10:
        achievements.append({
            "id": "deep_work_expert",
            "name": "Deep Work Expert",
            "description": "Accumulated 10 hours of focused time"
        })
    
    # Performance-based achievements
    if session.focus_score >= 85:
        achievements.append({
            "id": "high_performer",
            "name": "High Performer",
            "description": "Achieved 85% focus score"
        })
    
    return achievements

def generate_peer_comparison(focus_score):
    """Generate peer comparison data."""
    
    # Generate realistic percentile rankings
    focus_percentile = min(95, max(5, int((focus_score / 100) * 100 + random.uniform(-15, 15))))
    session_percentile = min(90, max(10, int(random.uniform(40, 80))))
    hours_percentile = min(92, max(8, int(random.uniform(30, 85))))
    
    return {
        "focus_score_percentile": focus_percentile,
        "session_count_percentile": session_percentile,
        "focus_hours_percentile": hours_percentile,
        "comparison_summary": f"You focused more than {focus_percentile}% of users",
        "total_peers": random.randint(100, 500)
    }

def generate_insights(session, deep_work_metrics, distraction_analytics, biological_trends):
    """Generate personalized insights based on session data."""
    
    insights = []
    
    # Focus efficiency insights
    if session.focus_score >= 85:
        insights.append("Excellent focus performance! You're in the top tier of productivity.")
    elif session.focus_score >= 70:
        insights.append("Good focus session with room for improvement in consistency.")
    else:
        insights.append("Consider minimizing distractions to improve your focus score.")
    
    # Distraction insights
    if distraction_analytics["interruption_count"] > 5:
        insights.append(f"High interruption count ({distraction_analytics['interruption_count']}) - consider blocking notifications.")
    elif distraction_analytics["interruption_count"] == 0:
        insights.append("Perfect session with zero interruptions - keep up the great work!")
    
    # Context switching insights
    context_cost = distraction_analytics["context_switching_cost"]["total_minutes"]
    if context_cost > 60:
        insights.append(f"Context switching cost you {context_cost:.0f} minutes - try batching similar tasks.")
    
    # Time-based insights
    session_hour = session.start_time.hour
    if 9 <= session_hour <= 11:
        insights.append("Morning session timing is optimal for most people's focus patterns.")
    elif 14 <= session_hour <= 16:
        insights.append("Afternoon timing shows good consistency - maintain this schedule.")
    
    # Biological insights
    if biological_trends["rhythmic_insights"]["pattern_consistency"] >= 85:
        insights.append("High pattern consistency indicates strong focus discipline.")
    
    # Productivity insights
    if deep_work_metrics["focus_consistency"] >= 80:
        insights.append("Consistent focus throughout the session - excellent deep work!")
    
    return insights[:3]  # Return top 3 insights

def generate_recommendations(session, deep_work_metrics, distraction_analytics, biological_trends):
    """Generate actionable recommendations based on analytics."""
    
    recommendations = []
    
    # Focus improvement recommendations
    if session.focus_score < 75:
        recommendations.append({
            "category": "Focus Improvement",
            "priority": "High",
            "action": "Try the Pomodoro Technique: 25-minute focused sessions with 5-minute breaks",
            "expected_impact": "+15-20% focus score"
        })
    
    # Distraction management recommendations
    if distraction_analytics["interruption_count"] > 3:
        recommendations.append({
            "category": "Distraction Management",
            "priority": "High", 
            "action": "Use website blockers and turn off notifications during focus sessions",
            "expected_impact": "Reduce interruptions by 60-80%"
        })
    
    # Biological rhythm recommendations
    if biological_trends["rhythmic_insights"]["circadian_alignment"] < 80:
        recommendations.append({
            "category": "Biological Optimization",
            "priority": "Medium",
            "action": "Schedule your most important tasks during your peak energy hours",
            "expected_impact": "+10-15% overall productivity"
        })
    
    # Environment recommendations
    recommendations.append({
        "category": "Environment Setup",
        "priority": "Low",
        "action": "Optimize your workspace with proper lighting and minimal distractions",
        "expected_impact": "+5-10% focus consistency"
    })
    
    return recommendations[:4]  # Return top 4 recommendations

def update_sessions_with_analytics(db, sessions, analytics_data):
    """Update sessions with comprehensive analytics data."""
    
    for session in sessions:
        if session.session_id in analytics_data:
            session.raw_session_data = json.dumps(analytics_data[session.session_id])
    
    db.commit()

def verify_data():
    """Verify the dummy data was created correctly."""
    
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'focus_tracker.db')
    
    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return False
    
    engine = create_engine(f'sqlite:///{db_path}')
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check users
        user_count = db.query(User).count()
        session_count = db.query(UserSession).count()
        
        print(f"\n✅ Data Verification:")
        print(f"   • Users in database: {user_count}")
        print(f"   • Sessions in database: {session_count}")
        
        # Show sample session with analytics
        sample_session = db.query(UserSession).first()
        if sample_session and sample_session.raw_session_data:
            analytics = json.loads(sample_session.raw_session_data)
            print(f"   • Sample session analytics keys: {list(analytics.keys())}")
            
            # Show sample insights
            if 'insights' in analytics:
                print(f"   • Sample insights: {analytics['insights'][:2]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying data: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🎯 Focus Tracker Dummy Data Generator")
    print("=" * 50)
    
    try:
        create_dummy_data()
        
        if verify_data():
            print("\n🎉 Dummy data created successfully!")
            print("\n📝 Next Steps:")
            print("1. Start the server: python server.py")
            print("2. Open web client: http://localhost:8002/examples/web_demo_client.html")
            print("3. Test with demo users: demo_user_001, demo_user_002, etc.")
            print("4. View comprehensive analytics in the dashboard")
        else:
            print("\n❌ Data verification failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Failed to create dummy data: {e}")
        sys.exit(1)
