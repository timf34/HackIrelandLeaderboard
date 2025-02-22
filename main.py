import time
import sys
import os
from github_commit_tracker import GitHubTracker

# Get GitHub token from environment variable (optional but recommended)
github_token = os.environ.get("GITHUB_TOKEN")

def main():
    # Initialize the tracker
    tracker = GitHubTracker(github_token)
    
    # Add some example teams and repositories
    print("Setting up example teams and repositories...")
    
    # Team 1
    team1_id = tracker.add_team("Team Tim")
    tracker.add_repository(team1_id, "https://github.com/timf34/HackIrelandLeaderboard")
    
    
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