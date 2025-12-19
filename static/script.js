// DOM Elements
const jobsTbody = document.getElementById('jobs-tbody');
const searchInput = document.getElementById('search-input');
const filterSite = document.getElementById('filter-site');
const btnFullScrape = document.getElementById('btn-full-scrape');
const statusBanner = document.getElementById('status-banner');
const statusMessage = document.getElementById('status-message');
const modal = document.getElementById('modal');
const modalClose = document.getElementById('modal-close');
const modalTitle = document.getElementById('modal-title');
const modalSite = document.getElementById('modal-site');
const modalScore = document.getElementById('modal-score');
const modalLink = document.getElementById('modal-link');
const modalDescription = document.getElementById('modal-description');

// Log Modal Elements
const logModal = document.getElementById('log-modal');
const logContent = document.getElementById('log-content');
const logModalClose = document.getElementById('log-modal-close');
const logModalCloseBtn = document.getElementById('log-modal-close-btn');

// Pagination elements
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const paginationInfo = document.getElementById('pagination-info');

// Stat elements
const statTotal = document.getElementById('stat-total');
const statDetails = document.getElementById('stat-details');
const statMatches = document.getElementById('stat-matches');
const statSites = document.getElementById('stat-sites');

// State
let matchingJobs = [];
let currentPage = 1;
let totalPages = 1;
let perPage = 20;
let statusCheckInterval = null;
let searchTimeout = null;
let lastLogCount = 0;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadSites();
    loadMatchingJobs();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Debounced search
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentPage = 1;
            renderMatchingJobs();
        }, 300);
    });
    
    filterSite.addEventListener('change', () => {
        currentPage = 1;
        renderMatchingJobs();
    });
    
    btnFullScrape.addEventListener('click', startFullScrape);
    
    // Pagination
    btnPrev.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderMatchingJobs();
        }
    });
    
    btnNext.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            renderMatchingJobs();
        }
    });
    
    modalClose.addEventListener('click', closeModal);
    logModalClose.addEventListener('click', closeLogModal);
    logModalCloseBtn.addEventListener('click', closeLogModal);
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    
    logModal.addEventListener('click', (e) => {
        if (e.target === logModal) closeLogModal();
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeLogModal();
        }
    });
}


// Load Matching Jobs (Matching Jobs tab)
async function loadMatchingJobs() {
    try {
        const response = await fetch('/api/matching/jobs');
        matchingJobs = await response.json();
        statMatches.textContent = matchingJobs.length;
        renderMatchingJobs();
    } catch (error) {
        console.error('Error loading matching jobs:', error);
        matchingJobs = [];
    }
}

// Render Matching Jobs
function renderMatchingJobs() {
    const searchTerm = searchInput.value.toLowerCase();
    
    let filtered = matchingJobs.filter(job => {
        const matchesSearch = 
            job.title.toLowerCase().includes(searchTerm) ||
            job.url.toLowerCase().includes(searchTerm);
        return matchesSearch;
    });
    
    // Pagination (client-side for matching jobs as it's a smaller set)
    const total = filtered.length;
    totalPages = Math.ceil(total / perPage) || 1;
    const start = (currentPage - 1) * perPage;
    const end = start + perPage;
    const paginated = filtered.slice(start, end);
    
    if (paginated.length === 0) {
        jobsTbody.innerHTML = '<tr><td colspan="6" class="loading-cell">No matching jobs found. Click "Scrape & Match" to start.</td></tr>';
        updatePagination({ page: 1, total_pages: 1, total: 0 });
        return;
    }
    
    jobsTbody.innerHTML = paginated.map(job => {
        const date = new Date(job.matched_at).toLocaleDateString();
        let statusClass = 'badge--success';
        let statusText = 'Match';
        
        if (job.status === 'viewed') {
            statusClass = 'badge--secondary';
            statusText = 'Viewed';
        } else if (job.is_new) {
            statusClass = 'badge--primary';
            statusText = 'New Match';
        }
        
        return `
            <tr>
                <td><span class="score-badge">${(job.score * 100).toFixed(0)}%</span></td>
                <td>${getSiteFromUrl(job.url)}</td>
                <td>${escapeHtml(job.title)}</td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
                <td><span class="text-secondary">${date}</span></td>
                <td>
                    <button class="btn btn--secondary btn--small" onclick="viewMatchingJob('${escapeHtml(job.url)}')">
                        View
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    updatePagination({ page: currentPage, total_pages: totalPages, total: total });
}

// Get site name from URL
function getSiteFromUrl(url) {
    try {
        const hostname = new URL(url).hostname;
        return hostname.replace('www.', '').split('.')[0];
    } catch {
        return 'unknown';
    }
}

// Load Sites for filter dropdown
async function loadSites() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        const sites = Object.keys(stats.sites).sort();
        filterSite.innerHTML = '<option value="">All Sites</option>';
        sites.forEach(site => {
            const option = document.createElement('option');
            option.value = site;
            option.textContent = site;
            filterSite.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading sites:', error);
    }
}

// Load Stats
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        statTotal.textContent = stats.total_urls;
        statDetails.textContent = stats.total_details;
        statSites.textContent = Object.keys(stats.sites).length;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}


// Update Pagination UI
function updatePagination(pagination) {
    const { page, total_pages, total } = pagination;
    
    paginationInfo.textContent = `Page ${page} of ${total_pages} (${total} jobs)`;
    
    btnPrev.disabled = page <= 1;
    btnNext.disabled = page >= total_pages;
}

// Get Status Badge HTML
function getStatusBadge(job) {
    if (job.seen) {
        return '<span class="badge badge--success">Seen</span>';
    } else if (job.has_details) {
        return '<span class="badge badge--warning">New</span>';
    } else {
        return '<span class="badge badge--pending">Pending</span>';
    }
}


// View Matching Job Details
function viewMatchingJob(url) {
    const job = matchingJobs.find(j => j.url === url);
    if (!job) return;
    
    // Mark as viewed immediately when opening modal
    if (job.status !== 'viewed') {
        markAsViewed(url);
    }
    
    modalTitle.textContent = job.title;
    modalSite.textContent = getSiteFromUrl(job.url);
    modalScore.textContent = `Match Score: ${(job.score * 100).toFixed(1)}%`;
    modalScore.classList.remove('hidden');
    modalLink.href = job.url;
    modalLink.onclick = null; // Remove click handler
    modalDescription.textContent = job.description || 'No description available.';
    
    modal.classList.remove('hidden');
}

async function markAsViewed(url) {
    try {
        await fetch('/api/jobs/view', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        const job = matchingJobs.find(j => j.url === url);
        if (job) {
            job.status = 'viewed';
            job.is_new = false;
            renderMatchingJobs();
        }
    } catch (error) {
        console.error('Error marking job as viewed:', error);
    }
}

// Start Full Scrape Process
async function startFullScrape() {
    btnFullScrape.disabled = true;
    logContent.innerHTML = '<div class="log-line">Starting unified process...</div>';
    logModal.classList.remove('hidden');
    lastLogCount = 0;
    
    try {
        const response = await fetch('/api/scrape/full', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            startStatusPolling();
        } else {
            addLogLine(`Error: ${result.message}`);
            btnFullScrape.disabled = false;
        }
    } catch (error) {
        console.error('Error starting full scrape:', error);
        addLogLine('Error connecting to server.');
        btnFullScrape.disabled = false;
    }
}

// Status Polling for Logs and Progress
function startStatusPolling() {
    if (statusCheckInterval) clearInterval(statusCheckInterval);
    
    statusCheckInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/scrape/status');
            const status = await response.json();
            
            // Update logs
            if (status.logs && status.logs.length > lastLogCount) {
                const newLogs = status.logs.slice(lastLogCount);
                newLogs.forEach(line => addLogLine(line));
                lastLogCount = status.logs.length;
                // Auto-scroll to bottom
                logContent.scrollTop = logContent.scrollHeight;
            }
            
            if (!status.running) {
                clearInterval(statusCheckInterval);
                statusCheckInterval = null;
                btnFullScrape.disabled = false;
                addLogLine(`\n --- Process Completed: ${status.message} ---`);
                
                // Refresh data
                loadStats();
                loadMatchingJobs();
            }
        } catch (error) {
            console.error('Error checking status:', error);
        }
    }, 500);
}

// Helper to add log line
function addLogLine(text) {
    const line = document.createElement('div');
    line.className = 'log-line';
    if (text.startsWith('>>>')) {
        line.classList.add('log-line--step');
    }
    line.textContent = text;
    logContent.appendChild(line);
}

// Close Modals
function closeModal() {
    modal.classList.add('hidden');
}

function closeLogModal() {
    logModal.classList.add('hidden');
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
