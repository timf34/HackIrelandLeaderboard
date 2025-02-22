"""
Configuration file for the Hack Ireland Leaderboard.
Loads team configurations from teams.csv and provides settings for the application.
"""

import csv
import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Path to the teams CSV file
TEAMS_CSV_PATH = 'teams.csv'

def load_team_configs():
    """Load and format team configurations for use with GitHubTracker."""
    teams = []
    try:
        with open(TEAMS_CSV_PATH, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Handle potential whitespace and formatting issues
                team_number = int(row['team_number'].strip())
                repo_url = row['repository_url'].strip()
                
                # Clean the URL (remove trailing slashes, etc)
                repo_url = repo_url.rstrip('/')
                
                teams.append({
                    "name": f"Team {team_number}",
                    "repos": [repo_url]
                })
        return teams
    except Exception as e:
        print(f"Error loading team configurations: {str(e)}")
        return []

# GitHub configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    raise ValueError("GitHub token not found in .env file. Please add GITHUB_TOKEN=your_token to .env")

# Web server configuration
WEB_CONFIG = {
    "host": "0.0.0.0",   # Listen on all interfaces
    "port": 5000,        # Port to run the web server on
    "debug": True,       # Enable debug mode (set to False in production)
}

# GitHub API configuration
GITHUB_CONFIG = {
    "polling_interval": 5,  # Time between checks (in seconds)
    "token": GITHUB_TOKEN,  # Add token to config for easier access
}

# Competition timing configuration
COMPETITION_CONFIG = {
    "start_time": "2024-03-20T09:00:00Z",
    "end_time": "2024-03-21T17:00:00Z"
}

def validate_github_url(url):
    """Validate if a GitHub URL is well-formed and accessible."""
    try:
        # Clean the URL first
        url = url.strip().rstrip('/')
        
        parsed = urlparse(url)
        if not parsed.netloc == 'github.com':
            return False, "Not a GitHub URL"
        
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            return False, "Invalid GitHub repository URL format"
            
        api_url = f"https://api.github.com/repos/{path_parts[0]}/{path_parts[1]}"
        
        headers = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            return True, "Repository exists and is accessible"
        elif response.status_code == 404:
            return False, "Repository not found"
        elif response.status_code == 403:
            return False, "Rate limit exceeded or access denied"
        else:
            return False, f"HTTP Error: {response.status_code}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Validate all team configurations."""
    print("\nValidating team configurations...")
    print("-" * 50)
    
    valid_teams = True
    teams = load_team_configs()
    
    if not teams:
        print("❌ No teams found or error loading team configurations")
        return
    
    for team in teams:
        team_name = team["name"]
        repo_url = team["repos"][0]
        print(f"\n{team_name}:")
        print(f"Repository: {repo_url}")
        
        # Validate URL
        is_valid, message = validate_github_url(repo_url)
        if is_valid:
            print("✅ Valid GitHub repository")
        else:
            valid_teams = False
            print(f"❌ Invalid repository: {message}")
    
    print("\n" + "-" * 50)
    if valid_teams:
        print("✅ All team configurations are valid!")
    else:
        print("❌ Some team configurations have errors. Please check the details above.")
    print("-" * 50 + "\n")

if __name__ == "__main__":
    main()