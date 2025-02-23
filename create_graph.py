import pandas as pd
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from collections import defaultdict
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# GitHub API configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

def read_repos_from_csv():
    """Read repository list from CSV file."""
    df = pd.read_csv('teams.csv')
    # Remove duplicates and clean whitespace from URLs
    repos = df['repository_url'].str.strip().unique().tolist()
    # Remove any .git suffixes from the URLs
    repos = [repo.rstrip('.git') for repo in repos]
    return repos

def extract_repo_info(repo_url):
    """Extract owner and repo name from GitHub URL."""
    parts = repo_url.rstrip('/').split('/')
    return parts[-2], parts[-1]

def get_commits(owner, repo, since_time):
    """Fetch commits for a repository since the given time."""
    url = f'https://api.github.com/repos/{owner}/{repo}/commits'
    params = {'since': since_time.isoformat()}
    
    commits = []
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        commits = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching commits for {owner}/{repo}: {e}")
    
    return commits

def create_hourly_commit_graph():
    # Get current time and time 30 hours ago
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=30)
    
    # Read repositories from CSV
    repos = read_repos_from_csv()
    
    # Dictionary to store commits per hour
    hourly_commits = defaultdict(int)
    
    # Fetch commits for each repository
    for repo_url in repos:
        owner, repo = extract_repo_info(repo_url)
        commits = get_commits(owner, repo, start_time)
        
        # Count commits per hour
        for commit in commits:
            commit_time = datetime.strptime(commit['commit']['author']['date'], 
                                         '%Y-%m-%dT%H:%M:%SZ')
            hour_key = commit_time.replace(minute=0, second=0, microsecond=0)
            hourly_commits[hour_key] += 1
    
    # Create lists for plotting
    hours = sorted(hourly_commits.keys())
    commit_counts = [hourly_commits[hour] for hour in hours]
    
    # Format hours to show only HH:00
    hour_labels = [hour.strftime('%H:00') for hour in hours]
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(hours)), commit_counts, marker='o')
    
    # Customize the plot
    plt.title('Hourly Commit Activity Across All Repositories')
    plt.xlabel('Hour')
    plt.ylabel('Number of Commits')
    plt.grid(True)
    
    # Set x-axis ticks and labels
    plt.xticks(range(len(hours)), hour_labels, rotation=45)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('commit_activity.png')
    print("Graph has been saved as 'commit_activity.png'")

if __name__ == "__main__":
    create_hourly_commit_graph()
