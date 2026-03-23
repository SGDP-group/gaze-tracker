#!/usr/bin/env python3
"""
Demo script to test the enhanced web demo client with comprehensive analytics.
This script starts the server and provides instructions for testing.
"""

import subprocess
import time
import sys
import os

def start_server():
    """Start the focus tracking server."""
    print("🚀 Starting Focus Tracking Server...")
    
    # Change to the project directory
    os.chdir('/home/lahirud/gaze_tracker')
    
    try:
        # Start the server
        process = subprocess.Popen([
            sys.executable, 'server.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        print("✅ Server started successfully!")
        print("🌐 Server URL: http://localhost:8002")
        print()
        
        print("📋 Testing Instructions:")
        print("=" * 50)
        print("1. Open your web browser")
        print("2. Navigate to: http://localhost:8002/examples/web_demo_client.html")
        print("3. Test the comprehensive analytics:")
        print()
        print("   🎯 Basic Workflow:")
        print("   • Click 'Start Session'")
        print("   • Click 'Send Test Frame' (5-10 times)")
        print("   • Click 'End Session'")
        print("   • Analytics dashboard will appear automatically!")
        print()
        print("   📊 Analytics Features:")
        print("   • Deep Work Metrics (focus duration, efficiency, ratios)")
        print("   • Distraction Analytics (interruptions, context switching)")
        print("   • Biological Trends (peak times, heatmap)")
        print("   • Gamification Stats (streaks, achievements, peer comparison)")
        print("   • Personalized Insights")
        print()
        print("   🔧 Additional Controls:")
        print("   • 'Show Analytics' - Manually display current session analytics")
        print("   • 'Get Session Data' - View raw session data")
        print("   • 'Hide Analytics' - Close the analytics dashboard")
        print("   • 'Refresh Analytics' - Update with latest data")
        print()
        
        print("🎨 Visual Features:")
        print("=" * 30)
        print("• Color-coded analytics cards")
        print("• Progress bars for efficiency metrics")
        print("• Interactive heatmap visualization")
        print("• Achievement badges with tooltips")
        print("• Responsive grid layout")
        print("• Smooth animations and transitions")
        print()
        
        print("📈 What to Look For:")
        print("=" * 25)
        print("• Focus Efficiency: Should show realistic percentages (not 100%)")
        print("• Focus-to-Rest Ratio: Mathematical ratio of focus vs rest time")
        print("• Context Switching Cost: 23 minutes per interruption")
        print("• Inconsistency Penalties: Applied for frequent state changes")
        print("• Achievement Progress: Based on configurable thresholds")
        print("• Peer Comparison: Percentile rankings (if enough data)")
        print()
        
        print("⚙️ Configuration Notes:")
        print("=" * 30)
        print("• All analytics use configurable parameters from src/config.py")
        print("• Inconsistency penalties: Enabled by default")
        print("• Achievement thresholds: Progressive difficulty levels")
        print("• Realistic scoring: Capped at 99% maximum")
        print()
        
        print("🔍 Debug Information:")
        print("=" * 20)
        print("• Check browser console for any JavaScript errors")
        print("• API responses are logged in the 'API Responses' section")
        print("• Server logs show detailed processing information")
        print("• Network tab shows all API requests and responses")
        print()
        
        print("Press Ctrl+C to stop the server...")
        
        # Keep server running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping server...")
            process.terminate()
            process.wait()
            print("✅ Server stopped successfully!")
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🎯 Focus Analytics Web Client Demo")
    print("=" * 40)
    print()
    
    # Check if server.py exists
    if not os.path.exists('/home/lahirud/gaze_tracker/server.py'):
        print("❌ server.py not found. Please ensure you're in the correct directory.")
        sys.exit(1)
    
    # Start the server
    success = start_server()
    
    if success:
        print("\n🎉 Demo completed!")
        print("The enhanced web client now properly visualizes:")
        print("• All comprehensive analytics metrics")
        print("• Interactive charts and visualizations")
        print("• Real-time updates and responsive design")
        print("• Detailed explanations and tooltips")
    else:
        print("\n❌ Demo failed. Please check the error messages above.")
        sys.exit(1)
