/**
 * Gestionnaire pour la page d'extraction de données enrichies
 */

class EnhancedDataExtractor {
    constructor() {
        this.map = null;
        this.polygon = null;
        this.drawingMode = false;
        this.points = [];
        this.markers = [];
        this.polyline = null;
        this.lastResult = null;
        this.init();
    }

    /**
     * Initialisation
     */
    init() {
        this.initMap();
        this.setupEventListeners();
    }

    /**
     * Initialisation de la carte Leaflet
     */
    initMap() {
        // Centrer sur la France par défaut
        this.map = L.map('map').setView([46.603354, 1.888334], 6);

        // Ajouter les tuiles OpenStreetMap
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);

        // Désactiver le clic sur la carte par défaut
        this.map.on('click', (e) => {
            if (this.drawingMode) {
                this.addPoint(e.latlng);
            }
        });
    }

    /**
     * Configuration des événements
     */
    setupEventListeners() {
        // Dessiner une zone
        document.getElementById('drawZoneBtn').addEventListener('click', () => {
            this.startDrawing();
        });

        // Effacer la zone
        document.getElementById('clearZoneBtn').addEventListener('click', () => {
            this.clearZone();
        });

        // Bouton d'extraction
        document.getElementById('extractBtn').addEventListener('click', () => {
            this.extractData();
        });

        // Tout sélectionner
        document.getElementById('selectAllBtn').addEventListener('click', () => {
            this.selectAll(true);
        });

        // Tout désélectionner
        document.getElementById('clearAllBtn').addEventListener('click', () => {
            this.selectAll(false);
        });

        // Télécharger le JSON
        document.getElementById('downloadBtn').addEventListener('click', () => {
            this.downloadJSON();
        });

        // Copier l'URL
        document.getElementById('copyUrlBtn').addEventListener('click', () => {
            this.copyURL();
        });
    }

    /**
     * Démarrer le mode dessin
     */
    startDrawing() {
        if (this.drawingMode) {
            return;
        }

        this.clearZone();
        this.drawingMode = true;
        this.points = [];
        this.markers = [];

        document.getElementById('map').style.cursor = 'crosshair';

        const btn = document.getElementById('drawZoneBtn');
        btn.textContent = '✏️ Cliquez pour placer des points...';
        btn.classList.add('active');

        this.showMessage('Cliquez pour placer des points. Cliquez sur le premier point pour fermer le polygone.', 'info');
    }

    /**
     * Ajouter un point au polygone
     */
    addPoint(latlng) {
        if (this.points.length >= 3) {
            const firstPoint = this.points[0];

            const firstPointPx = this.map.latLngToContainerPoint(firstPoint);
            const clickPointPx = this.map.latLngToContainerPoint(latlng);

            const dx = firstPointPx.x - clickPointPx.x;
            const dy = firstPointPx.y - clickPointPx.y;
            const distancePixels = Math.sqrt(dx * dx + dy * dy);

            if (distancePixels < 15) {
                this.closePolygon();
                return;
            }
        }

        this.points.push(latlng);

        const marker = L.circleMarker(latlng, {
            radius: 6,
            fillColor: '#1a73e8',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }).addTo(this.map);

        if (this.points.length === 1) {
            marker.setRadius(8);
            marker.setStyle({ fillColor: '#10b981' });

            marker.on('click', (e) => {
                L.DomEvent.stopPropagation(e);
                if (this.drawingMode && this.points.length >= 3) {
                    this.closePolygon();
                }
            });
        }

        this.markers.push(marker);

        if (this.points.length > 1) {
            if (this.polyline) {
                this.map.removeLayer(this.polyline);
            }

            this.polyline = L.polyline(this.points, {
                color: '#1a73e8',
                weight: 2,
                opacity: 0.7,
                dashArray: '5, 10'
            }).addTo(this.map);
        }

        this.updateZoneDisplay();
    }

    /**
     * Fermer le polygone
     */
    closePolygon() {
        if (this.points.length < 3) {
            this.showMessage('Vous devez placer au moins 3 points', 'error');
            return;
        }

        if (this.polyline) {
            this.map.removeLayer(this.polyline);
            this.polyline = null;
        }

        this.polygon = L.polygon(this.points, {
            color: '#1a73e8',
            weight: 2,
            opacity: 0.8,
            fillColor: '#1a73e8',
            fillOpacity: 0.2
        }).addTo(this.map);

        this.drawingMode = false;
        document.getElementById('map').style.cursor = '';

        const btn = document.getElementById('drawZoneBtn');
        btn.textContent = '🗺️ Redessiner la zone';
        btn.classList.remove('active');

        this.markers.forEach(m => this.map.removeLayer(m));
        this.markers = [];

        this.map.fitBounds(this.polygon.getBounds(), { padding: [50, 50] });

        this.showMessage('Zone définie avec succès!', 'success');
        this.updateZoneDisplay();
    }

    /**
     * Effacer la zone
     */
    clearZone() {
        this.drawingMode = false;
        document.getElementById('map').style.cursor = '';

        if (this.polygon) {
            this.map.removeLayer(this.polygon);
            this.polygon = null;
        }

        if (this.polyline) {
            this.map.removeLayer(this.polyline);
            this.polyline = null;
        }

        this.markers.forEach(m => this.map.removeLayer(m));
        this.markers = [];

        this.points = [];

        const btn = document.getElementById('drawZoneBtn');
        btn.textContent = '🖊️ Dessiner une zone';
        btn.classList.remove('active');

        this.updateZoneDisplay();
    }

    /**
     * Mettre à jour l'affichage de la zone
     */
    updateZoneDisplay() {
        const zoneStatus = document.getElementById('zoneStatus');

        if (this.polygon) {
            const bounds = this.polygon.getBounds();
            const area = L.GeometryUtil.geodesicArea(this.polygon.getLatLngs()[0]);
            const areaKm2 = (area / 1000000).toFixed(2);

            zoneStatus.innerHTML = `
                <div class="zone-defined">
                    <strong>✅ Zone définie</strong>
                    <div class="zone-info-grid">
                        <div><strong>Points:</strong> ${this.points.length}</div>
                        <div><strong>Surface:</strong> ~${areaKm2} km²</div>
                        <div><strong>Lat min:</strong> ${bounds.getSouth().toFixed(6)}</div>
                        <div><strong>Lat max:</strong> ${bounds.getNorth().toFixed(6)}</div>
                        <div><strong>Lng min:</strong> ${bounds.getWest().toFixed(6)}</div>
                        <div><strong>Lng max:</strong> ${bounds.getEast().toFixed(6)}</div>
                    </div>
                </div>
            `;
        } else if (this.drawingMode) {
            zoneStatus.innerHTML = `
                <div class="zone-drawing">
                    <strong>✏️ Dessin en cours</strong>
                    <p>${this.points.length} point(s) placé(s)</p>
                    ${this.points.length >= 3 ? '<p class="hint">Cliquez sur le premier point pour fermer</p>' : ''}
                </div>
            `;
        } else {
            zoneStatus.innerHTML = `
                <div class="zone-undefined">
                    <strong>⚠️ Aucune zone définie</strong>
                    <p>Cliquez sur "Dessiner une zone" pour commencer</p>
                </div>
            `;
        }
    }

    /**
     * Afficher un message
     */
    showMessage(text, type = 'info') {
        const overlay = document.querySelector('.map-overlay');
        const messageDiv = document.createElement('div');
        messageDiv.className = `overlay-message ${type}`;
        messageDiv.textContent = text;

        overlay.appendChild(messageDiv);

        setTimeout(() => {
            messageDiv.remove();
        }, 3000);
    }

    /**
     * Sélectionner / désélectionner toutes les cases
     */
    selectAll(checked) {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = checked);
    }

    /**
     * Construire l'objet GeoJSON de la zone
     */
    getBoundsGeoJSON() {
        if (!this.polygon) {
            throw new Error('Aucune zone définie');
        }

        const latlngs = this.polygon.getLatLngs()[0];
        const coordinates = latlngs.map(ll => [ll.lng, ll.lat]);


        coordinates.push(coordinates[0]);

        return {
            type: 'Polygon',
            coordinates: [coordinates]
        };
    }

    /**
     * Récupérer les paramètres sélectionnés
     */
    getSelectedParams() {
        const params = {};

        const paramNames = [
            'school', 'station', 'supermarket', 'mall', 'bakery',
            'leisure', 'restaurant', 'factory', 'hospital',
            'fire_station', 'police_station',
            'residential_zone', 'commercial_zone', 'industrial_zone',
            'forest_zone', 'farmland_zone'
        ];

        paramNames.forEach(name => {
            const checkbox = document.getElementById(name);
            params[name] = checkbox.checked ? 'true' : 'false';
        });

        return params;
    }

    /**
     * Construire l'URL de requête
     */
    buildURL() {
        const zone = this.getBoundsGeoJSON();
        const params = this.getSelectedParams();

        const queryParams = new URLSearchParams({
            zone: JSON.stringify(zone),
            ...params
        });

        return `/api/enhanced-data/?${queryParams.toString()}`;
    }

    /**
     * Extraire les données
     */
    async extractData() {
        const extractBtn = document.getElementById('extractBtn');
        const resultsSection = document.getElementById('resultsSection');
        const resultsContent = document.getElementById('resultsContent');

        if (!this.polygon) {
            this.showMessage('Veuillez d\'abord dessiner une zone', 'error');
            resultsContent.innerHTML = '<div class="result-error">⚠️ Veuillez d\'abord dessiner une zone sur la carte</div>';
            resultsSection.classList.remove('hidden');
            return;
        }

        const params = this.getSelectedParams();
        const hasSelection = Object.values(params).some(v => v === 'true');

        if (!hasSelection) {
            this.showMessage('Veuillez sélectionner au moins un type de données', 'error');
            resultsContent.innerHTML = '<div class="result-error">⚠️ Veuillez sélectionner au moins un type de données à extraire</div>';
            resultsSection.classList.remove('hidden');
            return;
        }

        extractBtn.disabled = true;
        extractBtn.textContent = '⏳ Extraction en cours...';
        resultsSection.classList.remove('hidden');
        resultsContent.innerHTML = '<div class="result-loading">Extraction des données depuis OpenStreetMap via Overpass API...<br>Cela peut prendre quelques secondes.</div>';

        try {
            const url = this.buildURL();
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.lastResult = data;

            this.displayResults(data);

            document.getElementById('downloadBtn').classList.remove('hidden');
            document.getElementById('copyUrlBtn').classList.remove('hidden');

            this.showMessage('Extraction réussie!', 'success');

        } catch (error) {
            resultsContent.innerHTML = `<div class="result-error">❌ Erreur lors de l'extraction:<br>${error.message}</div>`;
            this.showMessage('Erreur lors de l\'extraction', 'error');
        } finally {
            extractBtn.disabled = false;
            extractBtn.textContent = '🚀 Extraire les données';
        }
    }

    /**
     * Afficher les résultats
     */
    displayResults(data) {
        const resultsContent = document.getElementById('resultsContent');

        const elementsCount = data.elements ? data.elements.length : 0;

        let html = `<div class="result-success">✅ Extraction réussie!</div>`;
        html += `<div class="result-stats">`;
        html += `<div class="stat-item">
            <strong>Éléments trouvés:</strong>
            <span>${elementsCount}</span>
        </div>`;

        if (data.elements && data.elements.length > 0) {
            const types = {};
            data.elements.forEach(el => {
                const type = el.type || 'unknown';
                types[type] = (types[type] || 0) + 1;
            });

            html += `<div class="stat-item">
                <strong>Types d'éléments:</strong>
                <span>${Object.keys(types).length}</span>
            </div>`;

            for (const [type, count] of Object.entries(types)) {
                const icon = type === 'node' ? '📍' : type === 'way' ? '🛣️' : '🗺️';
                html += `<div class="stat-item">
                    <strong>${icon} ${type}:</strong>
                    <span>${count}</span>
                </div>`;
            }
        }

        html += `</div>`;

        resultsContent.innerHTML = html;
    }

    /**
     * Télécharger le JSON
     */
    downloadJSON() {
        if (!this.lastResult) {
            alert('Aucune donnée à télécharger');
            return;
        }

        const dataStr = JSON.stringify(this.lastResult, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `enhanced_data_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Copier l'URL de la requête
     */
    copyURL() {
        const url = window.location.origin + this.buildURL();

        navigator.clipboard.writeText(url).then(() => {
            const btn = document.getElementById('copyUrlBtn');
            const originalText = btn.textContent;
            btn.textContent = '✅ URL copiée!';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 2000);
        }).catch(err => {
            alert('Erreur lors de la copie de l\'URL: ' + err);
        });
    }
}

L.GeometryUtil = L.extend(L.GeometryUtil || {}, {
    geodesicArea: function (latLngs) {
        var pointsCount = latLngs.length,
            area = 0.0,
            d2r = Math.PI / 180,
            p1, p2;

        if (pointsCount > 2) {
            for (var i = 0; i < pointsCount; i++) {
                p1 = latLngs[i];
                p2 = latLngs[(i + 1) % pointsCount];
                area += ((p2.lng - p1.lng) * d2r) *
                    (2 + Math.sin(p1.lat * d2r) + Math.sin(p2.lat * d2r));
            }
            area = area * 6378137.0 * 6378137.0 / 2.0;
        }

        return Math.abs(area);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const extractor = new EnhancedDataExtractor();
    window.extractor = extractor;
});
