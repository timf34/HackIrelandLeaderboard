import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify
from github_commit_tracker import GitHubTracker
from dotenv import load_dotenv
from config import load_team_configs, WEB_CONFIG, GITHUB_CONFIG, GITHUB_TOKEN

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development

# Initialize tracker
tracker = GitHubTracker(GITHUB_TOKEN)

# Configure tracker with teams
def setup_tracker():
    teams = load_team_configs()
    print(f"Setting up tracker with {len(teams)} teams...")
    start_time = time.time()
    
    for team in teams:
        team_id = tracker.add_team(team["name"])
        for repo_url in team["repos"]:
            repo_id = tracker.add_repository(team_id, repo_url)
            print(f"Added repository {repo_url} for {team['name']}")
    
    duration = time.time() - start_time
    print(f"Setup completed in {duration:.2f} seconds")

# Routes
@app.route('/')
def index():
    print("Index route accessed!")
    return render_template('index.html')

@app.route('/api/leaderboard')
def get_leaderboard():
    leaderboard = tracker.get_leaderboard()
    
    # Make sure None values are converted to 0 for sorting
    for team in leaderboard:
        if team["total_commits"] is None:
            team["total_commits"] = 0
    
    # Sort and limit to top 15 teams
    sorted_leaderboard = sorted(leaderboard, key=lambda x: x["total_commits"], reverse=True)
    top_teams = sorted_leaderboard[:15]
    
    return jsonify(top_teams)

@app.route('/api/events')
def get_events():
    events = tracker.get_unprocessed_events()
    event_ids = [event['id'] for event in events]
    
    # Mark events as processed
    if event_ids:
        tracker.mark_events_processed(event_ids)
    
    return jsonify(events)

@app.route('/api/repositories')
def get_repositories():
    repos = tracker.get_all_repositories()
    return jsonify(repos)

@app.route('/api/stats')
def get_stats():
    """Return some statistics about the tracker."""
    from datetime import datetime
    
    repos = tracker.get_all_repositories()
    
    # Calculate stats
    stats = {
        "total_teams": len(set([repo["team_name"] for repo in repos])),
        "total_repos": len(repos),
        "total_commits": sum(repo["total_commits"] for repo in repos),
        "api_calls_remaining": tracker.remaining_api_calls,
        "api_reset_time": datetime.fromtimestamp(tracker.last_api_reset).strftime('%H:%M:%S') 
            if tracker.last_api_reset > 0 else "Unknown"
    }
    
    return jsonify(stats)

@app.route('/api/recent-activity')
def get_recent_activity():
    """Return recent activity history."""
    activity = tracker.get_recent_activity(limit=50)
    return jsonify(activity)

if __name__ == '__main__':
    # Setup tracker
    setup_tracker()
    
    # Start tracker in background
    tracker.start()
    
    try:
        # Run Flask app
        app.run(host="0.0.0.0", port=8000, debug=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Ensure tracker is stopped when the app exits
        tracker.stop()
        tracker.close()
        print("Application closed.")