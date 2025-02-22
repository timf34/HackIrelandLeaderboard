import time
import sys
import os
import argparse
from github_commit_tracker import GitHubTracker

# Parse command line arguments
parser = argparse.ArgumentParser(description='GitHub Hackathon Tracker')
parser.add_argument('--token', type=str, help='GitHub API token')
args = parser.parse_args()

# Get GitHub token with priority: command line arg > environment variable
# github_token = args.token if args.token else os.environ.get("GITHUB_TOKEN")
github_token = ""

if not github_token:
    print("WARNING: No GitHub API token provided. You may hit rate limits quickly.")
    print("To use a token, either:")
    print("  1. Set the GITHUB_TOKEN environment variable, or")
    print("  2. Pass the token with --token parameter")
    print("Continuing without a token...")
else:
    print("Using provided GitHub API token")

def main():
    # Initialize the tracker
    tracker = GitHubTracker(github_token)
    
    # Add some example teams and repositories
    print("Setting up example teams and repositories...")
    
    # Add your own repositories here
    # For example:
    team1_id = tracker.add_team("Team Tim")
    tracker.add_repository(team1_id, "https://github.com/timf34/HackIrelandLeaderboard")
    
    # Add more teams as needed
    # team2_id = tracker.add_team("Team Beta")
    # tracker.add_repository(team2_id, "https://github.com/teamname/repo-name")
    
    # Start the tracker
    print("Starting tracker...")
    tracker.start()
    
    try:
        # Run for a while, printing updates
        print("Tracker running. Press Ctrl+C to stop.")
        while True:
            # Wait for new commits event or timeout after 10 seconds
            tracker.new_commits_event.wait(timeout=10)
            
            # Clear the event
            tracker.new_commits_event.clear()
            
            # Get current leaderboard
            leaderboard = tracker.get_leaderboard()
            
            # Print leaderboard
            print("\nCurrent Leaderboard:")
            print("------------------------")
            for i, entry in enumerate(leaderboard, 1):
                print(f"{i}. {entry['team_name']}: {entry['total_commits']} commits")
            
            # Get unprocessed events
            events = tracker.get_unprocessed_events()
            event_ids = [event['id'] for event in events]
            
            if events:
                print("\nNew Commits Detected:")
                print("------------------------")
                for event in events:
                    if event['event_type'] == 'new_commits':
                        data = event['data']
                        print(f"🎉 {data['team_name']} made {data['new_commit_count']} new commits on {data['repo_name']}!")
                
                # Mark events as processed
                tracker.mark_events_processed(event_ids)
            
    except KeyboardInterrupt:
        print("\nStopping tracker...")
    finally:
        tracker.stop()
        tracker.close()
        print("Tracker stopped.")

if __name__ == "__main__":
    main()