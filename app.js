// Load sources data
let allSources = [];
let filteredSources = [];

// Fetch sources data
async function loadSources() {
    try {
        const response = await fetch('sources_data.json');
        allSources = await response.json();
        filteredSources = [...allSources];
        renderSources();
        populateCategories();
        updateStats();
        document.getElementById('lastUpdated').textContent = new Date().toLocaleDateString('uk-UA');
    } catch (error) {
        console.error('Error loading sources:', error);
        // Fallback: try to load from embedded data if fetch fails
        if (typeof sourcesData !== 'undefined') {
            allSources = sourcesData;
            filteredSources = [...allSources];
            renderSources();
            populateCategories();
            updateStats();
        }
    }
}

function populateCategories() {
    const categories = [...new Set(allSources.map(s => s.category))].sort();
    const select = document.getElementById('categoryFilter');
    
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        select.appendChild(option);
    });
}

function renderSources() {
    const container = document.getElementById('sourcesContainer');
    
    if (filteredSources.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #6c757d;"><p style="font-size: 1.2em;">No sources found matching your criteria.</p></div>';
        return;
    }
    
    container.innerHTML = filteredSources.map(source => `
        <div class="source-card">
            <div class="source-header">
                <div class="source-name">${source.id}. ${escapeHtml(source.name)}</div>
                <a href="${source.url}" target="_blank" rel="noopener noreferrer" class="source-url">
                    ${truncateUrl(source.url)}
                </a>
                <div class="category-badge">${escapeHtml(source.category)}</div>
            </div>
            
            <div class="sample-data">
                <h3>Sample Data</h3>
                ${renderSampleData(source.sample_data)}
                <a href="${source.url}" target="_blank" rel="noopener noreferrer" class="more-data-link">
                    View Full Data →
                </a>
            </div>
            
            <div class="metadata">
                <span>📈 Total Records: ${source.sample_data.total_records || 'N/A'}</span>
                <span>🕒 Updated: ${source.sample_data.last_updated || 'N/A'}</span>
            </div>
        </div>
    `).join('');
}

function renderSampleData(sampleData) {
    if (!sampleData || !sampleData.sample) {
        return '<p style="color: #6c757d; font-style: italic;">Sample data not available</p>';
    }
    
    return sampleData.sample.map(item => {
        const fields = Object.entries(item)
            .map(([key, value]) => `<span><strong>${escapeHtml(key)}:</strong> ${escapeHtml(String(value))}</span>`)
            .join('<br>');
        return `<div class="sample-item">${fields}</div>`;
    }).join('');
}

function truncateUrl(url) {
    if (url.length > 60) {
        return url.substring(0, 57) + '...';
    }
    return url;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function filterSources() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const categoryFilter = document.getElementById('categoryFilter').value;
    
    filteredSources = allSources.filter(source => {
        const matchesSearch = !searchTerm || 
            source.name.toLowerCase().includes(searchTerm) ||
            source.url.toLowerCase().includes(searchTerm) ||
            source.category.toLowerCase().includes(searchTerm);
        
        const matchesCategory = !categoryFilter || source.category === categoryFilter;
        
        return matchesSearch && matchesCategory;
    });
    
    renderSources();
    updateStats();
}

function updateStats() {
    document.getElementById('resultsCount').textContent = filteredSources.length;
}

// Event listeners
document.getElementById('searchInput').addEventListener('input', filterSources);
document.getElementById('categoryFilter').addEventListener('change', filterSources);
document.getElementById('clearSearch').addEventListener('click', () => {
    document.getElementById('searchInput').value = '';
    document.getElementById('categoryFilter').value = '';
    filterSources();
});

// Load sources on page load
loadSources();

