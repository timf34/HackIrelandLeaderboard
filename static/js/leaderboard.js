// Cache DOM elements
const leaderboardTable = document.getElementById('leaderboard-table');
const leaderboardBody = leaderboardTable.querySelector('tbody');
const eventsFeed = document.getElementById('events-feed');

// Polling intervals (in milliseconds)
const LEADERBOARD_POLL_INTERVAL = 5000;  // 5 seconds
const EVENTS_POLL_INTERVAL = 2000;       // 2 seconds

// Format number with commas for thousands
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
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

// Update the leaderboard table
function updateLeaderboard(data) {
    // Clear existing rows except for loading message
    while (leaderboardBody.firstChild) {
        leaderboardBody.removeChild(leaderboardBody.firstChild);
    }
    
    // If no data, show message
    if (!data || data.length === 0) {
        const row = document.createElement('tr');
        row.className = 'loading';
        row.innerHTML = '<td colspan="3">No teams found. Add teams to get started!</td>';
        leaderboardBody.appendChild(row);
        return;
    }
    
    // Add team rows
    data.forEach((team, index) => {
        const row = document.createElement('tr');
        
        // Add special classes for top 3
        if (index === 0) row.className = 'top-1';
        else if (index === 1) row.className = 'top-2';
        else if (index === 2) row.className = 'top-3';
        
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
        const timestamp = new Date(event.created_at).toLocaleString();
        
        eventElement.innerHTML = `
            <div>
                <span class="team-name">${data.team_name}</span> made 
                <span class="commit-count">${data.new_commit_count} new commit${data.new_commit_count !== 1 ? 's' : ''}</span> 
                on ${data.repo_name}
            </div>
            <span class="timestamp" data-time="${event.created_at}">${formatRelativeTime(event.created_at)}</span>
        `;
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

// Update relative timestamps
function updateTimestamps() {
    const timestamps = document.querySelectorAll('.timestamp[data-time]');
    timestamps.forEach(element => {
        const time = element.getAttribute('data-time');
        element.textContent = formatRelativeTime(time);
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

// Initialize the app
function init() {
    // Initial data load
    fetchLeaderboard();
    fetchEvents();
    
    // Set up polling for updates
    setInterval(fetchLeaderboard, LEADERBOARD_POLL_INTERVAL);
    setInterval(fetchEvents, EVENTS_POLL_INTERVAL);
    
    // Update relative timestamps every minute
    setInterval(updateTimestamps, 60000);
}

// Start the app when the DOM is ready
document.addEventListener('DOMContentLoaded', init);