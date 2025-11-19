/**
 * Gestionnaire de carte interactive avec Leaflet et OpenStreetMap
 * Gère les couches, la recherche et les interactions utilisateur
 */

class MapController {
    constructor(config) {
        this.config = config;
        this.map = null;
        this.layers = {};
        this.layerGroups = {};
        this.currentDetailLayer = null;
        
        this.init();
    }
    
    /**
     * Initialisation de la carte et des événements
     */
    init() {
        this.initMap();
        this.loadLayers();
        this.setupEventListeners();
    }
    
    /**
     * Initialisation de la carte Leaflet
     */
    initMap() {
        // Création de la carte
        this.map = L.map('map').setView(
            this.config.defaultCenter,
            this.config.defaultZoom
        );
        
        // Ajout de la couche de tuiles OSM
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        console.log('Carte initialisée');
    }
    
    /**
     * Chargement de la liste des couches depuis l'API
     */
    async loadLayers() {
        try {
            const response = await fetch(this.config.apiEndpoints.layers);
            const data = await response.json();
            
            this.layers = {};
            data.layers.forEach(layer => {
                this.layers[layer.id] = layer;
            });
            
            this.renderLayersList();
            
            // Charger les données des couches activées par défaut
            for (const layerId in this.layers) {
                if (this.layers[layerId].enabled) {
                    await this.loadLayerData(layerId);
                }
            }
            
        } catch (error) {
            console.error('Erreur lors du chargement des couches:', error);
            this.showError('Impossible de charger les couches');
        }
    }
    
    /**
     * Affichage de la liste des couches dans le panneau latéral
     */
    renderLayersList() {
        const layersList = document.getElementById('layersList');
        layersList.innerHTML = '';
        
        for (const layerId in this.layers) {
            const layer = this.layers[layerId];
            
            const layerItem = document.createElement('div');
            layerItem.className = 'layer-item';
            layerItem.dataset.layerId = layerId;
            
            layerItem.innerHTML = `
                <div class="layer-header">
                    <div class="layer-info" data-layer-id="${layerId}">
                        <span class="layer-icon">${layer.icon}</span>
                        <span class="layer-name">${layer.name}</span>
                    </div>
                    <label class="toggle-switch">
                        <input 
                            type="checkbox" 
                            class="layer-toggle"
                            data-layer-id="${layerId}"
                            ${layer.enabled ? 'checked' : ''}
                        >
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="layer-description">${layer.description}</div>
            `;
            
            layersList.appendChild(layerItem);
        }
        
        // Ajouter les événements
        this.setupLayerEvents();
    }
    
    /**
     * Configuration des événements pour les couches
     */
    setupLayerEvents() {
        // Toggle ON/OFF des couches
        document.querySelectorAll('.layer-toggle').forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                const layerId = e.target.dataset.layerId;
                this.toggleLayer(layerId, e.target.checked);
            });
        });
        
        // Clic sur le nom de la couche pour ouvrir les détails
        document.querySelectorAll('.layer-info').forEach(info => {
            info.addEventListener('click', (e) => {
                const layerId = e.currentTarget.dataset.layerId;
                this.showLayerDetails(layerId);
            });
        });
    }
    
    /**
     * Activation/désactivation d'une couche
     */
    async toggleLayer(layerId, enabled) {
        this.layers[layerId].enabled = enabled;
        
        if (enabled) {
            await this.loadLayerData(layerId);
        } else {
            this.hideLayerData(layerId);
        }
    }
    
    /**
     * Chargement des données d'une couche
     */
    async loadLayerData(layerId) {
        try {
            const url = this.config.apiEndpoints.layerData.replace('{id}', layerId);
            const response = await fetch(url);
            const data = await response.json();
            
            // Supprimer l'ancienne couche si elle existe
            if (this.layerGroups[layerId]) {
                this.map.removeLayer(this.layerGroups[layerId]);
            }
            
            // Créer un nouveau groupe de couches
            this.layerGroups[layerId] = L.layerGroup();
            
            const layer = this.layers[layerId];
            const config = layer.config;
            
            // Afficher les données selon le type de couche
            if (layer.type === 'geojson' || layer.type === 'polygon') {
                L.geoJSON(data, {
                    style: {
                        color: config.color || '#1a73e8',
                        weight: config.weight || 2,
                        opacity: config.opacity || 0.7,
                        fillColor: config.fillColor || config.color,
                        fillOpacity: config.fillOpacity || 0.3
                    },
                    onEachFeature: (feature, layer) => {
                        if (feature.properties) {
                            const props = feature.properties;
                            let popupContent = '<div class="popup-content">';
                            for (const key in props) {
                                popupContent += `<p><strong>${key}:</strong> ${props[key]}</p>`;
                            }
                            popupContent += '</div>';
                            layer.bindPopup(popupContent);
                        }
                    }
                }).addTo(this.layerGroups[layerId]);
            } else if (layer.type === 'markers') {
                data.features.forEach(feature => {
                    const coords = feature.geometry.coordinates;
                    const marker = L.marker([coords[1], coords[0]]);
                    
                    if (feature.properties) {
                        const props = feature.properties;
                        let popupContent = '<div class="popup-content">';
                        if (props.name) {
                            popupContent += `<h4>${props.name}</h4>`;
                        }
                        for (const key in props) {
                            if (key !== 'name') {
                                popupContent += `<p><strong>${key}:</strong> ${props[key]}</p>`;
                            }
                        }
                        popupContent += '</div>';
                        marker.bindPopup(popupContent);
                    }
                    
                    marker.addTo(this.layerGroups[layerId]);
                });
            }
            
            // Ajouter le groupe de couches à la carte
            this.layerGroups[layerId].addTo(this.map);
            
            console.log(`Couche ${layerId} chargée`);
            
        } catch (error) {
            console.error(`Erreur lors du chargement de la couche ${layerId}:`, error);
        }
    }
    
    /**
     * Masquage des données d'une couche
     */
    hideLayerData(layerId) {
        if (this.layerGroups[layerId]) {
            this.map.removeLayer(this.layerGroups[layerId]);
            console.log(`Couche ${layerId} masquée`);
        }
    }
    
    /**
     * Affichage du menu détaillé d'une couche
     */
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
            
            // Section Paramètres
            if (config.parameters && config.parameters.length > 0) {
                content += '<div class="detail-section"><h4>Paramètres visuels</h4>';
                config.parameters.forEach(param => {
                    content += this.renderParameter(param);
                });
                content += '</div>';
            }
            
            // Section Filtres
            if (config.filters && config.filters.length > 0) {
                content += '<div class="detail-section"><h4>Filtres</h4>';
                config.filters.forEach(filter => {
                    content += this.renderParameter(filter);
                });
                content += '</div>';
            }
            
            // Section Informations
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
            
            // Ajouter les événements pour les contrôles
            this.setupDetailEvents(layerId);
            
        } catch (error) {
            console.error(`Erreur lors du chargement des détails de la couche ${layerId}:`, error);
        }
    }
    
    /**
     * Rendu d'un paramètre dans le menu détaillé
     */
    renderParameter(param) {
        let html = `<div class="parameter-item">`;
        html += `<label class="parameter-label">${param.label}</label>`;
        
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
                        <input type="checkbox" class="parameter-control" data-param="${param.name}" 
                            value="${opt}" ${checked ? 'checked' : ''}>
                        ${opt}
                    </label>`;
                });
                break;
        }
        
        html += `</div>`;
        return html;
    }
    
    /**
     * Configuration des événements pour les contrôles du menu détaillé
     */
    setupDetailEvents(layerId) {
        document.querySelectorAll('#detailContent .parameter-control').forEach(control => {
            control.addEventListener('change', (e) => {
                this.updateLayerParameter(layerId, e.target);
            });
            
            // Pour les range, mettre à jour la valeur affichée
            if (control.type === 'range') {
                control.addEventListener('input', (e) => {
                    const valueSpan = e.target.nextElementSibling;
                    if (valueSpan) {
                        valueSpan.textContent = e.target.value;
                    }
                });
            }
        });
    }
    
    /**
     * Mise à jour d'un paramètre de couche
     */
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
        
        // Mettre à jour la configuration de la couche
        this.layers[layerId].config[paramName] = value;
        
        // Recharger les données de la couche avec les nouveaux paramètres
        if (this.layers[layerId].enabled) {
            this.loadLayerData(layerId);
        }
        
        console.log(`Paramètre ${paramName} de la couche ${layerId} mis à jour:`, value);
    }
    
    /**
     * Configuration des événements globaux
     */
    setupEventListeners() {
        // Recherche
        const searchButton = document.getElementById('searchButton');
        const searchInput = document.getElementById('searchInput');
        
        searchButton.addEventListener('click', () => this.performSearch());
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
        
        // Fermeture du menu détaillé
        document.getElementById('closeDetail').addEventListener('click', () => {
            document.getElementById('detailMenu').classList.add('hidden');
            this.currentDetailLayer = null;
        });
        
        // Réinitialisation de la vue
        document.getElementById('resetView').addEventListener('click', () => {
            this.map.setView(this.config.defaultCenter, this.config.defaultZoom);
        });
        
        // Plein écran
        document.getElementById('toggleFullscreen').addEventListener('click', () => {
            this.toggleFullscreen();
        });
    }
    
    /**
     * Effectuer une recherche de lieu
     */
    async performSearch() {
        const searchInput = document.getElementById('searchInput');
        const query = searchInput.value.trim();
        
        if (!query) return;
        
        const searchResults = document.getElementById('searchResults');
        searchResults.innerHTML = '<div class="loading">Recherche en cours...</div>';
        searchResults.classList.remove('hidden');
        
        try {
            const response = await fetch(`${this.config.apiEndpoints.search}?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.success && data.result) {
                const result = data.result;
                
                // Recentrer la carte
                this.map.setView([result.lat, result.lng], result.zoom || this.config.defaultZoom);
                
                // Ajouter un marqueur temporaire
                if (this.searchMarker) {
                    this.map.removeLayer(this.searchMarker);
                }
                
                this.searchMarker = L.marker([result.lat, result.lng])
                    .addTo(this.map)
                    .bindPopup(`<strong>${result.name}</strong>`)
                    .openPopup();
                
                searchResults.innerHTML = `<div class="success">📍 ${result.name}</div>`;
                
                // Masquer les résultats après 3 secondes
                setTimeout(() => {
                    searchResults.classList.add('hidden');
                }, 3000);
                
            } else {
                searchResults.innerHTML = `<div class="error">${data.message || 'Aucun résultat trouvé'}</div>`;
            }
            
        } catch (error) {
            console.error('Erreur lors de la recherche:', error);
            searchResults.innerHTML = '<div class="error">Erreur lors de la recherche</div>';
        }
    }
    
    /**
     * Basculer le mode plein écran
     */
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
    
    /**
     * Afficher un message d'erreur
     */
    showError(message) {
        const layersList = document.getElementById('layersList');
        layersList.innerHTML = `<div class="error">${message}</div>`;
    }
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    const mapController = new MapController(MAP_CONFIG);
    
    // Exposer globalement pour le débogage
    window.mapController = mapController;
    
    console.log('Application de carte initialisée');
});
