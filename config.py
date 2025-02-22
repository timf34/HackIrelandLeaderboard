"""
Configuration file for the Hack Ireland Leaderboard.
Add your teams and their repositories here.
"""

# List of teams and their repositories
TEAMS = [
    {
        "name": "Team Tim",
        "repos": [
            "https://github.com/timf34/HackIrelandLeaderboard"
        ]
    }
]

# Web server configuration
WEB_CONFIG = {
    "host": "0.0.0.0",   # Listen on all interfaces
    "port": 5000,        # Port to run the web server on
    "debug": True,       # Enable debug mode (set to False in production)
}

# GitHub API configuration
GITHUB_CONFIG = {
    "polling_interval": 5,  # Time between checks (in seconds)
}