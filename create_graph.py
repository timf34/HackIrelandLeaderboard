import pandas as pd
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from collections import defaultdict
import os
from dotenv import load_dotenv
import numpy as np

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
    end_time = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)  # Set end time to 13:00
    start_time = end_time - timedelta(hours=30)
    
    # Read repositories from CSV
    repos = read_repos_from_csv()
    
    # Dictionary to store commits per hour
    hourly_commits = defaultdict(int)
    
    # Fetch commits for each repository
    for repo_url in repos:
        owner, repo = extract_repo_info(repo_url)
        commits = get_commits(owner, repo, start_time)
        
        # Count commits per hour, but only up to 13:00
        for commit in commits:
            commit_time = datetime.strptime(commit['commit']['author']['date'], 
                                         '%Y-%m-%dT%H:%M:%SZ')
            if commit_time <= end_time:  # Only include commits up to 13:00
                hour_key = commit_time.replace(minute=0, second=0, microsecond=0)
                hourly_commits[hour_key] += 1
    
    # Create lists for plotting
    hours = sorted(hourly_commits.keys())
    commit_counts = [hourly_commits[hour] for hour in hours]
    
    # Format hours to show only HH:00
    hour_labels = [hour.strftime('%H:00') for hour in hours]
    
    # Set the style
    plt.style.use('dark_background')
    
    # Create figure with dark background
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111)
    background_color = '#13151a'  # Matching --background-color from style.css
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)
    
    # Plot with gradient line
    line = plt.plot(range(len(hours)), commit_counts, marker='o', linewidth=2.5)[0]
    
    # Create gradient effect for the line
    from matplotlib.patheffects import withStroke
    line.set_color('#883aea')
    line.set_markerfacecolor('#f951d2')
    line.set_markeredgecolor('#f951d2')
    line.set_path_effects([withStroke(linewidth=4, foreground=(0.53, 0.23, 0.92, 0.2))])
    
    # Customize the plot
    plt.title('Hourly Commit Activity', 
             color='white', 
             pad=20,
             fontsize=14,
             fontweight='bold')
    plt.xlabel('Hour', color='white')
    plt.ylabel('Number of Commits', color='white')
    
    # Customize grid
    plt.grid(True, color=(1, 1, 1, 0.05), linestyle='-', linewidth=1)
    
    # Set x-axis ticks and labels with white color and bold font
    plt.xticks(range(len(hours)), hour_labels, rotation=45, color='white', 
               fontsize=11, fontweight='bold')
    plt.yticks(color='white', fontsize=11, fontweight='bold')
    
    # Style the spines
    for spine in ax.spines.values():
        spine.set_color((1, 1, 1, 0.1))
    
    # Add subtle glow effect
    from matplotlib.colors import LinearSegmentedColormap
    z = [[0,0],[0,0]]
    levels = np.linspace(0, 0.5, 100)
    cmap = LinearSegmentedColormap.from_list('custom', [(0.53, 0.23, 0.92, 0), (0.53, 0.23, 0.92, 0.2)])
    ax.contourf(z, levels, cmap=cmap, origin='lower', extent=[0, len(hours)-1, min(commit_counts), max(commit_counts)])
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot with the new background color
    plt.savefig('commit_activity.png', 
                facecolor=background_color,
                edgecolor='none',
                bbox_inches='tight',
                dpi=300)
    print("Graph has been saved as 'commit_activity.png'")

if __name__ == "__main__":
    create_hourly_commit_graph()
