"""
Vue pour la page de carte interactive avec OpenStreetMap et Leaflet.
"""
from django.http import HttpResponse, JsonResponse
from django.template import loader
from .database import db_manager


# Configuration centralisée des couches
LAYERS_CONFIG = {
    'arrets': {
        'name': 'Arrêts',
        'enabled': True,
        'type': 'markers',
        'description': 'Arrêts de transport en commun',
        'icon': '🚏',
        'config': {
            'color': '#e74c3c',
            'opacity': 1.0,
            'iconSize': [25, 41]
        },
        'parameters': [
            {'name': 'iconSize', 'label': 'Taille des icônes', 'type': 'range', 'min': 15, 'max': 50, 'step': 5, 'value': 25},
            {'name': 'showLabels', 'label': 'Afficher les étiquettes', 'type': 'checkbox', 'value': True}
        ],
        'filters': [
            {'name': 'type', 'label': 'Type de transport', 'type': 'select', 'options': ['Tous', 'Bus', 'Tram', 'Métro', 'Train'], 'value': 'Tous'}
        ],
        'info': {'source': 'Base de données PostGIS', 'description': 'Arrêts de transport en commun'}
    },
    'lignes': {
        'name': 'Lignes',
        'enabled': False,
        'type': 'geojson',
        'description': 'Lignes de transport',
        'icon': '🚌',
        'config': {
            'color': '#3498db',
            'opacity': 0.8,
            'weight': 3
        },
        'parameters': [
            {'name': 'color', 'label': 'Couleur', 'type': 'color', 'value': '#3498db'},
            {'name': 'opacity', 'label': 'Opacité', 'type': 'range', 'min': 0, 'max': 1, 'step': 0.1, 'value': 0.8},
            {'name': 'weight', 'label': 'Épaisseur', 'type': 'range', 'min': 1, 'max': 10, 'step': 1, 'value': 3}
        ],
        'filters': [
            {'name': 'type', 'label': 'Type de transport', 'type': 'multiselect', 'options': ['Bus', 'Tram', 'Métro', 'Train'], 'value': ['Bus', 'Tram']}
        ],
        'info': {'source': 'Base de données PostGIS', 'description': 'Lignes de transport en commun'}
    },
    'traces': {
        'name': 'Traces GNSS',
        'enabled': False,
        'type': 'geojson',
        'description': 'Trajectoires utilisateurs',
        'icon': '👣',
        'config': {
            'color': '#FF0000',
            'opacity': 0.8,
            'weight': 4
        },
        'parameters': [
            {'name': 'color', 'label': 'Couleur', 'type': 'color', 'value': '#FF0000'},
            {'name': 'opacity', 'label': 'Opacité', 'type': 'range', 'min': 0, 'max': 1, 'step': 0.1, 'value': 0.8},
            {'name': 'weight', 'label': 'Épaisseur', 'type': 'range', 'min': 1, 'max': 10, 'step': 1, 'value': 4}
        ],
        'filters': [
            {'name': 'trajectory_id', 'label': 'Sélectionner des traces', 'type': 'multiselect', 'options': [], 'value': [], 'dynamic': 'trajectory_ids'}
        ],
        'info': {'source': 'PostGIS (trajectory_gnss)', 'description': 'Traces GPS brutes des utilisateurs'}
    },
    'poi': {
        'name': 'POI',
        'enabled': True,
        'type': 'markers',
        'description': 'Points d\'intérêt',
        'icon': '📍',
        'config': {
            'color': '#2ecc71',
            'opacity': 1.0,
            'iconSize': [25, 41]
        },
        'parameters': [
            {'name': 'iconSize', 'label': 'Taille des icônes', 'type': 'range', 'min': 15, 'max': 50, 'step': 5, 'value': 25}
        ],
        'filters': [
            {'name': 'type', 'label': 'Catégories', 'type': 'multiselect', 'options': [], 'value': [], 'dynamic': 'poi_types'},
            {'name': 'subtype', 'label': 'Sous-catégories', 'type': 'multiselect', 'options': [], 'value': [], 'dynamic': 'poi_subtypes', 'parent': 'type'}
        ],
        'info': {'source': 'Base de données PostGIS', 'description': 'Points d\'intérêt'}
    },
    'zones': {
        'name': 'Zones',
        'enabled': False,
        'type': 'polygon',
        'description': 'Zones d\'analyse',
        'icon': '🔷',
        'config': {
            'fillColor': '#9b59b6',
            'fillOpacity': 0.3,
            'color': '#8e44ad',
            'weight': 2
        },
        'parameters': [
            {'name': 'fillColor', 'label': 'Couleur de remplissage', 'type': 'color', 'value': '#9b59b6'},
            {'name': 'fillOpacity', 'label': 'Opacité du remplissage', 'type': 'range', 'min': 0, 'max': 1, 'step': 0.1, 'value': 0.3},
            {'name': 'color', 'label': 'Couleur du contour', 'type': 'color', 'value': '#8e44ad'},
            {'name': 'weight', 'label': 'Épaisseur du contour', 'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'value': 2}
        ],
        'filters': [
            {'name': 'type', 'label': 'Catégories', 'type': 'multiselect', 'options': [], 'value': [], 'dynamic': 'zone_types'},
            {'name': 'subtype', 'label': 'Sous-catégories', 'type': 'multiselect', 'options': [], 'value': [], 'dynamic': 'zone_subtypes', 'parent': 'type'}
        ],
        'info': {'source': 'Base de données PostGIS', 'description': 'Zones géographiques'}
    },
    'background': {
        'name': 'Background',
        'enabled': True,
        'hasToggle': False,
        'type': 'tile',
        'description': 'Type de fond de carte',
        'icon': '🗺️',
        'config': {
            'opacity': 1.0,
            'variant': 'Plan'
        },
        'parameters': [
            {'name': 'variant', 'label': 'Type de carte', 'type': 'select', 'options': ['Plan', 'Sombre', 'Satellite', 'Topographique'], 'value': 'Plan'}
        ],
        'filters': [],
        'info': {'source': 'OpenStreetMap', 'description': 'Fond de carte'}
    }
}

# Mapping des fonctions de récupération de données par couche
LAYER_DATA_HANDLERS = {
    'arrets': lambda bbox, request: db_manager.get_arrets(bbox, request.GET.get('type')),
    'lignes': lambda bbox, request: db_manager.get_lignes(bbox, request.GET.get('type')),
    'traces': lambda bbox, request: db_manager.get_trajectories_gnss(
        bbox, 
        int(request.GET.get('zoom', 14)),
        trajectory_ids=request.GET.getlist('trajectory_id')
    ),
    'poi': lambda bbox, request: db_manager.get_poi(
        bbox, 
        request.GET.getlist('type'), 
        request.GET.getlist('subtype'),
        int(request.GET.get('zoom', 14))
    ),
    'zones': lambda bbox, request: db_manager.get_zones(
        bbox,
        request.GET.getlist('type'),
        request.GET.getlist('subtype'),
        int(request.GET.get('zoom', 14))
    )
}

# Mapping des fonctions pour charger les options dynamiques des filtres
DYNAMIC_FILTER_LOADERS = {
    'poi_types': lambda: db_manager.get_poi_types(),
    'poi_subtypes': lambda: db_manager.get_poi_subtypes(),
    'zone_types': lambda: db_manager.get_zone_types(),
    'zone_subtypes': lambda: db_manager.get_zone_subtypes(),
    'trajectory_ids': lambda: db_manager.get_trajectory_ids(),
    'poi_hierarchy': lambda: db_manager.get_poi_structure(),
    'zone_hierarchy': lambda: db_manager.get_zone_structure()
}


def carte_view(request):
    """Vue principale pour afficher la carte interactive."""
    template = loader.get_template('carte.html')
    context = {
        'title': 'Carte Interactive - MobiFlux',
        'default_center': [43.4853, 5.7246],
        'default_zoom': 14
    }
    return HttpResponse(template.render(context, request))


def api_search(request):
    """API de recherche de lieux dans la base de données."""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 3:
        return JsonResponse({'results': []})
    
    try:
        results = []
        search_param = f'%{query}%'
        
        # Rechercher dans les arrêts
        arrets = db_manager.execute_query("""
            SELECT a.nom, ST_Y(a.position) as lat, ST_X(a.position) as lng, t.nom as type
            FROM arret a
            LEFT JOIN type_transport t ON a.id_type = t.id
            WHERE LOWER(a.nom) LIKE LOWER(%s)
            LIMIT 5
        """, (search_param,))
        
        if arrets:
            results.extend([{
                'name': a['nom'],
                'lat': float(a['lat']),
                'lng': float(a['lng']),
                'type': f"🚏 {a['type'] or 'Arrêt'}",
                'category': 'transport'
            } for a in arrets])
        
        # Rechercher dans les POI
        pois = db_manager.execute_query("""
            SELECT nom, ST_Y(position) as lat, ST_X(position) as lng, type
            FROM poi
            WHERE LOWER(nom) LIKE LOWER(%s)
            LIMIT 5
        """, (search_param,))
        
        if pois:
            results.extend([{
                'name': p['nom'],
                'lat': float(p['lat']),
                'lng': float(p['lng']),
                'type': f"📍 {p['type'] or 'POI'}",
                'category': 'poi'
            } for p in pois])
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        return JsonResponse({'error': str(e), 'results': []}, status=500)


def api_layers_list(request):
    """API pour lister toutes les couches disponibles."""
    layers = []
    for layer_id, config in LAYERS_CONFIG.items():
        layers.append({
            'id': layer_id,
            'name': config['name'],
            'enabled': config['enabled'],
            'type': config['type'],
            'description': config['description'],
            'icon': config['icon'],
            'config': config['config'],
            'hasToggle': config.get('hasToggle', True)
        })
    
    return JsonResponse({'layers': layers})


def api_layer_data(request, layer_id):
    """API pour récupérer les données d'une couche depuis la base PostGIS."""
    if layer_id not in LAYER_DATA_HANDLERS:
        return JsonResponse({'error': 'Couche non trouvée'}, status=404)
    
    try:
        bbox = (
            float(request.GET.get('minLng', 5.70)),
            float(request.GET.get('minLat', 43.47)),
            float(request.GET.get('maxLng', 5.75)),
            float(request.GET.get('maxLat', 43.50))
        )
        
        if not db_manager.connect():
            return JsonResponse({
                'type': 'FeatureCollection',
                'features': [],
                'error': 'Connexion à la base de données échouée'
            }, status=500)
        
        try:
            data = LAYER_DATA_HANDLERS[layer_id](bbox, request)
            
            if data is None:
                data = {'type': 'FeatureCollection', 'features': []}
            
            return JsonResponse(data, safe=False)
            
        except Exception as e:
            return JsonResponse({
                'type': 'FeatureCollection',
                'features': [],
                'error': str(e)
            }, status=500)
        
    except ValueError as e:
        return JsonResponse({'error': f'Paramètres invalides: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    finally:
        db_manager.disconnect()


def api_layer_config(request, layer_id):
    """API pour récupérer la configuration détaillée d'une couche."""
    if layer_id not in LAYERS_CONFIG:
        return JsonResponse({'error': 'Configuration non trouvée'}, status=404)
    
    config = LAYERS_CONFIG[layer_id].copy()
    
    # Charger les options dynamiques des filtres depuis la DB
    if config.get('filters'):
        try:
            if db_manager.connect():
                for filter_item in config['filters']:
                    dynamic_key = filter_item.get('dynamic')
                    if dynamic_key and dynamic_key in DYNAMIC_FILTER_LOADERS:
                        filter_item['options'] = DYNAMIC_FILTER_LOADERS[dynamic_key]()
                db_manager.disconnect()
        except Exception:
            pass
    
    return JsonResponse({
        'id': layer_id,
        'name': config['name'],
        'icon': config['icon'],
        'parameters': config.get('parameters', []),
        'filters': config.get('filters', []),
        'info': config.get('info', {}),
        'hierarchy': DYNAMIC_FILTER_LOADERS[f"{layer_id}_hierarchy"]() if f"{layer_id}_hierarchy" in DYNAMIC_FILTER_LOADERS else None
    })
