/**
 * Gestionnaire de carte interactive avec Leaflet et OpenStreetMap
 */

class MapController {
    constructor(config) {
        this.config = config;
        this.map = null;
        this.layers = {};
        this.layerGroups = {};
        this.currentDetailLayer = null;
        this.baseTileLayer = null;
        
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
        this.map = L.map('map').setView(
            this.config.defaultCenter,
            this.config.defaultZoom
        );
        
        this.baseTileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        // Recharger les données quand la carte bouge
        this.map.on('moveend', () => {
            this.reloadVisibleLayers();
        });
    }
    
    /**
     * Recharger les couches visibles avec la nouvelle bbox
     */
    reloadVisibleLayers() {
        for (const layerId in this.layers) {
            if (this.layers[layerId].enabled && layerId !== 'background') {
                this.loadLayerData(layerId);
            }
        }
    }
    
    /**
     * Obtenir la bounding box actuelle de la carte
     */
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
    
    /**
     * Chargement de la liste des couches depuis l'API
     */
    async loadLayers() {
        try {
            console.log('📋 Chargement des couches...');
            const response = await fetch(this.config.apiEndpoints.layers);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log('✅ Couches chargées:', data);
            
            this.layers = {};
            data.layers.forEach(layer => {
                this.layers[layer.id] = layer;
            });
            
            this.renderLayersList();
            
            // Charger les données des couches activées par défaut
            for (const layerId in this.layers) {
                if (this.layers[layerId].enabled && layerId !== 'background') {
                    console.log(`🔄 Chargement initial de la couche: ${layerId}`);
                    await this.loadLayerData(layerId);
                }
            }
            
        } catch (error) {
            console.error('❌ Erreur lors du chargement des couches:', error);
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
            
            // Afficher le toggle seulement si hasToggle n'est pas false
            const toggleHTML = layer.hasToggle !== false ? `
                <label class="toggle-switch">
                    <input 
                        type="checkbox" 
                        class="layer-toggle"
                        data-layer-id="${layerId}"
                        ${layer.enabled ? 'checked' : ''}
                    >
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
        console.log(`🗺️ Chargement des données pour: ${layerId}`);
        
        try {
            // Construire l'URL avec la bounding box
            const bounds = this.getCurrentBounds();
            const params = new URLSearchParams({
                minLng: bounds.minLng,
                minLat: bounds.minLat,
                maxLng: bounds.maxLng,
                maxLat: bounds.maxLat,
                zoom: bounds.zoom
            });
            
            // Ajouter les filtres si ils existent
            const layer = this.layers[layerId];
            if (layer.filters) {
                layer.filters.forEach(filter => {
                    if (filter.value && filter.value !== 'Tous' && filter.value !== 'Toutes') {
                        params.append(filter.name, filter.value);
                    }
                });
            }
            
            const url = `${this.config.apiEndpoints.layerData.replace('{id}', layerId)}?${params}`;
            console.log(`📡 Requête API: ${url}`);
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log(`✅ Données reçues pour ${layerId}:`, data);
            
            if (data.error) {
                console.warn(`⚠️ Erreur API pour ${layerId}:`, data.error);
                return;
            }
            
            // Supprimer l'ancienne couche si elle existe
            if (this.layerGroups[layerId]) {
                this.map.removeLayer(this.layerGroups[layerId]);
            }
            
            // Créer un nouveau groupe de couches
            this.layerGroups[layerId] = L.layerGroup();
            
            const config = layer.config;
            
            // Afficher les données selon le type de couche
            if (data.features && data.features.length > 0) {
                console.log(`📍 Affichage de ${data.features.length} features pour ${layerId}`);
                
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
                                layer.bindPopup(this.createPopupContent(feature.properties));
                            }
                        }
                    }).addTo(this.layerGroups[layerId]);
                    
                } else if (layer.type === 'markers') {
                    data.features.forEach(feature => {
                        const coords = feature.geometry.coordinates;
                        const marker = L.marker([coords[1], coords[0]]);
                        
                        if (feature.properties) {
                            marker.bindPopup(this.createPopupContent(feature.properties));
                        }
                        
                        marker.addTo(this.layerGroups[layerId]);
                    });
                }
                
                // Ajouter le groupe de couches à la carte
                this.layerGroups[layerId].addTo(this.map);
                console.log(`✅ Couche ${layerId} affichée avec succès`);
            } else {
                console.log(`ℹ️ Aucune donnée à afficher pour ${layerId}`);
            }
            
        } catch (error) {
            console.error(`❌ Erreur chargement couche ${layerId}:`, error);
            alert(`Erreur lors du chargement de la couche ${layerId}: ${error.message}`);
        }
    }
    
    /**
     * Créer le contenu HTML d'une popup
     */
    createPopupContent(properties) {
        let content = '<div class="popup-content">';
        
        // Titre si nom disponible
        if (properties.nom || properties.name) {
            content += `<h4>${properties.nom || properties.name}</h4>`;
        }
        
        // Autres propriétés
        for (const key in properties) {
            if (key !== 'nom' && key !== 'name' && key !== 'feature_type') {
                const label = key.charAt(0).toUpperCase() + key.slice(1);
                content += `<p><strong>${label}:</strong> ${properties[key]}</p>`;
            }
        }
        
        content += '</div>';
        return content;
    }
    
    /**
     * Masquage des données d'une couche
     */
    hideLayerData(layerId) {
        if (this.layerGroups[layerId]) {
            this.map.removeLayer(this.layerGroups[layerId]);
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
            // Erreur silencieuse
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
        
        // Si c'est un filtre, le sauvegarder aussi
        const layer = this.layers[layerId];
        if (layer.filters) {
            const filter = layer.filters.find(f => f.name === paramName);
            if (filter) {
                filter.value = value;
            }
        }
        
        // Cas spécial pour la couche background
        if (layerId === 'background') {
            if (paramName === 'variant') {
                this.changeBaseTiles(value);
            } else if (paramName === 'opacity') {
                if (this.baseTileLayer) {
                    this.baseTileLayer.setOpacity(value);
                }
            }
        } else {
            // Recharger les données de la couche avec les nouveaux paramètres
            if (this.layers[layerId].enabled) {
                this.loadLayerData(layerId);
            }
        }
    }
    
    /**
     * Obtenir la configuration des tuiles selon le type
     */
    getTileConfig(variant) {
        const configs = {
            'Plan': {
                url: 'https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png',
                attribution: '© OpenStreetMap France | © OpenStreetMap contributors',
                maxZoom: 20
            },
            'Sombre': {
                url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                attribution: '© OpenStreetMap contributors © CARTO',
                maxZoom: 19,
                subdomains: 'abcd'
            },
            'Satellite': {
                url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attribution: 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
                maxZoom: 19
            },
            'Topographique': {
                url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
                attribution: 'Map data: © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap (CC-BY-SA)',
                maxZoom: 17
            }
        };
        
        return configs[variant] || configs['Plan'];
    }
    
    /**
     * Changer les tuiles de base de la carte
     */
    changeBaseTiles(variant) {
        // Supprimer l'ancienne couche de tuiles
        if (this.baseTileLayer) {
            this.map.removeLayer(this.baseTileLayer);
        }
        
        // Obtenir la configuration du nouveau type de tuiles
        const config = this.getTileConfig(variant);
        
        // Créer et ajouter la nouvelle couche de tuiles
        this.baseTileLayer = L.tileLayer(config.url, {
            attribution: config.attribution,
            maxZoom: config.maxZoom,
            subdomains: config.subdomains || 'abc',
            opacity: this.layers['background']?.config?.opacity || 1.0
        }).addTo(this.map);
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
        
        // Autocomplétion : écouter les saisies dans le champ de recherche
        let searchTimeout = null;
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            // Annuler le délai précédent
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            
            // Si la requête est trop courte, masquer les suggestions
            if (query.length < 3) {
                this.hideSuggestions();
                return;
            }
            
            // Attendre 300ms après la dernière frappe avant de chercher
            searchTimeout = setTimeout(() => {
                this.fetchSuggestions(query);
            }, 300);
        });
        
        // Fermeture des suggestions en cliquant ailleurs
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-section')) {
                this.hideSuggestions();
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
     * Récupérer les suggestions de recherche
     */
    async fetchSuggestions(query) {
        try {
            // Attendre un peu pour respecter la politique de Nominatim
            await new Promise(resolve => setTimeout(resolve, 300));
            
            // Utiliser l'API Nominatim pour les suggestions
            const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`;
            
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                return;
            }
            
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
    
    /**
     * Afficher les suggestions
     */
    displaySuggestions(suggestions) {
        const searchResults = document.getElementById('searchResults');
        searchResults.innerHTML = '';
        
        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.innerHTML = `
                <div class="suggestion-icon">📍</div>
                <div class="suggestion-text">
                    <div class="suggestion-name">${this.highlightMatch(suggestion.display_name)}</div>
                    <div class="suggestion-type">${this.getSuggestionType(suggestion)}</div>
                </div>
            `;
            
            item.addEventListener('click', () => {
                this.selectSuggestion(suggestion);
            });
            
            searchResults.appendChild(item);
        });
        
        searchResults.classList.remove('hidden');
    }
    
    /**
     * Masquer les suggestions
     */
    hideSuggestions() {
        const searchResults = document.getElementById('searchResults');
        searchResults.classList.add('hidden');
        searchResults.innerHTML = '';
    }
    
    /**
     * Sélectionner une suggestion
     */
    selectSuggestion(suggestion) {
        const searchInput = document.getElementById('searchInput');
        searchInput.value = suggestion.display_name;
        
        const lat = parseFloat(suggestion.lat);
        const lng = parseFloat(suggestion.lon);
        
        // Recentrer la carte
        this.map.setView([lat, lng], 15);
        
        // Ajouter un marqueur
        if (this.searchMarker) {
            this.map.removeLayer(this.searchMarker);
        }
        
        this.searchMarker = L.marker([lat, lng])
            .addTo(this.map)
            .bindPopup(`<strong>${suggestion.display_name}</strong>`)
            .openPopup();
        
        // Masquer les suggestions
        this.hideSuggestions();
    }
    
    /**
     * Mettre en évidence la correspondance dans le texte
     */
    highlightMatch(text) {
        // Pour l'instant, retourner le texte tel quel
        // On pourrait améliorer en mettant en évidence la requête
        return text;
    }
    
    /**
     * Obtenir le type de suggestion
     */
    getSuggestionType(suggestion) {
        if (suggestion.type) {
            const types = {
                'city': '🏙️ Ville',
                'town': '🏘️ Ville',
                'village': '🏡 Village',
                'hamlet': '🏠 Hameau',
                'administrative': '🏛️ Administratif',
                'road': '🛣️ Route',
                'house': '🏠 Adresse',
                'building': '🏢 Bâtiment',
                'suburb': '🏘️ Quartier',
                'neighbourhood': '🏘️ Quartier'
            };
            return types[suggestion.type] || suggestion.type;
        }
        return suggestion.class || '';
    }
    
    /**
     * Effectuer une recherche de lieu
     */
    async performSearch() {
        const searchInput = document.getElementById('searchInput');
        const query = searchInput.value.trim();
        
        if (!query) {
            return;
        }
        
        const searchResults = document.getElementById('searchResults');
        searchResults.innerHTML = '<div class="loading">Recherche en cours...</div>';
        searchResults.classList.remove('hidden');
        
        try {
            // Attendre 1 seconde pour respecter la politique de Nominatim
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Utiliser l'API Nominatim d'OpenStreetMap
            const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`;
            
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data && data.length > 0) {
                const result = data[0];
                
                const lat = parseFloat(result.lat);
                const lng = parseFloat(result.lon);
                
                // Vérifier que les coordonnées sont valides
                if (isNaN(lat) || isNaN(lng)) {
                    throw new Error('Coordonnées invalides');
                }
                
                // Recentrer la carte
                this.map.setView([lat, lng], 13);
                
                // Ajouter un marqueur temporaire
                if (this.searchMarker) {
                    this.map.removeLayer(this.searchMarker);
                }
                
                this.searchMarker = L.marker([lat, lng])
                    .addTo(this.map)
                    .bindPopup(`<strong>${result.display_name}</strong>`)
                    .openPopup();
                
                searchResults.innerHTML = `<div class="success">📍 ${result.display_name}</div>`;
                
                // Masquer les résultats après 3 secondes
                setTimeout(() => {
                    searchResults.classList.add('hidden');
                }, 3000);
                
            } else {
                searchResults.innerHTML = '<div class="error">Aucun résultat trouvé</div>';
                setTimeout(() => {
                    searchResults.classList.add('hidden');
                }, 3000);
            }
            
        } catch (error) {
            searchResults.innerHTML = `<div class="error">Erreur lors de la recherche</div>`;
            setTimeout(() => {
                searchResults.classList.add('hidden');
            }, 3000);
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
    window.mapController = mapController;
});
