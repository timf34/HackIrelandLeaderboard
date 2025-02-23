// Cache DOM elements
const leaderboardTable = document.getElementById('leaderboard-table');
const leaderboardBody = leaderboardTable.querySelector('tbody');
const eventsFeed = document.getElementById('events-feed');

// Polling intervals (in milliseconds)
const LEADERBOARD_POLL_INTERVAL = 5000;  // 5 seconds
const EVENTS_POLL_INTERVAL = 2000;       // 2 seconds

// GitHub repository and polling interval
const GITHUB_REPO = "timf34/HackIrelandLeaderboard";
const GITHUB_POLL_INTERVAL = 300000; // 5 minutes (300 seconds)

// Format number with commas for thousands
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Configure confetti
function fireConfetti() {
    const colors = ['#883aea', '#f951d2']; // Purple and pink colors from your theme
    const end = Date.now() + 1000; // Duration of the effect

    // Create a confetti burst
    (function frame() {
        confetti({
            particleCount: 2,
            angle: 60,
            spread: 55,
            origin: { x: 0 },
            colors: colors
        });
        confetti({
            particleCount: 2,
            angle: 120,
            spread: 55,
            origin: { x: 1 },
            colors: colors
        });

        if (Date.now() < end) {
            requestAnimationFrame(frame);
        }
    }());
}

// Format relative time (e.g., "2 minutes ago")
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) {
        return interval + " year" + (interval === 1 ? "" : "s") + " ago";
    }
    
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) {
        return interval + " month" + (interval === 1 ? "" : "s") + " ago";
    }
    
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) {
        return interval + " day" + (interval === 1 ? "" : "s") + " ago";
    }
    
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) {
        return interval + " hour" + (interval === 1 ? "" : "s") + " ago";
    }
    
    interval = Math.floor(seconds / 60);
    if (interval >= 1) {
        return interval + " minute" + (interval === 1 ? "" : "s") + " ago";
    }
    
    return "just now";
}

// Format time only (e.g., "12:34 PM")
function formatTimeOnly(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
    }).toUpperCase();
}

// Update the leaderboard table
function updateLeaderboard(data) {
    const oldPositions = {};
    
    // Store current positions
    Array.from(leaderboardBody.children).forEach(row => {
        const teamName = row.querySelector('.team-col')?.textContent;
        if (teamName) oldPositions[teamName] = true;
    });
    
    // Clear and update table
    while (leaderboardBody.firstChild) {
        leaderboardBody.removeChild(leaderboardBody.firstChild);
    }
    
    if (!data || data.length === 0) {
        const row = document.createElement('tr');
        row.className = 'loading';
        row.innerHTML = '<td colspan="3">No teams found. Add teams to get started!</td>';
        leaderboardBody.appendChild(row);
        return;
    }
    
    data.forEach((team, index) => {
        const row = document.createElement('tr');
        
        // Add special classes for top 3
        if (index === 0) row.className = 'top-1';
        else if (index === 1) row.className = 'top-2';
        else if (index === 2) row.className = 'top-3';
        
        // Add animation if position changed
        if (oldPositions[team.team_name]) {
            row.classList.add('scale-animation');
        }
        
        row.innerHTML = `
            <td class="rank-col"><span class="rank">${index + 1}</span></td>
            <td class="team-col">${team.team_name}</td>
            <td class="commits-col">${formatNumber(team.total_commits)}</td>
        `;
        
        leaderboardBody.appendChild(row);
    });
}

// Add a new event to the feed
function addEvent(event) {
    // Remove loading message if present
    const loadingEvent = eventsFeed.querySelector('.loading');
    if (loadingEvent) {
        eventsFeed.removeChild(loadingEvent);
    }
    
    // Create event element
    const eventElement = document.createElement('div');
    eventElement.className = 'event new';
    
    if (event.event_type === 'new_commits') {
        const data = event.data;
        const timeStr = formatTimeOnly(event.created_at);
        
        eventElement.innerHTML = `
            <div>
                <span class="team-name">${data.team_name}</span> made 
                <span class="commit-count">${data.new_commit_count} new commit${data.new_commit_count !== 1 ? 's' : ''}</span> 
                at ${timeStr}
            </div>
            <span class="timestamp" data-time="${event.created_at}">${formatRelativeTime(event.created_at)}</span>
        `;
        
        // Fire confetti for new commits!
        fireConfetti();
    } else {
        eventElement.innerHTML = `
            <div>Unknown event: ${event.event_type}</div>
            <span class="timestamp" data-time="${event.created_at}">${formatRelativeTime(event.created_at)}</span>
        `;
    }
    
    // Add event to the top of the feed
    eventsFeed.insertBefore(eventElement, eventsFeed.firstChild);
    
    // Limit number of events shown
    const maxEvents = 20;
    const events = eventsFeed.querySelectorAll('.event:not(.loading)');
    if (events.length > maxEvents) {
        eventsFeed.removeChild(events[events.length - 1]);
    }
    
    // Remove 'new' class after animation
    setTimeout(() => {
        eventElement.classList.remove('new');
    }, 2000);
}

// Add new function to format timestamps
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMinutes = Math.floor((now - date) / (1000 * 60));
    
    if (diffMinutes < 1) return 'just now';
    if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
    
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
    
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Update the event creation in fetchInitialActivity
async function fetchInitialActivity() {
    try {
        const response = await fetch('/api/recent-activity');
        if (!response.ok) throw new Error('Failed to fetch activity history');
        
        const activities = await response.json();
        
        // Clear any loading messages
        const loadingEvent = eventsFeed.querySelector('.loading');
        if (loadingEvent) {
            eventsFeed.removeChild(loadingEvent);
        }
        
        // Add each activity to the feed
        activities.forEach(activity => {
            const eventElement = document.createElement('div');
            eventElement.className = 'event';
            
            if (activity.event_type === 'new_commits') {
                const timeStr = formatTimeOnly(activity.local_timestamp);
                
                eventElement.innerHTML = `
                    <div>
                        <span class="team-name">${activity.team_name}</span> made 
                        <span class="commit-count">${activity.commit_count} new commit${activity.commit_count !== 1 ? 's' : ''}</span> 
                        at ${timeStr}
                    </div>
                    <span class="timestamp" title="${activity.local_timestamp}">
                        ${formatTimestamp(activity.local_timestamp)}
                    </span>
                `;
            }
            
            eventsFeed.appendChild(eventElement);
        });
        
    } catch (error) {
        console.error('Error fetching activity history:', error);
    }
}

// Add function to update timestamps periodically
function updateTimestamps() {
    const timestamps = document.querySelectorAll('.timestamp');
    timestamps.forEach(timestamp => {
        const originalTime = timestamp.getAttribute('title');
        timestamp.textContent = formatTimestamp(originalTime);
    });
}

// Fetch leaderboard data
async function fetchLeaderboard() {
    try {
        const response = await fetch('/api/leaderboard');
        if (!response.ok) throw new Error('Failed to fetch leaderboard data');
        
        const data = await response.json();
        updateLeaderboard(data);
    } catch (error) {
        console.error('Error fetching leaderboard:', error);
    }
}

// Fetch new events
async function fetchEvents() {
    try {
        const response = await fetch('/api/events');
        if (!response.ok) throw new Error('Failed to fetch events');
        
        const events = await response.json();
        
        // Add each new event to the feed
        events.forEach(event => {
            addEvent(event);
        });
    } catch (error) {
        console.error('Error fetching events:', error);
    }
}

// Add this function to fetch star count
async function updateStarCount() {
    try {
        const response = await fetch(`https://api.github.com/repos/${GITHUB_REPO}`);
        if (!response.ok) throw new Error('Failed to fetch GitHub data');
        
        const data = await response.json();
        const starCount = data.stargazers_count;
        
        // Force GitHub button to re-render with new count
        if (window.GitHubButton) {
            window.GitHubButton.render();
        }
    } catch (error) {
        console.error('Error fetching GitHub stars:', error);
    }
}

// Update the init function to include initial activity load
function init() {
    // Initial data load
    fetchLeaderboard();
    fetchInitialActivity();
    
    // Add GitHub star count polling
    updateStarCount();
    setInterval(updateStarCount, GITHUB_POLL_INTERVAL);
    
    // Set up polling for updates
    setInterval(fetchLeaderboard, LEADERBOARD_POLL_INTERVAL);
    setInterval(fetchEvents, EVENTS_POLL_INTERVAL);
    
    // Update timestamps every minute
    setInterval(updateTimestamps, 60000);
}

// Start the app when the DOM is ready
document.addEventListener('DOMContentLoaded', init);