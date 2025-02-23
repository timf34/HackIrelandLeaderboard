import os
import time
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
import threading
import json
import requests
from bs4 import BeautifulSoup

import requests
from github import Github, GithubException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("github-tracker")

# Constants
POLLING_INTERVAL = 15  # seconds
DEFAULT_API_REQUEST_TIMEOUT = 10  # seconds
DB_PATH = "hackathon_tracker.db"

class GitHubTracker:
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the GitHub tracker with an optional GitHub token.
        Using a token increases rate limits for API calls.
        """
        self.github_token = github_token
        self.github = Github(github_token, retry=3) if github_token else Github(retry=3)
        self.db_conn = self._init_database()
        self.running = False
        self.teams_cache = {}  # Cache of team data
        self.repos_cache = {}  # Cache of repo data
        self.commit_counts = {}  # Current commit counts
        self.new_commits_event = threading.Event()  # Event for new commits
        self.last_api_reset = 0  # Track when API rate limit resets
        self.remaining_api_calls = 0  # Track remaining API calls
        
    def _init_database(self) -> sqlite3.Connection:
        """Initialize the SQLite database with required tables."""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        cursor = conn.cursor()
        
        # Create teams table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create repositories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                repo_url TEXT UNIQUE NOT NULL,
                repo_name TEXT NOT NULL,
                last_checked TIMESTAMP,
                total_commits INTEGER DEFAULT 0,
                FOREIGN KEY (team_id) REFERENCES teams (id)
            )
        ''')
        
        # Create commits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                commit_hash TEXT NOT NULL,
                author TEXT,
                message TEXT,
                timestamp TIMESTAMP,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repo_id) REFERENCES repositories (id)
            )
        ''')
        
        # Create events table for future web notifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                data TEXT,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        return conn
    
    def add_team(self, team_name: str) -> int:
        """Add a new team to the tracker and return its ID."""
        cursor = self.db_conn.cursor()
        try:
            cursor.execute("INSERT INTO teams (team_name) VALUES (?)", (team_name,))
            self.db_conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Team already exists, get its ID
            cursor.execute("SELECT id FROM teams WHERE team_name = ?", (team_name,))
            return cursor.fetchone()[0]
    
    def add_repository(self, team_id: int, repo_url: str) -> int:
        """Add a new repository to track for a team."""
        # Extract repo name from URL
        repo_name = repo_url.rstrip("/").split("/")[-1]
        
        cursor = self.db_conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO repositories (team_id, repo_url, repo_name) VALUES (?, ?, ?)",
                (team_id, repo_url, repo_name)
            )
            self.db_conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Repository already exists, get its ID
            cursor.execute("SELECT id FROM repositories WHERE repo_url = ?", (repo_url,))
            return cursor.fetchone()[0]
    
    def get_all_repositories(self) -> List[Dict]:
        """Get all repositories being tracked."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT r.id, r.repo_url, r.repo_name, r.total_commits, t.team_name, r.last_checked
            FROM repositories r
            JOIN teams t ON r.team_id = t.id
        """)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_repository_by_id(self, repo_id: int) -> Dict:
        """Get repository details by ID."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT r.id, r.repo_url, r.repo_name, r.total_commits, t.team_name, r.last_checked
            FROM repositories r
            JOIN teams t ON r.team_id = t.id
            WHERE r.id = ?
        """, (repo_id,))
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None
    
    def get_leaderboard(self) -> List[Dict]:
        """Get the current leaderboard data."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT t.team_name, SUM(r.total_commits) as total_commits
            FROM teams t
            LEFT JOIN repositories r ON t.id = r.team_id
            GROUP BY t.id
            ORDER BY total_commits DESC
        """)
        return [{"team_name": row[0], "total_commits": row[1]} for row in cursor.fetchall()]
    
    def _get_total_commits(self, repo_url: str) -> int:
        """Get total commits by scraping the GitHub page."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'
                
            response = requests.get(repo_url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to fetch page for {repo_url}: {response.status_code}")
                return 0
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find the commits count element
            commits_element = soup.select_one('span.fgColor-default')
            if commits_element:
                # Extract the number from text like "3 Commits"
                commits_text = commits_element.text.strip()
                commits_count = int(''.join(filter(str.isdigit, commits_text)))
                return commits_count
            
            logger.warning(f"Could not find commits count element for {repo_url}")
            return 0
            
        except Exception as e:
            logger.error(f"Error scraping commits for {repo_url}: {str(e)}")
            return 0
    
    def _parse_github_url(self, url: str) -> tuple:
        """Parse a GitHub URL into owner and repo name."""
        parts = url.rstrip("/").replace("https://github.com/", "").split("/")
        return parts[0], parts[1]
    
    def _check_rate_limit(self) -> bool:
        """
        Check if we're close to hitting rate limits.
        Returns True if it's safe to make API calls, False otherwise.
        """
        try:
            rate_limit = self.github.get_rate_limit()
            core = rate_limit.core
            
            self.remaining_api_calls = core.remaining
            self.last_api_reset = core.reset.timestamp()
            
            if core.remaining < 10:  # Keep a safety buffer
                reset_time = core.reset.strftime('%H:%M:%S')
                logger.warning(f"GitHub API rate limit almost exhausted. Resets at {reset_time}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error checking rate limits: {str(e)}")
            # Default to being cautious
            return False
    
    def _get_repo_commits(self, repo_url: str, since_timestamp=None) -> List[Dict]:
        """
        Get commits from a GitHub repository since the given timestamp.
        Returns a list of commit dictionaries.
        """
        # Check if we're close to rate limits
        if not self._check_rate_limit():
            # Use only cached data if we're close to hitting limits
            logger.warning(f"Skipping API request for {repo_url} due to rate limit concerns")
            return []
        
        try:
            owner, repo_name = self._parse_github_url(repo_url)
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            # Get commits
            kwargs = {}
            if since_timestamp:
                kwargs['since'] = since_timestamp
            
            commits = []
            # Limit to the last 10 commits to reduce API calls
            for commit in list(repo.get_commits(**kwargs))[:10]:
                commits.append({
                    'hash': commit.sha,
                    'author': commit.author.login if commit.author else 'Unknown',
                    'message': commit.commit.message,
                    'timestamp': commit.commit.author.date,
                })
            
            return commits
            
        except GithubException as e:
            if e.status == 403 and "rate limit exceeded" in str(e).lower():
                logger.error(f"Rate limit exceeded. If this continues, consider using a GitHub token.")
                # Calculate time until reset
                if self.last_api_reset > 0:
                    now = time.time()
                    wait_time = max(0, self.last_api_reset - now)
                    logger.info(f"Rate limit will reset in approximately {wait_time:.1f} seconds")
            else:
                logger.error(f"GitHub API error for {repo_url}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error fetching commits for {repo_url}: {str(e)}")
            return []
    
    def check_repository(self, repo_id: int) -> int:
        """
        Check a repository for new commits and update the database.
        Returns the number of new commits found.
        """
        repo = self.get_repository_by_id(repo_id)
        if not repo:
            logger.error(f"Repository with ID {repo_id} not found")
            return 0
        
        # Get current total commits
        current_total = self._get_total_commits(repo['repo_url'])
        
        if current_total == 0:
            # Error fetching commits, don't update anything
            return 0
        
        # Calculate new commits
        previous_total = repo['total_commits'] or 0
        new_commit_count = max(0, current_total - previous_total)
        
        if new_commit_count > 0:
            cursor = self.db_conn.cursor()
            
            # Update repository's total commits
            cursor.execute(
                "UPDATE repositories SET total_commits = ?, last_checked = ? WHERE id = ?",
                (current_total, datetime.now().isoformat(), repo_id)
            )
            
            # Create a new event
            cursor.execute(
                "INSERT INTO events (event_type, entity_id, data) VALUES (?, ?, ?)",
                (
                    "new_commits", 
                    repo_id, 
                    json.dumps({
                        "repo_id": repo_id,
                        "team_name": repo['team_name'],
                        "repo_name": repo['repo_name'],
                        "new_commit_count": new_commit_count,
                        "total_commits": current_total
                    })
                )
            )
            
            self.db_conn.commit()
            self.new_commits_event.set()
        
        return new_commit_count
    
    def run_polling_loop(self):
        """Run the main polling loop to check repositories."""
        self.running = True
        
        # Track repositories to implement staggered polling
        repos_last_checked = {}
        
        while self.running:
            try:
                # Get all repositories
                repos = self.get_all_repositories()
                current_time = time.time()
                
                # Check if we're approaching rate limits
                approaching_limit = self.remaining_api_calls < len(repos) * 2  # Buffer for safety
                
                # Process repositories in a staggered manner to avoid hitting rate limits
                for repo in repos:
                    repo_id = repo['id']
                    
                    # Initialize last checked time if not already set
                    if repo_id not in repos_last_checked:
                        repos_last_checked[repo_id] = 0
                    
                    # Determine if we should check this repository now
                    # If approaching rate limits, check less frequently
                    check_interval = POLLING_INTERVAL * 5 if approaching_limit else POLLING_INTERVAL
                    
                    if current_time - repos_last_checked[repo_id] >= check_interval:
                        new_commits = self.check_repository(repo_id)
                        repos_last_checked[repo_id] = current_time
                        
                        if new_commits > 0:
                            logger.info(f"Found {new_commits} new commits for {repo['repo_name']} ({repo['team_name']})")
                
                # Log rate limit status occasionally
                if self.remaining_api_calls < 100:
                    reset_time = datetime.fromtimestamp(self.last_api_reset).strftime('%H:%M:%S')
                    logger.info(f"GitHub API calls remaining: {self.remaining_api_calls}, resets at {reset_time}")
                
            except Exception as e:
                logger.error(f"Error in polling loop: {str(e)}")
            
            # Sleep before the next polling cycle
            time.sleep(1)  # Short sleep between cycles
    
    def start(self):
        """Start the tracker in a background thread."""
        threading.Thread(target=self.run_polling_loop, daemon=True).start()
        logger.info("GitHub tracker started")
    
    def stop(self):
        """Stop the tracker."""
        self.running = False
        logger.info("GitHub tracker stopped")
    
    def get_unprocessed_events(self) -> List[Dict]:
        """Get all unprocessed events for the web interface."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT id, event_type, entity_id, data, created_at
            FROM events
            WHERE processed = FALSE
            ORDER BY created_at ASC
        """)
        columns = [col[0] for col in cursor.description]
        events = []
        for row in cursor.fetchall():
            event = dict(zip(columns, row))
            event['data'] = json.loads(event['data'])
            events.append(event)
        return events
    
    def mark_events_processed(self, event_ids: List[int]):
        """Mark events as processed."""
        if not event_ids:
            return
        
        placeholders = ','.join(['?'] * len(event_ids))
        cursor = self.db_conn.cursor()
        cursor.execute(
            f"UPDATE events SET processed = TRUE WHERE id IN ({placeholders})",
            event_ids
        )
        self.db_conn.commit()

    def close(self):
        """Close the database connection."""
        if self.db_conn:
            self.db_conn.close()