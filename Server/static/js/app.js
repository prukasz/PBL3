/**
 * BLE Tag Tracker - Frontend Application
 */

// State
let selectedTag = null;
let tags = {};
let historyPoints = [];
let mapImage = null;
let updateInterval = null;

// DOM Elements
const tagsLayer = document.getElementById('tags-layer');
const historyLayer = document.getElementById('history-layer');
const tagList = document.getElementById('tag-list');
const tagInfo = document.getElementById('tag-info');
const tagCount = document.getElementById('tag-count');
const statusIndicator = document.getElementById('connection-status');
const statusText = document.getElementById('status-text');
const historyRangeSelect = document.getElementById('history-range');
const showHistoryBtn = document.getElementById('show-history-btn');
const clearHistoryBtn = document.getElementById('clear-history-btn');
const alarmModal = document.getElementById('alarm-modal');
const alarmTagMac = document.getElementById('alarm-tag-mac');
const roomSelect = document.getElementById('room-select');
const sendAlarmBtn = document.getElementById('send-alarm-btn');
const cancelAlarmBtn = document.getElementById('cancel-alarm-btn');
const closeModalBtn = document.getElementById('close-modal');
const floorMap = document.getElementById('floor-map');

// Configuration - based on floor plan coordinates
// Coordinate system: X from -4883 to 590, Y from 270 to 4800
// Origin (0,0) is at bottom-right of the map
const MAP_CONFIG = {
    // Coordinate bounds from floor plan
    minX: -4883,
    maxX: 450,
    minY: -400,
    maxY: 5000,
    // Map image dimensions (will be updated when image loads)
    mapWidth: 1000,
    mapHeight: 600,
    // Padding from edges
    padding: 20
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    init();
});

async function init() {
    // Wait for map image to load
    floorMap.onload = () => {
        console.log('Map loaded:', floorMap.naturalWidth, 'x', floorMap.naturalHeight);
        // Update map dimensions in config
        MAP_CONFIG.mapWidth = floorMap.naturalWidth;
        MAP_CONFIG.mapHeight = floorMap.naturalHeight;
        // Re-render tags with correct positions
        renderTags();
    };
    
    // If image already loaded
    if (floorMap.complete) {
        MAP_CONFIG.mapWidth = floorMap.naturalWidth;
        MAP_CONFIG.mapHeight = floorMap.naturalHeight;
    }
    
    // Setup event listeners
    setupEventListeners();
    
    // Start fetching positions
    await fetchPositions();
    updateInterval = setInterval(fetchPositions, 2000); // Update every 2 seconds
    
    setConnectionStatus(true);
}

function setupEventListeners() {
    // History controls
    showHistoryBtn.addEventListener('click', () => {
        if (selectedTag) {
            fetchHistory(selectedTag);
        }
    });
    
    clearHistoryBtn.addEventListener('click', clearHistory);
    
    // Modal controls
    closeModalBtn.addEventListener('click', closeModal);
    cancelAlarmBtn.addEventListener('click', closeModal);
    sendAlarmBtn.addEventListener('click', sendAlarm);
    
    // Close modal on outside click
    alarmModal.addEventListener('click', (e) => {
        if (e.target === alarmModal) {
            closeModal();
        }
    });
}

// API Functions
async function fetchPositions() {
    try {
        const response = await fetch('/api/positions');
        if (!response.ok) throw new Error('Failed to fetch positions');
        
        const positions = await response.json();
        updateTags(positions);
        setConnectionStatus(true);
    } catch (error) {
        console.error('Error fetching positions:', error);
        setConnectionStatus(false);
    }
}

async function fetchHistory(mac) {
    try {
        const range = historyRangeSelect.value;
        const response = await fetch(`/api/history/${mac}?range=${range}`);
        if (!response.ok) throw new Error('Failed to fetch history');
        
        const history = await response.json();
        displayHistory(history, mac);
        showToast(`Historia załadowana: ${history.length} punktów`, 'info');
    } catch (error) {
        console.error('Error fetching history:', error);
        showToast('Błąd ładowania historii', 'error');
    }
}

async function sendAlarm() {
    const mac = alarmTagMac.dataset.mac || alarmTagMac.textContent;  // Użyj MAC z dataset
    const tagName = alarmTagMac.textContent;  // Nazwa do wyświetlenia
    const room = roomSelect.value;
    
    try {
        const response = await fetch('/api/alarm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mac, room })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast(`Alarm wysłany do ${tagName} - pokój ${room}`, 'success');
            closeModal();
        } else {
            throw new Error(result.error || 'Unknown error');
        }
    } catch (error) {
        console.error('Error sending alarm:', error);
        showToast(`Błąd wysyłania alarmu: ${error.message}`, 'error');
    }
}

// UI Functions
function updateTags(positions) {
    // Update internal state
    const newTags = {};
    
    positions.forEach(pos => {
        newTags[pos.mac] = {
            mac: pos.mac,
            name: pos.name || pos.mac,  // Użyj nazwy z API lub MAC jako fallback
            x: pos.x,
            y: pos.y,
            time: pos.time
        };
    });
    
    tags = newTags;
    
    // Update counter
    tagCount.textContent = Object.keys(tags).length;
    
    // Render tags on map
    renderTags();
    
    // Update tag list
    renderTagList();
    
    // Update info panel if tag is selected
    if (selectedTag && tags[selectedTag]) {
        updateTagInfo(tags[selectedTag]);
    }
}

function renderTags() {
    tagsLayer.innerHTML = '';
    
    Object.values(tags).forEach(tag => {
        const marker = createTagMarker(tag);
        tagsLayer.appendChild(marker);
    });
}

function createTagMarker(tag) {
    const marker = document.createElement('div');
    marker.className = 'tag-marker';
    if (tag.mac === selectedTag) {
        marker.classList.add('selected');
    }
    
    // Convert coordinates to pixels
    const { pixelX, pixelY } = coordsToPixels(tag.x, tag.y);
    marker.style.left = `${pixelX}px`;
    marker.style.top = `${pixelY}px`;
    
    // Add label - użyj nazwy taga zamiast MAC
    const label = document.createElement('span');
    label.className = 'tag-label';
    label.textContent = tag.name;
    marker.appendChild(label);
    
    // Click handler
    marker.addEventListener('click', () => {
        selectTag(tag.mac);
    });
    
    // Double click to open alarm modal
    marker.addEventListener('dblclick', () => {
        openAlarmModal(tag.mac);
    });
    
    return marker;
}

function renderTagList() {
    tagList.innerHTML = '';
    
    Object.values(tags).forEach(tag => {
        const li = document.createElement('li');
        if (tag.mac === selectedTag) {
            li.classList.add('selected');
        }
        
        li.innerHTML = `
            <span class="tag-mac">${tag.name}</span>
            <span class="tag-pos">(${tag.x.toFixed(1)}, ${tag.y.toFixed(1)})</span>
        `;
        
        li.addEventListener('click', () => {
            selectTag(tag.mac);
        });
        
        tagList.appendChild(li);
    });
}

function selectTag(mac) {
    selectedTag = mac;
    showHistoryBtn.disabled = false;
    
    // Re-render to update selection
    renderTags();
    renderTagList();
    
    // Update info panel
    if (tags[mac]) {
        updateTagInfo(tags[mac]);
    }
}

function updateTagInfo(tag) {
    tagInfo.innerHTML = `
        <div class="info-row">
            <span class="info-label">Nazwa:</span>
            <span>${tag.name}</span>
        </div>
        <div class="info-row">
            <span class="info-label">MAC:</span>
            <span>${formatMac(tag.mac)}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Pozycja X:</span>
            <span>${tag.x.toFixed(2)}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Pozycja Y:</span>
            <span>${tag.y.toFixed(2)}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Ostatnia aktualizacja:</span>
            <span>${tag.time ? new Date(tag.time).toLocaleTimeString('pl-PL') : 'N/A'}</span>
        </div>
        <button class="btn btn-danger alarm-btn" onclick="openAlarmModal('${tag.mac}')">
            🔔 Wyślij Alarm
        </button>
    `;
}

function displayHistory(history, mac) {
    clearHistory();
    
    if (history.length === 0) {
        showToast('Brak historii dla tego tagu', 'info');
        return;
    }
    
    // Sort by time (oldest first for proper saturation calculation)
    history.sort((a, b) => new Date(a.time) - new Date(b.time));
    
    const now = new Date();
    const oldest = new Date(history[0].time);
    const timeSpan = now - oldest;
    
    history.forEach((point, index) => {
        const pointElement = document.createElement('div');
        pointElement.className = 'history-point';
        
        // Calculate saturation based on time (more recent = more saturated)
        const pointTime = new Date(point.time);
        const age = now - pointTime;
        const saturation = 1 - (age / timeSpan); // 0 to 1
        const opacity = 0.2 + (saturation * 0.8); // 0.2 to 1.0
        const size = 6 + (saturation * 6); // 6px to 12px
        
        const { pixelX, pixelY } = coordsToPixels(point.x, point.y);
        
        pointElement.style.left = `${pixelX}px`;
        pointElement.style.top = `${pixelY}px`;
        pointElement.style.opacity = opacity;
        pointElement.style.width = `${size}px`;
        pointElement.style.height = `${size}px`;
        pointElement.style.backgroundColor = `hsl(210, ${50 + saturation * 50}%, ${40 + saturation * 20}%)`;
        
        historyLayer.appendChild(pointElement);
        historyPoints.push(pointElement);
    });
}

function clearHistory() {
    historyLayer.innerHTML = '';
    historyPoints = [];
}

// Modal Functions
function openAlarmModal(mac) {
    // Pokaż nazwę taga w modalu (jeśli dostępna)
    const tag = tags[mac];
    const displayName = tag ? tag.name : mac;
    alarmTagMac.textContent = displayName;
    alarmTagMac.dataset.mac = mac;  // Przechowaj MAC do wysłania
    alarmModal.classList.add('active');
}

function closeModal() {
    alarmModal.classList.remove('active');
}

// Utility Functions
function coordsToPixels(x, y) {
    // Convert floor plan coordinates to pixel position on map image
    // X: -4883 (left) to 590 (right)
    // Y: 270 (bottom) to 4800 (top)
    
    const coordWidth = MAP_CONFIG.maxX - MAP_CONFIG.minX;   // 5473
    const coordHeight = MAP_CONFIG.maxY - MAP_CONFIG.minY;  // 4530
    
    const usableWidth = MAP_CONFIG.mapWidth - (2 * MAP_CONFIG.padding);
    const usableHeight = MAP_CONFIG.mapHeight - (2 * MAP_CONFIG.padding);
    
    // Normalize coordinates to 0-1 range
    const normalizedX = (x - MAP_CONFIG.minX) / coordWidth;
    // Y is inverted: higher Y values should be at top (lower pixel values)
    const normalizedY = 1 - ((y - MAP_CONFIG.minY) / coordHeight);
    
    return {
        pixelX: MAP_CONFIG.padding + (normalizedX * usableWidth),
        pixelY: MAP_CONFIG.padding + (normalizedY * usableHeight)
    };
}

function formatMac(mac) {
    // Format MAC address for display (add colons)
    if (mac.length === 12) {
        return mac.match(/.{2}/g).join(':');
    }
    return mac;
}

function setConnectionStatus(connected) {
    if (connected) {
        statusIndicator.className = 'status-indicator connected';
        statusText.textContent = 'Połączono';
    } else {
        statusIndicator.className = 'status-indicator disconnected';
        statusText.textContent = 'Rozłączono';
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Make openAlarmModal available globally
window.openAlarmModal = openAlarmModal;
