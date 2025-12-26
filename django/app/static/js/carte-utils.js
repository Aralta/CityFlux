/**
 * Fonctions utilitaires pour la carte interactive
 * Dépend de carte-config.js
 */

/**
 * Obtient l'icône emoji appropriée pour un POI
 * @param {Object} properties - Propriétés du POI
 * @returns {string} Emoji représentant le POI
 */
function getPOIIcon(properties) {
    const type = (properties.type || '').toLowerCase().trim();
    const subtype = (properties.subtype || '').toLowerCase().trim();
    
    if (subtype && POI_ICONS.subtypes[subtype]) {
        return POI_ICONS.subtypes[subtype];
    }
    
    if (type && POI_ICONS.types[type]) {
        return POI_ICONS.types[type];
    }
    
    return POI_ICONS.default;
}

/**
 * Obtient les couleurs appropriées pour une zone
 * @param {Object} properties - Propriétés de la zone
 * @param {number} index - Index de la zone (pour fallback)
 * @returns {Object} Objet avec fill et stroke
 */
function getZoneColor(properties, index = 0) {
    const type = (properties.type || '').toLowerCase().trim();
    const subtype = (properties.subtype || '').toLowerCase().trim();
    
    if (subtype && ZONE_COLORS.subtypes[subtype]) {
        return ZONE_COLORS.subtypes[subtype];
    }
    
    if (type && ZONE_COLORS.types[type]) {
        return ZONE_COLORS.types[type];
    }
    
    return ZONE_COLOR_PALETTE[index % ZONE_COLOR_PALETTE.length];
}

/**
 * Crée une icône Leaflet avec un emoji
 * @param {string} emoji - L'emoji à afficher
 * @param {number} size - Taille de l'icône (défaut: 24)
 * @returns {L.DivIcon} Icône Leaflet
 */
function createEmojiIcon(emoji, size = 24) {
    return L.divIcon({
        html: `<div style="font-size: ${size}px; text-align: center; line-height: ${size}px;">${emoji}</div>`,
        className: 'emoji-marker',
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
        popupAnchor: [0, -size / 2]
    });
}

/**
 * Génère le contenu HTML d'un popup pour un marqueur
 * @param {Object} properties - Propriétés du marqueur
 * @param {string} emoji - Emoji à afficher
 * @returns {string} HTML du popup
 */
function createMarkerPopupContent(properties, emoji) {
    let content = `<div class="marker-popup">`;
    content += `<h4>${emoji} ${properties.nom || properties.name || 'Sans nom'}</h4>`;
    
    const popupFields = ['type', 'subtype', 'description', 'type_transport', 'nb_lignes', 'capacity'];
    
    popupFields.forEach(field => {
        if (properties[field]) {
            const label = POPUP_LABELS[field] || field.charAt(0).toUpperCase() + field.slice(1);
            content += `<p><strong>${label}:</strong> ${properties[field]}</p>`;
        }
    });
    
    content += `</div>`;
    return content;
}

/**
 * Génère le contenu HTML d'un popup pour une zone
 * @param {Object} properties - Propriétés de la zone
 * @returns {string} HTML du popup
 */
function createZonePopupContent(properties) {
    let content = `<div class="zone-popup">`;
    content += `<h4>${properties.nom || properties.name || 'Zone sans nom'}</h4>`;
    
    if (properties.type) {
        content += `<p><strong>Type:</strong> ${properties.type}</p>`;
    }
    if (properties.subtype) {
        content += `<p><strong>Sous-type:</strong> ${properties.subtype}</p>`;
    }
    if (properties.description) {
        content += `<p><strong>Description:</strong> ${properties.description}</p>`;
    }
    if (properties.area || properties.surface) {
        const area = properties.area || properties.surface;
        content += `<p><strong>Surface:</strong> ${typeof area === 'number' ? area.toFixed(2) + ' m²' : area}</p>`;
    }
    
    content += `</div>`;
    return content;
}

/**
 * Calcule le centroïde d'un polygone GeoJSON
 * @param {Object} feature - Feature GeoJSON
 * @returns {Array} [lat, lng] du centroïde
 */
function calculateCentroid(feature) {
    try {
        const coords = feature.geometry.type === 'Polygon' 
            ? feature.geometry.coordinates[0]
            : feature.geometry.coordinates[0][0];
        
        let sumLat = 0, sumLng = 0;
        coords.forEach(coord => {
            sumLng += coord[0];
            sumLat += coord[1];
        });
        
        return [sumLat / coords.length, sumLng / coords.length];
    } catch (e) {
        console.warn('Erreur calcul centroïde:', e);
        return null;
    }
}

/**
 * Formate un type de suggestion Nominatim en label lisible
 * @param {string} type - Type Nominatim
 * @returns {string} Label formaté avec emoji
 */
function formatSuggestionType(type) {
    return SUGGESTION_TYPES[type] || '📍 Lieu';
}

/**
 * Debounce une fonction
 * @param {Function} func - Fonction à debounce
 * @param {number} wait - Délai en ms
 * @returns {Function} Fonction debounced
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Normalise une chaîne pour la recherche (sans accents, lowercase)
 * @param {string} str - Chaîne à normaliser
 * @returns {string} Chaîne normalisée
 */
function normalizeSearchString(str) {
    return str
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
}
