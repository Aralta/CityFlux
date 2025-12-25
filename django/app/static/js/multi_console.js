/**
 * Multi-Console Services - JavaScript
 * Gestion des logs Docker multi-services en temps réel
 */

class MultiConsole {
    constructor() {
        this.services = [
            { id: 'db', name: 'PostgreSQL', icon: '🐘', container: 'postgres_postgis' },
            { id: 'spark-master', name: 'Spark Master', icon: '⚡', container: 'spark-master' },
            { id: 'spark-worker', name: 'Spark Worker', icon: '👷', container: null }, // Multiple containers
            { id: 'spark-history', name: 'Spark History', icon: '📜', container: 'spark-history' },
            { id: 'spark-job-listener', name: 'Job Listener', icon: '👂', container: 'spark-job-listener' },
            { id: 'web', name: 'Django', icon: '🌐', container: 'django-server' },
            { id: 'celery-worker', name: 'Celery', icon: '🥬', container: 'celery-worker' },
            { id: 'redis', name: 'Redis', icon: '🔴', container: 'redis-server' }
        ];
        
        this.activeServices = new Set(['db', 'spark-master', 'web', 'celery-worker', 'redis', 'spark-job-listener']);
        this.logs = {};
        this.isPaused = false;
        this.refreshInterval = null;
        this.autoScroll = {};
        this.filters = {};
        this.maxLogLines = 500;
        
        this.init();
    }
    
    init() {
        this.createServiceToggles();
        this.createConsolePanels();
        this.setupEventListeners();
        this.startAutoRefresh();
        this.loadInitialLogs();
    }
    
    createServiceToggles() {
        const container = document.getElementById('serviceToggles');
        
        this.services.forEach(service => {
            const toggle = document.createElement('div');
            toggle.className = `service-toggle ${this.activeServices.has(service.id) ? 'active' : ''}`;
            toggle.dataset.service = service.id;
            toggle.innerHTML = `
                <span class="status-dot"></span>
                <span class="service-icon">${service.icon}</span>
                <span class="service-name">${service.name}</span>
            `;
            toggle.addEventListener('click', () => this.toggleService(service.id));
            container.appendChild(toggle);
        });
    }
    
    createConsolePanels() {
        const grid = document.getElementById('consoleGrid');
        grid.innerHTML = '';
        
        // Calculate optimal grid layout based on number of active services
        const count = this.activeServices.size;
        const layout = this.calculateOptimalLayout(count);
        grid.className = 'console-grid';
        grid.style.gridTemplateColumns = `repeat(${layout.cols}, 1fr)`;
        grid.style.gridTemplateRows = `repeat(${layout.rows}, 1fr)`;
        
        this.services.filter(s => this.activeServices.has(s.id)).forEach(service => {
            const panel = this.createPanel(service);
            grid.appendChild(panel);
            this.logs[service.id] = [];
            this.autoScroll[service.id] = true;
        });
    }
    
    calculateOptimalLayout(count) {
        // Determine optimal columns and rows to fit all panels on screen
        if (count <= 1) return { cols: 1, rows: 1 };
        if (count <= 2) return { cols: 2, rows: 1 };
        if (count <= 3) return { cols: 3, rows: 1 };
        if (count <= 4) return { cols: 2, rows: 2 };
        if (count <= 6) return { cols: 3, rows: 2 };
        if (count <= 8) return { cols: 4, rows: 2 };
        if (count <= 9) return { cols: 3, rows: 3 };
        if (count <= 12) return { cols: 4, rows: 3 };
        return { cols: 4, rows: Math.ceil(count / 4) };
    }
    
    createPanel(service) {
        const panel = document.createElement('div');
        panel.className = 'console-panel';
        panel.dataset.service = service.id;
        panel.id = `panel-${service.id}`;
        
        panel.innerHTML = `
            <div class="panel-header">
                <div class="panel-title">
                    <span class="service-icon">${service.icon}</span>
                    <h3>${service.name}</h3>
                    <span class="panel-status" id="status-${service.id}">checking...</span>
                </div>
                <div class="panel-controls">
                    <button class="panel-btn" onclick="console_app.filterPanel('${service.id}')" title="Filtrer">🔍</button>
                    <button class="panel-btn" onclick="console_app.clearPanel('${service.id}')" title="Effacer">🗑️</button>
                    <button class="panel-btn" onclick="console_app.toggleAutoScroll('${service.id}')" title="Auto-scroll" id="autoscroll-${service.id}">⬇️</button>
                    <button class="panel-btn" onclick="console_app.expandPanel('${service.id}')" title="Agrandir">⛶</button>
                </div>
            </div>
            <div class="log-output" id="logs-${service.id}">
                <div class="log-loading">Chargement des logs</div>
            </div>
            <div class="panel-footer">
                <div class="panel-stats">
                    <span class="stat-item">📝 <span id="linecount-${service.id}">0</span> lignes</span>
                </div>
                <input type="text" class="filter-input" id="filter-${service.id}" placeholder="Filtrer..." oninput="console_app.applyFilter('${service.id}')">
            </div>
        `;
        
        return panel;
    }
    
    setupEventListeners() {
        // Layout selector
        document.getElementById('layoutSelect').addEventListener('change', (e) => {
            const grid = document.getElementById('consoleGrid');
            const value = e.target.value;
            
            if (value === 'auto') {
                // Recalculate optimal layout
                this.createConsolePanels();
                this.loadInitialLogs();
            } else {
                // Apply predefined layout
                const layouts = {
                    'grid-2x2': { cols: 2, rows: 2 },
                    'grid-2x3': { cols: 3, rows: 2 },
                    'grid-3x3': { cols: 3, rows: 3 },
                    'horizontal': { cols: this.activeServices.size, rows: 1 },
                    'vertical': { cols: 1, rows: this.activeServices.size }
                };
                const layout = layouts[value] || { cols: 3, rows: 2 };
                grid.style.gridTemplateColumns = `repeat(${layout.cols}, 1fr)`;
                grid.style.gridTemplateRows = `repeat(${layout.rows}, 1fr)`;
            }
        });
        
        // Refresh rate selector
        document.getElementById('refreshRate').addEventListener('change', (e) => {
            const rate = parseInt(e.target.value);
            this.setRefreshRate(rate);
        });
        
        // Global controls
        document.getElementById('refreshAll').addEventListener('click', () => this.refreshAllLogs());
        document.getElementById('pauseAll').addEventListener('click', () => this.togglePause());
        document.getElementById('clearAll').addEventListener('click', () => this.clearAllPanels());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeExpandedPanel();
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                this.refreshAllLogs();
            }
            if (e.key === ' ' && e.ctrlKey) {
                e.preventDefault();
                this.togglePause();
            }
        });
    }
    
    setRefreshRate(rate) {
        // Clear existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        
        // Set new interval if rate > 0
        if (rate > 0) {
            this.refreshInterval = setInterval(() => {
                if (!this.isPaused) {
                    this.refreshAllLogs();
                }
            }, rate);
        }
    }
    
    toggleService(serviceId) {
        const toggle = document.querySelector(`.service-toggle[data-service="${serviceId}"]`);
        
        if (this.activeServices.has(serviceId)) {
            this.activeServices.delete(serviceId);
            toggle.classList.remove('active');
        } else {
            this.activeServices.add(serviceId);
            toggle.classList.add('active');
        }
        
        this.createConsolePanels();
        this.loadInitialLogs();
    }
    
    async loadInitialLogs() {
        for (const serviceId of this.activeServices) {
            await this.fetchLogs(serviceId);
        }
    }
    
    async fetchLogs(serviceId, tail = 100) {
        try {
            const response = await fetch(`/api/docker-logs/${serviceId}/?tail=${tail}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                this.updatePanel(serviceId, data.logs, data.container_status);
            } else {
                this.showError(serviceId, data.error || 'Erreur inconnue');
            }
        } catch (error) {
            this.showError(serviceId, `Erreur de connexion: ${error.message}`);
        }
    }
    
    updatePanel(serviceId, newLogs, status) {
        const logContainer = document.getElementById(`logs-${serviceId}`);
        const statusEl = document.getElementById(`status-${serviceId}`);
        const lineCountEl = document.getElementById(`linecount-${serviceId}`);
        
        if (!logContainer) return;
        
        // Update status
        if (statusEl) {
            statusEl.textContent = status || 'unknown';
            statusEl.className = `panel-status ${status === 'running' ? 'running' : 'stopped'}`;
        }
        
        // Update service toggle status
        const toggle = document.querySelector(`.service-toggle[data-service="${serviceId}"]`);
        if (toggle) {
            toggle.classList.remove('running', 'stopped', 'warning');
            if (status === 'running') toggle.classList.add('running');
            else if (status === 'exited') toggle.classList.add('stopped');
            else toggle.classList.add('warning');
        }
        
        // Parse and format logs (with filtering for multi-console requests)
        const formattedLogs = this.formatLogs(newLogs, serviceId);
        this.logs[serviceId] = formattedLogs.slice(-this.maxLogLines);
        
        // Apply filter if exists
        const filter = this.filters[serviceId] || '';
        const displayLogs = filter 
            ? this.logs[serviceId].filter(log => log.text.toLowerCase().includes(filter.toLowerCase()))
            : this.logs[serviceId];
        
        // Render logs
        logContainer.innerHTML = displayLogs.length > 0 
            ? displayLogs.map(log => this.renderLogLine(log)).join('')
            : '<div class="log-empty"><span class="log-empty-icon">📭</span>Aucun log disponible</div>';
        
        // Update line count
        if (lineCountEl) {
            lineCountEl.textContent = this.logs[serviceId].length;
        }
        
        // Auto-scroll
        if (this.autoScroll[serviceId]) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }
    
    formatLogs(rawLogs, serviceId) {
        if (!rawLogs) return [];
        
        return rawLogs.split('\n')
            .filter(line => line.trim())
            .filter(line => !this.shouldFilterLine(line, serviceId))
            .map(line => {
                const logType = this.detectLogType(line);
                const timestamp = this.extractTimestamp(line);
                
                return {
                    text: line,
                    type: logType,
                    timestamp: timestamp
                };
            });
    }
    
    shouldFilterLine(line, serviceId) {
        // Filter out multi-console API requests from web/django logs
        if (serviceId === 'web') {
            if (line.includes('/api/docker-logs/') || 
                line.includes('/api/docker-status/')) {
                return true;
            }
        }
        return false;
    }
    
    detectLogType(line) {
        const lowerLine = line.toLowerCase();
        if (lowerLine.includes('error') || lowerLine.includes('exception') || lowerLine.includes('failed') || lowerLine.includes('fatal')) {
            return 'error';
        }
        if (lowerLine.includes('warn')) {
            return 'warning';
        }
        if (lowerLine.includes('info')) {
            return 'info';
        }
        if (lowerLine.includes('debug') || lowerLine.includes('trace')) {
            return 'debug';
        }
        if (lowerLine.includes('success') || lowerLine.includes('completed') || lowerLine.includes('started')) {
            return 'success';
        }
        return '';
    }
    
    extractTimestamp(line) {
        // Try to extract common timestamp formats
        const patterns = [
            /(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})/,
            /(\d{2}:\d{2}:\d{2})/,
            /\[(\d{2}\/\w+\/\d{4}[: ]\d{2}:\d{2}:\d{2})\]/
        ];
        
        for (const pattern of patterns) {
            const match = line.match(pattern);
            if (match) return match[1];
        }
        return null;
    }
    
    renderLogLine(log) {
        const timestampHtml = log.timestamp 
            ? `<span class="log-timestamp">${log.timestamp}</span>` 
            : '';
        return `<div class="log-line ${log.type}">${timestampHtml}${this.escapeHtml(log.text)}</div>`;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showError(serviceId, message) {
        const logContainer = document.getElementById(`logs-${serviceId}`);
        if (logContainer) {
            logContainer.innerHTML = `<div class="log-line error">❌ ${message}</div>`;
        }
    }
    
    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            if (!this.isPaused) {
                this.refreshAllLogs();
            }
        }, 15000); // Refresh every 15 seconds (reduced from 5s to limit log spam)
    }
    
    async refreshAllLogs() {
        const promises = Array.from(this.activeServices).map(serviceId => 
            this.fetchLogs(serviceId, 100)
        );
        await Promise.all(promises);
    }
    
    togglePause() {
        this.isPaused = !this.isPaused;
        const btn = document.getElementById('pauseAll');
        btn.textContent = this.isPaused ? '▶️' : '⏸️';
        btn.classList.toggle('active', this.isPaused);
    }
    
    clearPanel(serviceId) {
        this.logs[serviceId] = [];
        const logContainer = document.getElementById(`logs-${serviceId}`);
        if (logContainer) {
            logContainer.innerHTML = '<div class="log-empty"><span class="log-empty-icon">📭</span>Logs effacés</div>';
        }
        document.getElementById(`linecount-${serviceId}`).textContent = '0';
    }
    
    clearAllPanels() {
        this.activeServices.forEach(serviceId => this.clearPanel(serviceId));
    }
    
    toggleAutoScroll(serviceId) {
        this.autoScroll[serviceId] = !this.autoScroll[serviceId];
        const btn = document.getElementById(`autoscroll-${serviceId}`);
        if (btn) {
            btn.style.opacity = this.autoScroll[serviceId] ? '1' : '0.5';
        }
    }
    
    applyFilter(serviceId) {
        const filterInput = document.getElementById(`filter-${serviceId}`);
        this.filters[serviceId] = filterInput ? filterInput.value : '';
        
        // Re-render with filter applied
        const displayLogs = this.filters[serviceId]
            ? this.logs[serviceId].filter(log => 
                log.text.toLowerCase().includes(this.filters[serviceId].toLowerCase())
            )
            : this.logs[serviceId];
        
        const logContainer = document.getElementById(`logs-${serviceId}`);
        if (logContainer) {
            logContainer.innerHTML = displayLogs.length > 0 
                ? displayLogs.map(log => this.renderLogLine(log)).join('')
                : '<div class="log-empty"><span class="log-empty-icon">🔍</span>Aucun résultat</div>';
        }
    }
    
    filterPanel(serviceId) {
        const filterInput = document.getElementById(`filter-${serviceId}`);
        if (filterInput) {
            filterInput.focus();
        }
    }
    
    expandPanel(serviceId) {
        const panel = document.getElementById(`panel-${serviceId}`);
        if (!panel) return;
        
        // Create overlay
        let overlay = document.querySelector('.panel-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'panel-overlay';
            overlay.addEventListener('click', () => this.closeExpandedPanel());
            document.body.appendChild(overlay);
        }
        
        overlay.classList.add('active');
        panel.classList.add('expanded');
        
        // Refresh logs for this panel
        this.fetchLogs(serviceId, 500);
    }
    
    closeExpandedPanel() {
        const expanded = document.querySelector('.console-panel.expanded');
        const overlay = document.querySelector('.panel-overlay');
        
        if (expanded) expanded.classList.remove('expanded');
        if (overlay) overlay.classList.remove('active');
    }
}

// Initialize
let console_app;
document.addEventListener('DOMContentLoaded', () => {
    console_app = new MultiConsole();
});
