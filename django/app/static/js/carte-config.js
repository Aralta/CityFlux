/**
 * Configuration des icônes et couleurs pour la carte interactive
 * Fichier séparé pour une meilleure maintenabilité
 */

/**
 * Mapping des icônes par catégorie de POI
 */
const POI_ICONS = {
    types: {
        'education': '🎓',
        'école': '🏫',
        'ecole': '🏫',
        'school': '🏫',
        'université': '🎓',
        'universite': '🎓',
        'university': '🎓',
        'college': '🎓',
        'lycée': '🎓',
        'lycee': '🎓',
        'commerce': '🛒',
        'shop': '🛒',
        'magasin': '🛒',
        'restaurant': '🍽️',
        'restauration': '🍽️',
        'food': '🍽️',
        'alimentation': '🍞',
        'santé': '🏥',
        'sante': '🏥',
        'health': '🏥',
        'médical': '🏥',
        'medical': '🏥',
        'sport': '⚽',
        'loisir': '🎭',
        'loisirs': '🎭',
        'leisure': '🎭',
        'culture': '🎭',
        'tourisme': '🏛️',
        'tourism': '🏛️',
        'transport': '🚏',
        'parking': '🅿️',
        'service': '🏢',
        'services': '🏢',
        'administration': '🏛️',
        'public': '🏛️',
        'religieux': '⛪',
        'religion': '⛪',
        'nature': '🌳',
        'parc': '🌳',
        'park': '🌳',
        'hébergement': '🏨',
        'hebergement': '🏨',
        'hotel': '🏨',
        'logement': '🏠'
    },

    subtypes: {
        // Alimentation
        'boulangerie': '🥖',
        'bakery': '🥖',
        'patisserie': '🍰',
        'pâtisserie': '🍰',
        'supermarché': '🛒',
        'supermarche': '🛒',
        'supermarket': '🛒',
        'epicerie': '🏪',
        'épicerie': '🏪',
        'grocery': '🏪',
        'boucherie': '🥩',
        'butcher': '🥩',
        'poissonnerie': '🐟',
        'fish': '🐟',
        'primeur': '🥬',
        'fruits_legumes': '🥬',
        'fromager': '🧀',
        'cheese': '🧀',
        'caviste': '🍷',
        'wine': '🍷',

        // Restauration
        'café': '☕',
        'cafe': '☕',
        'coffee': '☕',
        'bar': '🍺',
        'pub': '🍺',
        'fast_food': '🍔',
        'fastfood': '🍔',
        'pizza': '🍕',
        'pizzeria': '🍕',
        'glacier': '🍦',
        'ice_cream': '🍦',

        // Santé
        'pharmacie': '💊',
        'pharmacy': '💊',
        'médecin': '👨‍⚕️',
        'medecin': '👨‍⚕️',
        'doctor': '👨‍⚕️',
        'dentiste': '🦷',
        'dentist': '🦷',
        'hôpital': '🏥',
        'hopital': '🏥',
        'hospital': '🏥',
        'clinique': '🏥',
        'clinic': '🏥',
        'vétérinaire': '🐾',
        'veterinaire': '🐾',
        'veterinary': '🐾',
        'optique': '👓',
        'opticien': '👓',

        // Éducation
        'maternelle': '👶',
        'kindergarten': '👶',
        'primaire': '📚',
        'elementary': '📚',
        'crèche': '👶',
        'creche': '👶',
        'bibliothèque': '📖',
        'bibliotheque': '📖',
        'library': '📖',

        // Services
        'banque': '🏦',
        'bank': '🏦',
        'poste': '📮',
        'post_office': '📮',
        'police': '👮',
        'gendarmerie': '👮',
        'pompiers': '🚒',
        'fire_station': '🚒',
        'mairie': '🏛️',
        'town_hall': '🏛️',

        // Sport
        'piscine': '🏊',
        'swimming_pool': '🏊',
        'gymnase': '🏋️',
        'gym': '🏋️',
        'fitness': '🏋️',
        'stade': '🏟️',
        'stadium': '🏟️',
        'tennis': '🎾',
        'football': '⚽',
        'basketball': '🏀',

        // Loisirs/Culture
        'cinéma': '🎬',
        'cinema': '🎬',
        'théâtre': '🎭',
        'theatre': '🎭',
        'musée': '🏛️',
        'musee': '🏛️',
        'museum': '🏛️',
        'galerie': '🖼️',
        'gallery': '🖼️',

        // Transport
        'gare': '🚉',
        'station': '🚉',
        'aéroport': '✈️',
        'aeroport': '✈️',
        'airport': '✈️',
        'bus': '🚌',
        'métro': '🚇',
        'metro': '🚇',
        'tram': '🚊',
        'vélo': '🚲',
        'velo': '🚲',
        'bike': '🚲',

        // Hébergement
        'camping': '⛺',
        'gîte': '🏡',
        'gite': '🏡',
        'chambre_hote': '🛏️',

        // Religion
        'église': '⛪',
        'eglise': '⛪',
        'church': '⛪',
        'mosquée': '🕌',
        'mosquee': '🕌',
        'mosque': '🕌',
        'synagogue': '🕍',
        'temple': '🛕',

        // Autres commerces
        'coiffeur': '💇',
        'hairdresser': '💇',
        'fleuriste': '💐',
        'florist': '💐',
        'pressing': '👔',
        'laundry': '👔',
        'garage': '🔧',
        'car_repair': '🔧',
        'station_service': '⛽',
        'fuel': '⛽',
        'essence': '⛽'
    },

    default: '📍'
};

/**
 * Mapping des couleurs par catégorie de zone
 */
const ZONE_COLORS = {
    types: {
        'résidentiel': { fill: '#3498db', stroke: '#2980b9' },
        'residentiel': { fill: '#3498db', stroke: '#2980b9' },
        'residential': { fill: '#3498db', stroke: '#2980b9' },
        'commercial': { fill: '#e74c3c', stroke: '#c0392b' },
        'industriel': { fill: '#7f8c8d', stroke: '#5d6d7e' },
        'industrial': { fill: '#7f8c8d', stroke: '#5d6d7e' },
        'agricole': { fill: '#27ae60', stroke: '#1e8449' },
        'agricultural': { fill: '#27ae60', stroke: '#1e8449' },
        'naturel': { fill: '#2ecc71', stroke: '#27ae60' },
        'nature': { fill: '#2ecc71', stroke: '#27ae60' },
        'natural': { fill: '#2ecc71', stroke: '#27ae60' },
        'parc': { fill: '#1abc9c', stroke: '#16a085' },
        'park': { fill: '#1abc9c', stroke: '#16a085' },
        'loisirs': { fill: '#9b59b6', stroke: '#8e44ad' },
        'leisure': { fill: '#9b59b6', stroke: '#8e44ad' },
        'sport': { fill: '#f39c12', stroke: '#d68910' },
        'éducation': { fill: '#e67e22', stroke: '#ca6f1e' },
        'education': { fill: '#e67e22', stroke: '#ca6f1e' },
        'santé': { fill: '#e91e63', stroke: '#c2185b' },
        'sante': { fill: '#e91e63', stroke: '#c2185b' },
        'health': { fill: '#e91e63', stroke: '#c2185b' },
        'transport': { fill: '#00bcd4', stroke: '#0097a7' },
        'administratif': { fill: '#795548', stroke: '#5d4037' },
        'administrative': { fill: '#795548', stroke: '#5d4037' },
        'mixte': { fill: '#ff9800', stroke: '#f57c00' },
        'mixed': { fill: '#ff9800', stroke: '#f57c00' },
        'eau': { fill: '#2196f3', stroke: '#1976d2' },
        'water': { fill: '#2196f3', stroke: '#1976d2' },
        'forêt': { fill: '#4caf50', stroke: '#388e3c' },
        'foret': { fill: '#4caf50', stroke: '#388e3c' },
        'forest': { fill: '#4caf50', stroke: '#388e3c' },
        'zone_protégée': { fill: '#8bc34a', stroke: '#689f38' },
        'protected': { fill: '#8bc34a', stroke: '#689f38' },
        'danger': { fill: '#f44336', stroke: '#d32f2f' },
        'inondable': { fill: '#03a9f4', stroke: '#0288d1' },
        'flood': { fill: '#03a9f4', stroke: '#0288d1' },
        'urbain': { fill: '#607d8b', stroke: '#455a64' },
        'urban': { fill: '#607d8b', stroke: '#455a64' },
        'périurbain': { fill: '#78909c', stroke: '#546e7a' },
        'suburban': { fill: '#78909c', stroke: '#546e7a' },
        'rural': { fill: '#a5d6a7', stroke: '#81c784' }
    },

    subtypes: {
        // Résidentiel
        'habitat_collectif': { fill: '#5dade2', stroke: '#3498db' },
        'habitat_individuel': { fill: '#85c1e9', stroke: '#5dade2' },
        'lotissement': { fill: '#aed6f1', stroke: '#85c1e9' },

        // Commercial
        'centre_commercial': { fill: '#ec7063', stroke: '#e74c3c' },
        'zone_commerciale': { fill: '#f1948a', stroke: '#ec7063' },
        'marché': { fill: '#f5b7b1', stroke: '#f1948a' },

        // Industriel
        'usine': { fill: '#5d6d7e', stroke: '#4d5656' },
        'entrepôt': { fill: '#7f8c8d', stroke: '#5d6d7e' },
        'zone_artisanale': { fill: '#95a5a6', stroke: '#7f8c8d' },

        // Nature
        'jardin_public': { fill: '#58d68d', stroke: '#2ecc71' },
        'espace_vert': { fill: '#82e0aa', stroke: '#58d68d' },
        'bois': { fill: '#229954', stroke: '#1e8449' },
        'prairie': { fill: '#abebc6', stroke: '#82e0aa' },

        // Sport
        'stade': { fill: '#f5b041', stroke: '#f39c12' },
        'terrain_sport': { fill: '#f8c471', stroke: '#f5b041' },
        'piscine': { fill: '#5dade2', stroke: '#3498db' },
        'gymnase': { fill: '#fad7a0', stroke: '#f8c471' },

        // Transport
        'gare': { fill: '#17a2b8', stroke: '#138496' },
        'parking': { fill: '#6c757d', stroke: '#5a6268' },
        'aéroport': { fill: '#20c997', stroke: '#1a9c7a' },

        // Eau
        'lac': { fill: '#64b5f6', stroke: '#42a5f5' },
        'rivière': { fill: '#90caf9', stroke: '#64b5f6' },
        'étang': { fill: '#bbdefb', stroke: '#90caf9' },

        // Quartiers
        'centre_ville': { fill: '#ff7043', stroke: '#f4511e' },
        'quartier': { fill: '#ffab91', stroke: '#ff7043' },
        'village': { fill: '#d7ccc8', stroke: '#bcaaa4' }
    },

    default: { fill: '#9b59b6', stroke: '#8e44ad' }
};

/**
 * Palette de couleurs pour les zones sans type défini
 */
const ZONE_COLOR_PALETTE = [
    { fill: '#3498db', stroke: '#2980b9' },
    { fill: '#e74c3c', stroke: '#c0392b' },
    { fill: '#2ecc71', stroke: '#27ae60' },
    { fill: '#f39c12', stroke: '#d68910' },
    { fill: '#9b59b6', stroke: '#8e44ad' },
    { fill: '#1abc9c', stroke: '#16a085' },
    { fill: '#e91e63', stroke: '#c2185b' },
    { fill: '#00bcd4', stroke: '#0097a7' },
    { fill: '#ff9800', stroke: '#f57c00' },
    { fill: '#795548', stroke: '#5d4037' },
    { fill: '#607d8b', stroke: '#455a64' },
    { fill: '#8bc34a', stroke: '#689f38' }
];

/**
 * Configuration des tuiles de fond de carte
 */
const TILE_CONFIGS = {
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

/**
 * Labels en français pour les propriétés des popups
 */
const POPUP_LABELS = {
    nom: 'Nom',
    name: 'Nom',
    type: 'Type',
    subtype: 'Sous-type',
    description: 'Description',
    type_transport: 'Transport',
    nb_lignes: 'Lignes desservies',
    capacity: 'Capacité',
    speed: 'Vitesse (km/h)',
    timestamp: 'Heure'
};

/**
 * Types de suggestions pour la recherche
 */
const SUGGESTION_TYPES = {
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
