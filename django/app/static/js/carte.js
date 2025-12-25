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
        
        // Cache spatial pour les données
        this.dataCache = {};
        this.cacheExpiry = 30 * 60 * 1000; // 30 minutes (augmenté pour éviter les pertes)
        
        // Debounce pour éviter les requêtes excessives
        this.moveTimeout = null;
        this.debounceDelay = 300; // ms
        
        // Flag pour savoir si un chargement est en cours (évite les effacements)
        this.isLoading = {};
        
        // Suivi des requêtes en cours pour éviter les doublons
        this.pendingRequests = new Set();
        
        // Dernière bbox chargée par couche (pour éviter les recharges inutiles)
        this.lastLoadedBounds = {};
        
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
        
        // Recharger les données quand la carte bouge (avec debounce)
        this.map.on('moveend', () => {
            this.debouncedReload();
        });
    }
    
    /**
     * Debounce du rechargement pour éviter les requêtes excessives
     */
    debouncedReload() {
        if (this.moveTimeout) {
            clearTimeout(this.moveTimeout);
        }
        this.moveTimeout = setTimeout(() => {
            this.reloadVisibleLayers();
        }, this.debounceDelay);
    }
    
    /**
     * Recharger les couches visibles avec la nouvelle bbox
     * Utilise des requêtes parallèles et évite les rechargements inutiles
     */
    reloadVisibleLayers() {
        const currentBounds = this.getCurrentBounds();
        const layersToLoad = [];
        
        for (const layerId in this.layers) {
            if (this.layers[layerId].enabled && layerId !== 'background') {
                // Vérifier si on a besoin de recharger cette couche
                if (this.needsReload(layerId, currentBounds)) {
                    layersToLoad.push(layerId);
                }
            }
        }
        
        if (layersToLoad.length === 0) {
            console.log('📍 Aucune couche à recharger');
            return;
        }
        
        console.log(`🔄 Rechargement de ${layersToLoad.length} couches: ${layersToLoad.join(', ')}`);
        
        // Charger toutes les couches en parallèle
        Promise.all(layersToLoad.map(layerId => this.loadLayerData(layerId)));
    }
    
    /**
     * Vérifier si une couche doit être rechargée
     * OPTIMISÉ: Ne force plus le rechargement au changement de zoom pour éviter les effacements
     */
    needsReload(layerId, currentBounds) {
        const lastBounds = this.lastLoadedBounds[layerId];
        if (!lastBounds) return true;
        
        // Ne PAS forcer le rechargement au changement de zoom
        // Les données existantes restent valides, on charge juste les nouvelles zones
        // Cela évite l'effacement des données lors du zoom
        
        // Recharger si la vue actuelle sort de la zone précédemment chargée
        // avec une marge de 10% vers l'intérieur (réduite pour moins de rechargements)
        const margin = 0.1;
        const lastWidth = lastBounds.maxLng - lastBounds.minLng;
        const lastHeight = lastBounds.maxLat - lastBounds.minLat;
        
        // Zone "safe" = zone chargée réduite de la marge
        const safeZone = {
            minLng: lastBounds.minLng + lastWidth * margin,
            maxLng: lastBounds.maxLng - lastWidth * margin,
            minLat: lastBounds.minLat + lastHeight * margin,
            maxLat: lastBounds.maxLat - lastHeight * margin
        };
        
        // Recharger si la vue actuelle dépasse la zone safe
        const needsReload = currentBounds.minLng < safeZone.minLng ||
                           currentBounds.maxLng > safeZone.maxLng ||
                           currentBounds.minLat < safeZone.minLat ||
                           currentBounds.maxLat > safeZone.maxLat;
        
        if (needsReload) {
            console.log(`🔄 ${layerId}: Sortie de la zone safe, rechargement nécessaire`);
        }
        
        return needsReload;
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
     * Générer une clé de cache unique pour une requête
     */
    getCacheKey(layerId, filters) {
        let key = layerId;
        
        if (filters && Object.keys(filters).length > 0) {
            const filterStr = Object.entries(filters).sort().map(([k, v]) => `${k}=${v}`).join('_');
            key += `_${filterStr}`;
        }
        
        return key;
    }
    
    /**
     * Obtenir les données du cache pour une couche
     */
    getFromCache(cacheKey) {
        const cached = this.dataCache[cacheKey];
        if (cached && (Date.now() - cached.timestamp) < this.cacheExpiry) {
            return cached;
        }
        return null;
    }
    
    /**
     * Ajouter des features au cache d'une couche (fusion automatique)
     */
    addToCache(cacheKey, newFeatures, bounds) {
        const cached = this.dataCache[cacheKey];
        const now = Date.now();
        
        if (!cached || (now - cached.timestamp) >= this.cacheExpiry) {
            // Nouveau cache ou expiré
            this.dataCache[cacheKey] = {
                features: new Map(),
                bounds: bounds,
                timestamp: now
            };
        }
        
        const cache = this.dataCache[cacheKey];
        let addedCount = 0;
        
        // Ajouter les nouvelles features (avec déduplication par ID)
        for (const feature of newFeatures) {
            const featureId = this.getFeatureId(feature);
            if (!cache.features.has(featureId)) {
                cache.features.set(featureId, feature);
                addedCount++;
            }
        }
        
        // Étendre les bounds du cache
        if (bounds) {
            cache.bounds = this.mergeBounds(cache.bounds, bounds);
        }
        cache.timestamp = now;
        
        console.log(`💾 Cache ${cacheKey}: +${addedCount} features (total: ${cache.features.size})`);
    }
    
    /**
     * Obtenir un ID unique pour une feature
     */
    getFeatureId(feature) {
        if (feature.properties?.id) {
            return `${feature.properties.feature_type || 'f'}_${feature.properties.id}`;
        }
        // Fallback sur les coordonnées
        const coords = feature.geometry?.coordinates;
        if (coords) {
            return JSON.stringify(coords).substring(0, 100);
        }
        return Math.random().toString(36);
    }
    
    /**
     * Fusionner deux bounding boxes
     */
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
    
    /**
     * Obtenir toutes les features en cache pour une couche
     * OPTIMISÉ: Retourne les données même si expirées (pour éviter les effacements)
     * Le rechargement se fera en arrière-plan
     */
    getCachedFeatures(cacheKey) {
        const cached = this.dataCache[cacheKey];
        if (cached && cached.features) {
            // Retourner les données même si expirées
            // Mieux vaut des données légèrement anciennes que pas de données
            const isExpired = (Date.now() - cached.timestamp) >= this.cacheExpiry;
            if (isExpired) {
                console.log(`⚠️ Cache ${cacheKey} expiré mais utilisé pour éviter l'effacement`);
            }
            return Array.from(cached.features.values());
        }
        return [];
    }
    
    /**
     * Vérifier si le cache est expiré (pour déclencher un rechargement en arrière-plan)
     */
    isCacheExpired(cacheKey) {
        const cached = this.dataCache[cacheKey];
        if (!cached) return true;
        return (Date.now() - cached.timestamp) >= this.cacheExpiry;
    }
    
    /**
     * Vider le cache d'une couche spécifique
     * OPTIMISÉ: Option pour garder les données affichées
     */
    clearLayerCache(layerId, keepDisplayed = false) {
        // Supprimer les entrées de cache
        const keysToRemove = Object.keys(this.dataCache).filter(key => 
            key === layerId || key.startsWith(layerId + '_')
        );
        keysToRemove.forEach(key => delete this.dataCache[key]);
        
        // Réinitialiser les bounds chargées
        delete this.lastLoadedBounds[layerId];
        
        // NE PAS supprimer les couches affichées si keepDisplayed est true
        if (!keepDisplayed && this.layerGroups[layerId]) {
            // La couche sera recréée au prochain chargement
        }
        
        console.log(`🗑️ Cache vidé pour: ${layerId}`);
    }
    
    /**
     * Chargement des données d'une couche avec cache intelligent
     * OPTIMISÉ: Ne supprime plus les données avant d'avoir les nouvelles
     */
    async loadLayerData(layerId) {
        const layer = this.layers[layerId];
        const bounds = this.getCurrentBounds();
        
        // Collecter les filtres actifs
        const activeFilters = {};
        if (layer.filters) {
            layer.filters.forEach(filter => {
                if (filter.value && filter.value !== 'Tous' && filter.value !== 'Toutes') {
                    activeFilters[filter.name] = filter.value;
                }
            });
        }
        
        const cacheKey = this.getCacheKey(layerId, activeFilters);
        
        // Éviter les requêtes en double
        if (this.pendingRequests.has(cacheKey)) {
            console.log(`⏳ Requête déjà en cours pour: ${layerId}`);
            return;
        }
        
        // Marquer le chargement en cours
        this.isLoading[layerId] = true;
        
        try {
            this.pendingRequests.add(cacheKey);
            
            // Élargir la bbox pour pré-charger les données environnantes
            const expandedBounds = this.expandBounds(bounds, 0.5);
            
            // Construire les paramètres de la requête
            const params = new URLSearchParams({
                minLng: expandedBounds.minLng,
                minLat: expandedBounds.minLat,
                maxLng: expandedBounds.maxLng,
                maxLat: expandedBounds.maxLat,
                zoom: bounds.zoom
            });
            
            // Ajouter les filtres
            Object.entries(activeFilters).forEach(([name, value]) => {
                params.append(name, value);
            });
            
            const url = `${this.config.apiEndpoints.layerData.replace('{id}', layerId)}?${params}`;
            console.log(`📡 ${layerId}: Requête API...`);
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                console.warn(`⚠️ Erreur API pour ${layerId}:`, data.error);
                return;
            }
            
            // Ajouter les nouvelles features au cache
            if (data.features && data.features.length > 0) {
                this.addToCache(cacheKey, data.features, expandedBounds);
                // Mémoriser la bbox chargée (fusionnée avec l'ancienne)
                this.lastLoadedBounds[layerId] = this.mergeBounds(
                    this.lastLoadedBounds[layerId], 
                    expandedBounds
                );
            }
            
            // Afficher toutes les features en cache
            this.displayLayerFeatures(layerId, cacheKey);
            
        } catch (error) {
            console.error(`❌ Erreur chargement ${layerId}:`, error);
            // EN CAS D'ERREUR: Réafficher les données du cache existant
            // pour ne pas perdre l'affichage actuel
            const existingFeatures = this.getCachedFeatures(cacheKey);
            if (existingFeatures.length > 0) {
                console.log(`♻️ ${layerId}: Réaffichage des données en cache après erreur`);
                this.displayLayerFeatures(layerId, cacheKey);
            }
        } finally {
            this.pendingRequests.delete(cacheKey);
            this.isLoading[layerId] = false;
        }
    }
    
    /**
     * Élargir une bounding box d'un certain pourcentage
     */
    expandBounds(bounds, percent) {
        const lngRange = bounds.maxLng - bounds.minLng;
        const latRange = bounds.maxLat - bounds.minLat;
        const lngExpand = lngRange * percent;
        const latExpand = latRange * percent;
        
        return {
            minLng: bounds.minLng - lngExpand,
            minLat: bounds.minLat - latExpand,
            maxLng: bounds.maxLng + lngExpand,
            maxLat: bounds.maxLat + latExpand,
            zoom: bounds.zoom
        };
    }
    
    /**
     * Afficher les features d'une couche depuis le cache
     * OPTIMISÉ: Mise à jour atomique pour éviter le flash d'effacement
     */
    displayLayerFeatures(layerId, cacheKey) {
        const layer = this.layers[layerId];
        const config = layer.config;
        const features = this.getCachedFeatures(cacheKey);
        
        if (features.length === 0) {
            console.log(`ℹ️ Aucune donnée pour ${layerId}`);
            // NE PAS supprimer la couche existante si pas de nouvelles données
            return;
        }
        
        // Filtrer les features avec géométrie valide
        const validFeatures = features.filter(f => {
            if (!f.geometry || !f.geometry.coordinates) return false;
            const coords = f.geometry.coordinates;
            // Vérifier que les coordonnées sont des nombres valides
            if (f.geometry.type === 'Point') {
                return Array.isArray(coords) && 
                       coords.length >= 2 && 
                       isFinite(coords[0]) && 
                       isFinite(coords[1]);
            }
            // Pour les polygones et lignes, vérifier la structure
            if (f.geometry.type === 'LineString' || f.geometry.type === 'Polygon') {
                return Array.isArray(coords) && coords.length > 0;
            }
            return true;
        });
        
        if (validFeatures.length === 0) {
            console.log(`⚠️ ${layerId}: Aucune feature valide`);
            // NE PAS supprimer la couche existante
            return;
        }
        
        if (validFeatures.length !== features.length) {
            console.warn(`⚠️ ${layerId}: ${features.length - validFeatures.length} features ignorées (géométrie invalide)`);
        }
        
        // Sauvegarder l'ancienne couche pour suppression APRÈS l'ajout de la nouvelle
        const oldLayerGroup = this.layerGroups[layerId];
        
        // Créer un nouveau groupe de couches
        this.layerGroups[layerId] = L.layerGroup();
        
        const displayData = {
            type: 'FeatureCollection',
            features: validFeatures
        };
        
        console.log(`📍 ${layerId}: Affichage de ${validFeatures.length} features`);
        
        if (layer.type === 'geojson' || layer.type === 'polygon') {
            L.geoJSON(displayData, {
                style: {
                    color: config.color || '#1a73e8',
                    weight: config.weight || 2,
                    opacity: config.opacity || 0.7,
                    fillColor: config.fillColor || config.color,
                    fillOpacity: config.fillOpacity || 0.3
                },
                onEachFeature: (feature, layerObj) => {
                    if (feature.properties) {
                        layerObj.bindPopup(this.createPopupContent(feature.properties));
                    }
                }
            }).addTo(this.layerGroups[layerId]);
            
        } else if (layer.type === 'markers') {
            // Utiliser le clustering pour les marqueurs si beaucoup de points
            if (validFeatures.length > 100 && typeof L.markerClusterGroup !== 'undefined') {
                const markers = L.markerClusterGroup();
                validFeatures.forEach(feature => {
                    const coords = feature.geometry.coordinates;
                    const marker = L.marker([coords[1], coords[0]]);
                    if (feature.properties) {
                        marker.bindPopup(this.createPopupContent(feature.properties));
                    }
                    markers.addLayer(marker);
                });
                this.layerGroups[layerId].addLayer(markers);
            } else {
                validFeatures.forEach(feature => {
                    const coords = feature.geometry.coordinates;
                    const marker = L.marker([coords[1], coords[0]]);
                    if (feature.properties) {
                        marker.bindPopup(this.createPopupContent(feature.properties));
                    }
                    marker.addTo(this.layerGroups[layerId]);
                });
            }
        }
        
        // Ajouter le groupe à la carte AVANT de supprimer l'ancien
        // Cela évite le flash d'effacement
        this.layerGroups[layerId].addTo(this.map);
        
        // Supprimer l'ancienne couche APRÈS avoir ajouté la nouvelle
        if (oldLayerGroup) {
            this.map.removeLayer(oldLayerGroup);
        }
        
        console.log(`✅ ${layerId}: Affiché avec succès (${validFeatures.length} features)`);
    }
    
    /**
     * Créer le contenu HTML d'une popup
     */
    createPopupContent(properties) {
        let content = '<div class="popup-content">';
        
        // Labels en français pour les propriétés
        const labels = {
            nom: 'Nom',
            name: 'Nom',
            type: 'Type',
            subtype: 'Sous-type',
            description: 'Description',
            type_transport: 'Transport',
            nb_lignes: 'Lignes desservies',
            capacity: 'Capacité'
        };
        
        // Propriétés à ignorer dans l'affichage
        let ignoreKeys = ['feature_type', 'id'];
        
        // Pour les POI, ignorer aussi le type
        if (properties.feature_type === 'poi') {
            ignoreKeys.push('type');
        }
        
        // Titre si nom disponible
        if (properties.nom || properties.name) {
            content += `<h4>${properties.nom || properties.name}</h4>`;
        }
        
        // Autres propriétés
        for (const key in properties) {
            if (!ignoreKeys.includes(key) && key !== 'nom' && key !== 'name') {
                const value = properties[key];
                // Ne pas afficher les valeurs nulles ou vides
                if (value !== null && value !== undefined && value !== '') {
                    const label = labels[key] || key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
                    content += `<p><strong>${label}:</strong> ${value}</p>`;
                }
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
                // Vider le cache de cette couche quand un filtre change
                // mais garder l'affichage actuel jusqu'au rechargement
                this.clearLayerCache(layerId, true);
            }
        }
        
        // Cas spécial pour la couche background
        if (layerId === 'background') {
            if (paramName === 'variant') {
                this.changeBaseTiles(value);
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
            subdomains: config.subdomains || 'abc'
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
