/**
 * Contrôleur de carte interactive avec Leaflet et OpenStreetMap
 * Dépend de: carte-config.js, carte-utils.js
 */

// Cache pour les couleurs attribuées dynamiquement aux zones
const zoneColorCache = new Map();
let zoneColorIndex = 0;

class MapController {
    constructor(config) {
        this.config = config;
        this.map = null;
        this.layers = {};
        this.layerGroups = {};
        this.currentDetailLayer = null;
        this.baseTileLayer = null;
        this.searchMarker = null;
        
        this.dataCache = {};
        this.cacheExpiry = 30 * 60 * 1000;
        
        this.moveTimeout = null;
        this.debounceDelay = 300;
        
        this.isLoading = {};
        this.pendingRequests = new Set();
        this.lastLoadedBounds = {};
        
        this.init();
    }
    
    init() {
        this.initMap();
        this.loadLayers();
        this.setupEventListeners();
    }
    
    initMap() {
        this.map = L.map('map').setView(
            this.config.defaultCenter,
            this.config.defaultZoom
        );
        
        this.baseTileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        this.map.on('moveend', () => this.debouncedReload());
    }
    
    debouncedReload() {
        if (this.moveTimeout) clearTimeout(this.moveTimeout);
        this.moveTimeout = setTimeout(() => this.reloadVisibleLayers(), this.debounceDelay);
    }
    
    reloadVisibleLayers() {
        const currentBounds = this.getCurrentBounds();
        const layersToLoad = [];
        
        for (const layerId in this.layers) {
            if (this.layers[layerId].enabled && layerId !== 'background') {
                if (this.needsReload(layerId, currentBounds)) {
                    layersToLoad.push(layerId);
                }
            }
        }
        
        if (layersToLoad.length === 0) return;
        
        Promise.all(layersToLoad.map(layerId => this.loadLayerData(layerId)));
    }
    
    needsReload(layerId, currentBounds) {
        const lastBounds = this.lastLoadedBounds[layerId];
        if (!lastBounds) return true;
        
        const margin = 0.1;
        const lastWidth = lastBounds.maxLng - lastBounds.minLng;
        const lastHeight = lastBounds.maxLat - lastBounds.minLat;
        
        const safeZone = {
            minLng: lastBounds.minLng + lastWidth * margin,
            maxLng: lastBounds.maxLng - lastWidth * margin,
            minLat: lastBounds.minLat + lastHeight * margin,
            maxLat: lastBounds.maxLat - lastHeight * margin
        };
        
        return currentBounds.minLng < safeZone.minLng ||
               currentBounds.maxLng > safeZone.maxLng ||
               currentBounds.minLat < safeZone.minLat ||
               currentBounds.maxLat > safeZone.maxLat;
    }
    
    getCurrentBounds() {
        const bounds = this.map.getBounds();
        return {
            minLng: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLng: bounds.getEast(),
            maxLat: bounds.getNorth(),
            zoom: this.map.getZoom()
        };
    }
    
    async loadLayers() {
        try {
            const response = await fetch(this.config.apiEndpoints.layers);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            this.layers = {};
            data.layers.forEach(layer => {
                this.layers[layer.id] = layer;
            });
            
            this.renderLayersList();
            
            for (const layerId in this.layers) {
                if (this.layers[layerId].enabled && layerId !== 'background') {
                    await this.loadLayerData(layerId);
                }
            }
        } catch (error) {
            console.error('❌ Erreur chargement couches:', error);
            this.showError('Impossible de charger les couches');
        }
    }
    
    renderLayersList() {
        const layersList = document.getElementById('layersList');
        layersList.innerHTML = '';
        
        for (const layerId in this.layers) {
            const layer = this.layers[layerId];
            
            const layerItem = document.createElement('div');
            layerItem.className = 'layer-item';
            layerItem.dataset.layerId = layerId;
            
            const toggleHTML = layer.hasToggle !== false ? `
                <label class="toggle-switch">
                    <input type="checkbox" class="layer-toggle" data-layer-id="${layerId}" ${layer.enabled ? 'checked' : ''}>
                    <span class="toggle-slider"></span>
                </label>
            ` : '';
            
            layerItem.innerHTML = `
                <div class="layer-header">
                    <div class="layer-info" data-layer-id="${layerId}">
                        <span class="layer-icon">${layer.icon}</span>
                        <span class="layer-name">${layer.name}</span>
                    </div>
                    ${toggleHTML}
                </div>
                <div class="layer-description">${layer.description}</div>
            `;
            
            layersList.appendChild(layerItem);
        }
        
        this.setupLayerEvents();
    }
    
    setupLayerEvents() {
        document.querySelectorAll('.layer-toggle').forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                this.toggleLayer(e.target.dataset.layerId, e.target.checked);
            });
        });
        
        document.querySelectorAll('.layer-info').forEach(info => {
            info.addEventListener('click', (e) => {
                this.showLayerDetails(e.currentTarget.dataset.layerId);
            });
        });
    }
    
    async toggleLayer(layerId, enabled) {
        this.layers[layerId].enabled = enabled;
        
        if (enabled) {
            await this.loadLayerData(layerId);
        } else {
            this.hideLayerData(layerId);
        }
    }
    
    getCacheKey(layerId, filters) {
        let key = layerId;
        if (filters && Object.keys(filters).length > 0) {
            const filterStr = Object.entries(filters).sort().map(([k, v]) => `${k}=${v}`).join('_');
            key += `_${filterStr}`;
        }
        return key;
    }
    
    addToCache(cacheKey, newFeatures, bounds) {
        const cached = this.dataCache[cacheKey];
        const now = Date.now();
        
        if (!cached || (now - cached.timestamp) >= this.cacheExpiry) {
            this.dataCache[cacheKey] = {
                features: new Map(),
                bounds: bounds,
                timestamp: now
            };
        }
        
        const cache = this.dataCache[cacheKey];
        
        for (const feature of newFeatures) {
            const featureId = this.getFeatureId(feature);
            if (!cache.features.has(featureId)) {
                cache.features.set(featureId, feature);
            }
        }
        
        if (bounds) {
            cache.bounds = this.mergeBounds(cache.bounds, bounds);
        }
        cache.timestamp = now;
    }
    
    getFeatureId(feature) {
        if (feature.properties?.id) {
            return `${feature.properties.feature_type || 'f'}_${feature.properties.id}`;
        }
        const coords = feature.geometry?.coordinates;
        if (coords) {
            return JSON.stringify(coords).substring(0, 100);
        }
        return Math.random().toString(36);
    }
    
    mergeBounds(bounds1, bounds2) {
        if (!bounds1) return bounds2;
        if (!bounds2) return bounds1;
        return {
            minLng: Math.min(bounds1.minLng, bounds2.minLng),
            minLat: Math.min(bounds1.minLat, bounds2.minLat),
            maxLng: Math.max(bounds1.maxLng, bounds2.maxLng),
            maxLat: Math.max(bounds1.maxLat, bounds2.maxLat)
        };
    }
    
    getCachedFeatures(cacheKey) {
        const cached = this.dataCache[cacheKey];
        if (cached && cached.features) {
            return Array.from(cached.features.values());
        }
        return [];
    }
    
    clearLayerCache(layerId, keepDisplayed = false) {
        const keysToRemove = Object.keys(this.dataCache).filter(key => 
            key === layerId || key.startsWith(layerId + '_')
        );
        keysToRemove.forEach(key => delete this.dataCache[key]);
        delete this.lastLoadedBounds[layerId];
    }
    
    async loadLayerData(layerId) {
        const layer = this.layers[layerId];
        const bounds = this.getCurrentBounds();
        
        const activeFilters = {};
        if (layer.filters) {
            layer.filters.forEach(filter => {
                if (filter.value && filter.value !== 'Tous' && filter.value !== 'Toutes') {
                    activeFilters[filter.name] = filter.value;
                }
            });
        }
        
        const cacheKey = this.getCacheKey(layerId, activeFilters);
        
        if (this.pendingRequests.has(cacheKey)) return;
        
        this.isLoading[layerId] = true;
        
        try {
            this.pendingRequests.add(cacheKey);
            
            const expandedBounds = this.expandBounds(bounds, 0.5);
            
            const params = new URLSearchParams({
                minLng: expandedBounds.minLng,
                minLat: expandedBounds.minLat,
                maxLng: expandedBounds.maxLng,
                maxLat: expandedBounds.maxLat,
                zoom: bounds.zoom
            });
            
            Object.entries(activeFilters).forEach(([name, value]) => {
                params.append(name, value);
            });
            
            const url = `${this.config.apiEndpoints.layerData.replace('{id}', layerId)}?${params}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                console.warn(`⚠️ Erreur API pour ${layerId}:`, data.error);
                return;
            }
            
            if (data.features && data.features.length > 0) {
                this.addToCache(cacheKey, data.features, expandedBounds);
                this.lastLoadedBounds[layerId] = this.mergeBounds(
                    this.lastLoadedBounds[layerId], 
                    expandedBounds
                );
            }
            
            this.displayLayerFeatures(layerId, cacheKey);
            
        } catch (error) {
            console.error(`❌ Erreur chargement ${layerId}:`, error);
            const existingFeatures = this.getCachedFeatures(cacheKey);
            if (existingFeatures.length > 0) {
                this.displayLayerFeatures(layerId, cacheKey);
            }
        } finally {
            this.pendingRequests.delete(cacheKey);
            this.isLoading[layerId] = false;
        }
    }
    
    expandBounds(bounds, percent) {
        const lngRange = bounds.maxLng - bounds.minLng;
        const latRange = bounds.maxLat - bounds.minLat;
        return {
            minLng: bounds.minLng - lngRange * percent,
            minLat: bounds.minLat - latRange * percent,
            maxLng: bounds.maxLng + lngRange * percent,
            maxLat: bounds.maxLat + latRange * percent,
            zoom: bounds.zoom
        };
    }
    
    displayLayerFeatures(layerId, cacheKey) {
        const layer = this.layers[layerId];
        const config = layer.config;
        const features = this.getCachedFeatures(cacheKey);
        
        if (features.length === 0) return;
        
        const validFeatures = features.filter(f => {
            if (!f.geometry || !f.geometry.coordinates) return false;
            const coords = f.geometry.coordinates;
            if (f.geometry.type === 'Point') {
                return Array.isArray(coords) && coords.length >= 2 && isFinite(coords[0]) && isFinite(coords[1]);
            }
            if (f.geometry.type === 'LineString' || f.geometry.type === 'Polygon') {
                return Array.isArray(coords) && coords.length > 0;
            }
            return true;
        });
        
        if (validFeatures.length === 0) return;
        
        const oldLayerGroup = this.layerGroups[layerId];
        this.layerGroups[layerId] = L.layerGroup();
        
        const displayData = {
            type: 'FeatureCollection',
            features: validFeatures
        };
        
        if (layer.type === 'geojson' || layer.type === 'polygon') {
            L.geoJSON(displayData, {
                style: (feature) => {
                    if (layerId === 'zones' && feature.properties) {
                        const zoneColor = getZoneColor(feature.properties);
                        return {
                            color: zoneColor.stroke,
                            weight: config.weight || 2,
                            opacity: config.opacity || 0.8,
                            fillColor: zoneColor.fill,
                            fillOpacity: config.fillOpacity || 0.4
                        };
                    }
                    return {
                        color: config.color || '#1a73e8',
                        weight: config.weight || 2,
                        opacity: config.opacity || 0.7,
                        fillColor: config.fillColor || config.color,
                        fillOpacity: config.fillOpacity || 0.3
                    };
                },
                onEachFeature: (feature, layerObj) => {
                    if (feature.properties) {
                        layerObj.bindPopup(this.createPopupContent(feature.properties));
                    }
                }
            }).addTo(this.layerGroups[layerId]);
            
        } else if (layer.type === 'markers') {
            if (validFeatures.length > 100 && typeof L.markerClusterGroup !== 'undefined') {
                const markers = L.markerClusterGroup();
                validFeatures.forEach(feature => {
                    const coords = feature.geometry.coordinates;
                    let marker;
                    
                    if (layerId === 'poi' && feature.properties) {
                        const emoji = getPOIIcon(feature.properties);
                        const iconSize = config.iconSize ? config.iconSize[0] : 28;
                        marker = L.marker([coords[1], coords[0]], { icon: createEmojiIcon(emoji, iconSize) });
                    } else {
                        marker = L.marker([coords[1], coords[0]]);
                    }
                    
                    if (feature.properties) {
                        marker.bindPopup(this.createPopupContent(feature.properties));
                    }
                    markers.addLayer(marker);
                });
                this.layerGroups[layerId].addLayer(markers);
            } else {
                validFeatures.forEach(feature => {
                    const coords = feature.geometry.coordinates;
                    let marker;
                    
                    if (layerId === 'poi' && feature.properties) {
                        const emoji = getPOIIcon(feature.properties);
                        const iconSize = config.iconSize ? config.iconSize[0] : 28;
                        marker = L.marker([coords[1], coords[0]], { icon: createEmojiIcon(emoji, iconSize) });
                    } else {
                        marker = L.marker([coords[1], coords[0]]);
                    }
                    
                    if (feature.properties) {
                        marker.bindPopup(this.createPopupContent(feature.properties));
                    }
                    marker.addTo(this.layerGroups[layerId]);
                });
            }
        }
        
        this.layerGroups[layerId].addTo(this.map);
        
        if (oldLayerGroup) {
            this.map.removeLayer(oldLayerGroup);
        }
    }
    
    createPopupContent(properties) {
        let content = '<div class="popup-content">';
        
        let ignoreKeys = ['feature_type', 'id'];
        if (properties.feature_type === 'poi') {
            ignoreKeys.push('type');
        }
        
        if (properties.nom || properties.name) {
            content += `<h4>${properties.nom || properties.name}</h4>`;
        }
        
        for (const key in properties) {
            if (!ignoreKeys.includes(key) && key !== 'nom' && key !== 'name') {
                const value = properties[key];
                if (value !== null && value !== undefined && value !== '') {
                    const label = POPUP_LABELS[key] || key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
                    content += `<p><strong>${label}:</strong> ${value}</p>`;
                }
            }
        }
        
        content += '</div>';
        return content;
    }
    
    hideLayerData(layerId) {
        if (this.layerGroups[layerId]) {
            this.map.removeLayer(this.layerGroups[layerId]);
        }
    }
    
    async showLayerDetails(layerId) {
        try {
            const url = this.config.apiEndpoints.layerConfig.replace('{id}', layerId);
            const response = await fetch(url);
            const config = await response.json();
            
            this.currentDetailLayer = layerId;
            
            const detailMenu = document.getElementById('detailMenu');
            const detailTitle = document.getElementById('detailTitle');
            const detailContent = document.getElementById('detailContent');
            
            detailTitle.textContent = `${config.icon || ''} ${config.name}`;
            
            let content = '';
            
            if (config.parameters && config.parameters.length > 0) {
                content += '<div class="detail-section"><h4>Paramètres visuels</h4>';
                config.parameters.forEach(param => {
                    content += this.renderParameter(param);
                });
                content += '</div>';
            }
            
            if (config.filters && config.filters.length > 0) {
                content += '<div class="detail-section"><h4>Filtres</h4>';
                config.filters.forEach(filter => {
                    content += this.renderParameter(filter);
                });
                content += '</div>';
            }
            
            if (config.info) {
                content += '<div class="detail-section"><h4>Informations</h4>';
                content += '<div class="info-grid">';
                for (const key in config.info) {
                    const label = key.charAt(0).toUpperCase() + key.slice(1);
                    content += `<div class="info-item"><strong>${label}:</strong> ${config.info[key]}</div>`;
                }
                content += '</div></div>';
            }
            
            detailContent.innerHTML = content;
            detailMenu.classList.remove('hidden');
            
            this.setupDetailEvents(layerId);
        } catch (error) {
            // Erreur silencieuse
        }
    }
    
    renderParameter(param) {
        let html = `<div class="parameter-item"><label class="parameter-label">${param.label}</label>`;
        
        switch (param.type) {
            case 'color':
                html += `<input type="color" class="parameter-control" data-param="${param.name}" value="${param.value}">`;
                break;
            case 'range':
                html += `<div class="range-control">
                    <input type="range" class="parameter-control" data-param="${param.name}" 
                        min="${param.min}" max="${param.max}" step="${param.step}" value="${param.value}">
                    <span class="range-value">${param.value}</span>
                </div>`;
                break;
            case 'checkbox':
                html += `<input type="checkbox" class="parameter-control" data-param="${param.name}" ${param.value ? 'checked' : ''}>`;
                break;
            case 'select':
                html += `<select class="parameter-control" data-param="${param.name}">`;
                param.options.forEach(opt => {
                    html += `<option value="${opt}" ${opt === param.value ? 'selected' : ''}>${opt}</option>`;
                });
                html += `</select>`;
                break;
            case 'multiselect':
                param.options.forEach(opt => {
                    const checked = param.value.includes(opt);
                    html += `<label class="checkbox-label">
                        <input type="checkbox" class="parameter-control" data-param="${param.name}" value="${opt}" ${checked ? 'checked' : ''}>${opt}
                    </label>`;
                });
                break;
        }
        
        html += `</div>`;
        return html;
    }
    
    setupDetailEvents(layerId) {
        document.querySelectorAll('#detailContent .parameter-control').forEach(control => {
            control.addEventListener('change', (e) => {
                this.updateLayerParameter(layerId, e.target);
            });
            
            if (control.type === 'range') {
                control.addEventListener('input', (e) => {
                    const valueSpan = e.target.nextElementSibling;
                    if (valueSpan) valueSpan.textContent = e.target.value;
                });
            }
        });
    }
    
    updateLayerParameter(layerId, control) {
        const paramName = control.dataset.param;
        let value;
        
        if (control.type === 'checkbox') {
            value = control.checked;
        } else if (control.type === 'range') {
            value = parseFloat(control.value);
        } else {
            value = control.value;
        }
        
        this.layers[layerId].config[paramName] = value;
        
        const layer = this.layers[layerId];
        if (layer.filters) {
            const filter = layer.filters.find(f => f.name === paramName);
            if (filter) {
                filter.value = value;
                this.clearLayerCache(layerId, true);
            }
        }
        
        if (layerId === 'background') {
            if (paramName === 'variant') {
                this.changeBaseTiles(value);
            }
        } else {
            if (this.layers[layerId].enabled) {
                this.loadLayerData(layerId);
            }
        }
    }
    
    changeBaseTiles(variant) {
        if (this.baseTileLayer) {
            this.map.removeLayer(this.baseTileLayer);
        }
        
        const config = TILE_CONFIGS[variant] || TILE_CONFIGS['Plan'];
        
        this.baseTileLayer = L.tileLayer(config.url, {
            attribution: config.attribution,
            maxZoom: config.maxZoom,
            subdomains: config.subdomains || 'abc'
        }).addTo(this.map);
    }
    
    setupEventListeners() {
        const searchButton = document.getElementById('searchButton');
        const searchInput = document.getElementById('searchInput');
        
        searchButton.addEventListener('click', () => this.performSearch());
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        
        let searchTimeout = null;
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (searchTimeout) clearTimeout(searchTimeout);
            
            if (query.length < 3) {
                this.hideSuggestions();
                return;
            }
            
            searchTimeout = setTimeout(() => this.fetchSuggestions(query), 300);
        });
        
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-section')) {
                this.hideSuggestions();
            }
        });
        
        document.getElementById('closeDetail').addEventListener('click', () => {
            document.getElementById('detailMenu').classList.add('hidden');
            this.currentDetailLayer = null;
        });
        
        document.getElementById('resetView').addEventListener('click', () => {
            this.map.setView(this.config.defaultCenter, this.config.defaultZoom);
        });
        
        document.getElementById('toggleFullscreen').addEventListener('click', () => {
            this.toggleFullscreen();
        });
    }
    
    async fetchSuggestions(query) {
        try {
            await new Promise(resolve => setTimeout(resolve, 300));
            
            const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`;
            const response = await fetch(url, { headers: { 'Accept': 'application/json' } });
            
            if (!response.ok) return;
            
            const data = await response.json();
            
            if (data && data.length > 0) {
                this.displaySuggestions(data);
            } else {
                this.hideSuggestions();
            }
        } catch (error) {
            // Erreur silencieuse
        }
    }
    
    displaySuggestions(suggestions) {
        const searchResults = document.getElementById('searchResults');
        searchResults.innerHTML = '';
        
        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.innerHTML = `
                <div class="suggestion-icon">📍</div>
                <div class="suggestion-text">
                    <div class="suggestion-name">${suggestion.display_name}</div>
                    <div class="suggestion-type">${formatSuggestionType(suggestion.type)}</div>
                </div>
            `;
            
            item.addEventListener('click', () => this.selectSuggestion(suggestion));
            searchResults.appendChild(item);
        });
        
        searchResults.classList.remove('hidden');
    }
    
    hideSuggestions() {
        const searchResults = document.getElementById('searchResults');
        searchResults.classList.add('hidden');
        searchResults.innerHTML = '';
    }
    
    selectSuggestion(suggestion) {
        const searchInput = document.getElementById('searchInput');
        searchInput.value = suggestion.display_name;
        
        const lat = parseFloat(suggestion.lat);
        const lng = parseFloat(suggestion.lon);
        
        this.map.setView([lat, lng], 15);
        
        if (this.searchMarker) {
            this.map.removeLayer(this.searchMarker);
        }
        
        this.searchMarker = L.marker([lat, lng])
            .addTo(this.map)
            .bindPopup(`<strong>${suggestion.display_name}</strong>`)
            .openPopup();
        
        this.hideSuggestions();
    }
    
    async performSearch() {
        const searchInput = document.getElementById('searchInput');
        const query = searchInput.value.trim();
        
        if (!query) return;
        
        const searchResults = document.getElementById('searchResults');
        searchResults.innerHTML = '<div class="loading">Recherche en cours...</div>';
        searchResults.classList.remove('hidden');
        
        try {
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`;
            const response = await fetch(url, { headers: { 'Accept': 'application/json' } });
            
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            
            if (data && data.length > 0) {
                const result = data[0];
                const lat = parseFloat(result.lat);
                const lng = parseFloat(result.lon);
                
                if (isNaN(lat) || isNaN(lng)) throw new Error('Coordonnées invalides');
                
                this.map.setView([lat, lng], 13);
                
                if (this.searchMarker) {
                    this.map.removeLayer(this.searchMarker);
                }
                
                this.searchMarker = L.marker([lat, lng])
                    .addTo(this.map)
                    .bindPopup(`<strong>${result.display_name}</strong>`)
                    .openPopup();
                
                searchResults.innerHTML = `<div class="success">📍 ${result.display_name}</div>`;
                setTimeout(() => searchResults.classList.add('hidden'), 3000);
            } else {
                searchResults.innerHTML = '<div class="error">Aucun résultat trouvé</div>';
                setTimeout(() => searchResults.classList.add('hidden'), 3000);
            }
        } catch (error) {
            searchResults.innerHTML = `<div class="error">Erreur lors de la recherche</div>`;
            setTimeout(() => searchResults.classList.add('hidden'), 3000);
        }
    }
    
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
    
    showError(message) {
        const layersList = document.getElementById('layersList');
        layersList.innerHTML = `<div class="error">${message}</div>`;
    }
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    window.mapController = new MapController(MAP_CONFIG);
});
