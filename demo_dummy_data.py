#!/usr/bin/env python3
"""
Quick demonstration script to show the dummy data in action.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.models import User, UserSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

def demonstrate_dummy_data():
    """Demonstrate the dummy data created for the focus tracker."""
    
    print("🎯 Focus Tracker Dummy Data Demonstration")
    print("=" * 50)
    
    # Connect to database
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'focus_tracker.db')
    engine = create_engine(f'sqlite:///{db_path}')
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Show users
        users = db.query(User).all()
        print(f"\n👥 Demo Users ({len(users)}):")
        for user in users:
            print(f"   • {user.user_id} (Created: {user.created_at.strftime('%Y-%m-%d')})")
        
        # Show session summary
        sessions = db.query(UserSession).all()
        print(f"\n📊 Session Summary:")
        print(f"   • Total Sessions: {len(sessions)}")
        
        # Group sessions by user
        user_sessions = {}
        for session in sessions:
            if session.user_id not in user_sessions:
                user_sessions[session.user_id] = []
            user_sessions[session.user_id].append(session)
        
        for user_id, user_sess in user_sessions.items():
            avg_score = sum(s.focus_score for s in user_sess) / len(user_sess)
            total_hours = sum(s.duration_seconds for s in user_sess) / 3600
            print(f"   • {user_id}: {len(user_sess)} sessions, Avg: {avg_score:.1f}%, Total: {total_hours:.1f}h")
        
        # Show sample session with analytics
        sample_session = sessions[0]
        print(f"\n🔍 Sample Session Details:")
        print(f"   • Session ID: {sample_session.session_id}")
        print(f"   • User: {sample_session.user_id}")
        print(f"   • Duration: {sample_session.duration_seconds / 3600:.2f} hours")
        print(f"   • Focus Score: {sample_session.focus_score:.1f}%")
        print(f"   • Frames: {sample_session.total_frames} (Focused: {sample_session.focused_frames})")
        
        # Show comprehensive analytics
        if sample_session.raw_session_data:
            analytics = json.loads(sample_session.raw_session_data)
            print(f"\n📈 Comprehensive Analytics:")
            
            # Deep Work Metrics
            deep_work = analytics['deep_work_metrics']
            print(f"   🎯 Deep Work:")
            print(f"      • Focus Duration: {deep_work['focus_duration']['current_session_hours']:.2f}h")
            print(f"      • Focus Efficiency: {deep_work['focus_efficiency']:.1f}%")
            print(f"      • Focus-to-Rest Ratio: {deep_work['focus_to_rest_ratio']}:1")
            print(f"      • Focus Consistency: {deep_work.get('focus_consistency', 'N/A')}%")
            print(f"      • Productivity Score: {deep_work.get('productivity_score', 'N/A'):.1f}")
            
            # Distraction Analytics
            distraction = analytics['distraction_analytics']
            print(f"   🚫 Distraction Analytics:")
            print(f"      • Interruptions: {distraction['interruption_count']}")
            print(f"      • Context Switching Cost: {distraction['context_switching_cost']['total_minutes']:.0f}m")
            print(f"      • Distraction Frequency: {distraction['distraction_frequency']:.1f}%")
            print(f"      • Recovery Efficiency: {distraction['recovery_metrics'].get('recovery_efficiency', 'N/A')}%")
            
            # Biological Trends
            biological = analytics['biological_trends']
            print(f"   🌱 Biological Trends:")
            print(f"      • Pattern Consistency: {biological['rhythmic_insights']['pattern_consistency']:.1f}%")
            print(f"      • Circadian Alignment: {biological['rhythmic_insights'].get('circadian_alignment', 'N/A')}%")
            print(f"      • Focus Endurance: {biological['biological_markers']['focus_endurance']:.1f} hours")
            
            # Gamification Stats
            gamification = analytics['gamification_stats']
            print(f"   🎮 Gamification:")
            print(f"      • Current Streak: {gamification['focus_streaks']['current_streak']} days")
            print(f"      • Current Level: {gamification['level_progress']['current_level']}")
            print(f"      • Experience Points: {gamification['level_progress']['experience_points']}")
            print(f"      • Achievements: {len(gamification['achievements'])}")
            print(f"      • Peer Percentile: {gamification['peer_comparison']['focus_score_percentile']:.0f}%")
            
            # Performance Metrics
            performance = analytics['performance_metrics']
            print(f"   📈 Performance Metrics:")
            print(f"      • Productivity Index: {performance['productivity_index']:.1f}")
            print(f"      • Efficiency Score: {performance['efficiency_score']:.1f}")
            print(f"      • Quality Rating: {performance['quality_rating']:.1f}/10")
            print(f"      • Improvement Rate: {performance['improvement_rate']:+.1f}%")
            
            # Environmental Factors
            environmental = analytics['environmental_factors']
            print(f"   🏠 Environmental Factors:")
            print(f"      • Workspace Optimal: {'Yes' if environmental['workspace_optimal'] else 'No'}")
            print(f"      • Noise Level: {environmental['noise_level']}")
            print(f"      • Lighting: {environmental['lighting_conditions']}")
            print(f"      • Ergonomics Score: {environmental['ergonomics_score']:.1f}/10")
            
            # Recommendations
            print(f"   💡 Recommendations:")
            for i, rec in enumerate(analytics['recommendations'][:2], 1):
                print(f"      {i}. {rec['category']}: {rec['action']}")
                print(f"         Expected Impact: {rec['expected_impact']}")
            
            # Insights
            print(f"   🎯 Insights:")
            for insight in analytics['insights']:
                print(f"      • {insight}")
                
            # Session Metadata
            metadata = analytics['session_metadata']
            print(f"   📊 Session Quality: {metadata['session_quality']}")
            print(f"   📊 Data Completeness: {metadata['data_completeness']:.1f}%")
            print(f"   📊 Analysis Confidence: {metadata['analysis_confidence']:.2f}")
        
        print(f"\n✅ Database ready for testing!")
        print(f"   • Location: {db_path}")
        print(f"   • Size: {os.path.getsize(db_path) / 1024:.1f} KB")
        
        print(f"\n🚀 Quick Test Commands:")
        print(f"   1. Start server: python server.py")
        print(f"   2. Open browser: http://localhost:8002/examples/web_demo_client.html")
        print(f"   3. Use demo users: demo_user_001, demo_user_002, etc.")
        print(f"   4. Test API: curl http://localhost:8002/api/v1/focus/session/demo_user_001")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    demonstrate_dummy_data()
