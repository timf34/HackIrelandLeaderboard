import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify
from github_commit_tracker import GitHubTracker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development

# Get GitHub token from environment variable
github_token = os.environ.get("GITHUB_TOKEN")
if not github_token:
    print("WARNING: No GitHub API token provided. You may hit rate limits quickly.")
    print("To use a token, create a .env file with GITHUB_TOKEN=your_token")

# Initialize tracker
tracker = GitHubTracker(github_token)

# Configure tracker with teams
def setup_tracker():
    # Define your teams and repositories here
    # You can move this to a config file later
    teams = [
        {
            "name": "Team Alpha",
            "repos": ["https://github.com/timf34/HackIrelandLeaderboard"]
        },
        # Add more teams as needed
    ]
    
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

if __name__ == '__main__':
    # Setup tracker
    setup_tracker()
    
    # Start tracker in background
    tracker.start()
    
    try:
        # Run Flask app
        app.run(host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Ensure tracker is stopped when the app exits
        tracker.stop()
        tracker.close()
        print("Application closed.")