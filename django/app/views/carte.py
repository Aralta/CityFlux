"""
Vue pour la page de carte interactive avec OpenStreetMap et Leaflet
"""
from django.http import HttpResponse, JsonResponse
from django.template import loader
from .database import db_manager
import json
import traceback

def carte_view(request):
    """
    Vue principale pour afficher la carte interactive
    """
    template = loader.get_template('carte.html')
    context = {
        'title': 'Carte Interactive - MobiFlux',
        'default_center': [43.4853, 5.7246],  # Pourrières
        'default_zoom': 14
    }
    return HttpResponse(template.render(context, request))


def api_search(request):
    """
    API de recherche de lieux dans la base de données
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 3:
        return JsonResponse({'results': []})
    
    try:
        # Rechercher dans les arrêts
        arrets_query = """
        SELECT 
            a.nom,
            ST_Y(a.position) as lat,
            ST_X(a.position) as lng,
            t.nom as type
        FROM arret a
        LEFT JOIN type_transport t ON a.id_type = t.id
        WHERE LOWER(a.nom) LIKE LOWER(%s)
        LIMIT 5
        """
        arrets = db_manager.execute_query(arrets_query, (f'%{query}%',))
        
        # Rechercher dans les POI
        poi_query = """
        SELECT 
            nom,
            ST_Y(position) as lat,
            ST_X(position) as lng,
            type
        FROM poi
        WHERE LOWER(nom) LIKE LOWER(%s)
        LIMIT 5
        """
        pois = db_manager.execute_query(poi_query, (f'%{query}%',))
        
        results = []
        
        if arrets:
            for arret in arrets:
                results.append({
                    'name': arret['nom'],
                    'lat': float(arret['lat']),
                    'lng': float(arret['lng']),
                    'type': f"🚏 {arret['type'] or 'Arrêt'}",
                    'category': 'transport'
                })
        
        if pois:
            for poi in pois:
                results.append({
                    'name': poi['nom'],
                    'lat': float(poi['lat']),
                    'lng': float(poi['lng']),
                    'type': f"📍 {poi['type'] or 'POI'}",
                    'category': 'poi'
                })
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        return JsonResponse({'error': str(e), 'results': []}, status=500)


def api_layers_list(request):
    """
    API pour lister toutes les couches disponibles
    """
    print("📋 API layers_list appelée")
    layers = [
        {
            'id': 'arrets',
            'name': 'Arrêts',
            'enabled': True,
            'type': 'markers',
            'description': 'Arrêts de transport en commun',
            'icon': '🚏',
            'config': {
                'color': '#e74c3c',
                'opacity': 1.0,
                'iconSize': [25, 41]
            }
        },
        {
            'id': 'lignes',
            'name': 'Lignes',
            'enabled': False,
            'type': 'geojson',
            'description': 'Lignes de transport',
            'icon': '🚌',
            'config': {
                'color': '#3498db',
                'opacity': 0.8,
                'weight': 3
            }
        },
        {
            'id': 'poi',
            'name': 'POI',
            'enabled': True,
            'type': 'markers',
            'description': 'Points d\'intérêt',
            'icon': '📍',
            'config': {
                'color': '#2ecc71',
                'opacity': 1.0,
                'iconSize': [25, 41]
            }
        },
        {
            'id': 'zones',
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
            }
        },
        {
            'id': 'background',
            'name': 'Background',
            'enabled': True,
            'hasToggle': False,
            'type': 'tile',
            'description': 'Type de fond de carte',
            'icon': '🗺️',
            'config': {
                'opacity': 1.0,
                'variant': 'Plan'
            }
        }
    ]
    
    return JsonResponse({'layers': layers})


def api_layer_data(request, layer_id):
    """
    API pour récupérer les données d'une couche depuis la base PostGIS
    """
    print(f"🗺️ API layer_data appelée pour: {layer_id}")
    
    try:
        # Récupérer la bounding box depuis les paramètres
        min_lng = float(request.GET.get('minLng', 5.70))
        min_lat = float(request.GET.get('minLat', 43.47))
        max_lng = float(request.GET.get('maxLng', 5.75))
        max_lat = float(request.GET.get('maxLat', 43.50))
        zoom = int(request.GET.get('zoom', 14))
        
        print(f"📍 BBox: [{min_lng}, {min_lat}, {max_lng}, {max_lat}] @ zoom {zoom}")
        
        bbox = (min_lng, min_lat, max_lng, max_lat)
        
        # Connecter à la base de données
        if not db_manager.connect():
            print("❌ Échec de connexion à la base de données")
            return JsonResponse({
                'type': 'FeatureCollection',
                'features': [],
                'error': 'Connexion à la base de données échouée'
            }, status=500)
        
        data = None
        
        try:
            if layer_id == 'arrets':
                type_filter = request.GET.get('type', None)
                print(f"🚏 Récupération des arrêts (type: {type_filter})")
                data = db_manager.get_arrets(bbox, type_filter)
                
            elif layer_id == 'lignes':
                type_filter = request.GET.get('type', None)
                print(f"🚌 Récupération des lignes (type: {type_filter})")
                data = db_manager.get_lignes(bbox, type_filter)
                
            elif layer_id == 'poi':
                poi_type = request.GET.get('type', None)
                poi_subtype = request.GET.get('subtype', None)
                print(f"📍 Récupération des POI (type: {poi_type}, subtype: {poi_subtype}, zoom: {zoom})")
                data = db_manager.get_poi(bbox, poi_type, poi_subtype, zoom)
                
            elif layer_id == 'zones':
                zone_type = request.GET.get('type', None)
                zone_subtype = request.GET.get('subtype', None)
                print(f"🔷 Récupération des zones (type: {zone_type}, subtype: {zone_subtype}, zoom: {zoom})")
                data = db_manager.get_zones(bbox, zone_type, zone_subtype, zoom)
            
            else:
                print(f"⚠️ Couche inconnue: {layer_id}")
                return JsonResponse({'error': 'Couche non trouvée'}, status=404)
            
            # Si pas de données, retourner un GeoJSON vide
            if data is None:
                print(f"⚠️ Aucune donnée retournée pour {layer_id}")
                data = {
                    'type': 'FeatureCollection',
                    'features': []
                }
            
            print(f"✅ {len(data.get('features', []))} features retournées pour {layer_id}")
            return JsonResponse(data, safe=False)
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des données: {e}")
            traceback.print_exc()
            return JsonResponse({
                'type': 'FeatureCollection',
                'features': [],
                'error': str(e)
            }, status=500)
        
    except ValueError as e:
        print(f"❌ Paramètres invalides: {e}")
        return JsonResponse({'error': f'Paramètres invalides: {str(e)}'}, status=400)
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
    finally:
        db_manager.disconnect()


def api_layer_config(request, layer_id):
    """
    API pour récupérer la configuration détaillée d'une couche
    Les filtres sont chargés dynamiquement depuis la base de données
    """
    # Récupérer les types dynamiquement depuis la DB
    poi_types = ['Tous']
    poi_subtypes = ['Tous']
    zone_types = ['Toutes']
    zone_subtypes = ['Toutes']
    
    try:
        if db_manager.connect():
            if layer_id == 'poi':
                poi_types = ['Tous'] + db_manager.get_poi_types()
                poi_subtypes = ['Tous'] + db_manager.get_poi_subtypes()
            elif layer_id == 'zones':
                zone_types = ['Toutes'] + db_manager.get_zone_types()
                zone_subtypes = ['Toutes'] + db_manager.get_zone_subtypes()
            db_manager.disconnect()
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération des types: {e}")
    
    configs = {
        'arrets': {
            'id': 'arrets',
            'name': 'Arrêts',
            'icon': '🚏',
            'parameters': [
                {
                    'name': 'iconSize',
                    'label': 'Taille des icônes',
                    'type': 'range',
                    'min': 15,
                    'max': 50,
                    'step': 5,
                    'value': 25
                },
                {
                    'name': 'showLabels',
                    'label': 'Afficher les étiquettes',
                    'type': 'checkbox',
                    'value': True
                }
            ],
            'filters': [
                {
                    'name': 'type',
                    'label': 'Type de transport',
                    'type': 'select',
                    'options': ['Tous', 'Bus', 'Tram', 'Métro', 'Train'],
                    'value': 'Tous'
                }
            ],
            'info': {
                'source': 'Base de données PostGIS',
                'description': 'Arrêts de transport en commun'
            }
        },
        'lignes': {
            'id': 'lignes',
            'name': 'Lignes',
            'icon': '🚌',
            'parameters': [
                {
                    'name': 'color',
                    'label': 'Couleur',
                    'type': 'color',
                    'value': '#3498db'
                },
                {
                    'name': 'opacity',
                    'label': 'Opacité',
                    'type': 'range',
                    'min': 0,
                    'max': 1,
                    'step': 0.1,
                    'value': 0.8
                },
                {
                    'name': 'weight',
                    'label': 'Épaisseur',
                    'type': 'range',
                    'min': 1,
                    'max': 10,
                    'step': 1,
                    'value': 3
                }
            ],
            'filters': [
                {
                    'name': 'type',
                    'label': 'Type de transport',
                    'type': 'multiselect',
                    'options': ['Bus', 'Tram', 'Métro', 'Train'],
                    'value': ['Bus', 'Tram']
                }
            ],
            'info': {
                'source': 'Base de données PostGIS',
                'description': 'Lignes de transport en commun'
            }
        },
        'poi': {
            'id': 'poi',
            'name': 'POI',
            'icon': '📍',
            'parameters': [
                {
                    'name': 'iconSize',
                    'label': 'Taille des icônes',
                    'type': 'range',
                    'min': 15,
                    'max': 50,
                    'step': 5,
                    'value': 25
                }
            ],
            'filters': [
                {
                    'name': 'type',
                    'label': 'Catégorie',
                    'type': 'select',
                    'options': poi_types,
                    'value': 'Tous'
                },
                {
                    'name': 'subtype',
                    'label': 'Sous-catégorie',
                    'type': 'select',
                    'options': poi_subtypes,
                    'value': 'Tous'
                }
            ],
            'info': {
                'source': 'Base de données PostGIS',
                'description': 'Points d\'intérêt'
            }
        },
        'zones': {
            'id': 'zones',
            'name': 'Zones',
            'icon': '🔷',
            'parameters': [
                {
                    'name': 'fillColor',
                    'label': 'Couleur de remplissage',
                    'type': 'color',
                    'value': '#9b59b6'
                },
                {
                    'name': 'fillOpacity',
                    'label': 'Opacité du remplissage',
                    'type': 'range',
                    'min': 0,
                    'max': 1,
                    'step': 0.1,
                    'value': 0.3
                },
                {
                    'name': 'color',
                    'label': 'Couleur du contour',
                    'type': 'color',
                    'value': '#8e44ad'
                },
                {
                    'name': 'weight',
                    'label': 'Épaisseur du contour',
                    'type': 'range',
                    'min': 1,
                    'max': 5,
                    'step': 1,
                    'value': 2
                }
            ],
            'filters': [
                {
                    'name': 'type',
                    'label': 'Catégorie',
                    'type': 'select',
                    'options': zone_types,
                    'value': 'Toutes'
                },
                {
                    'name': 'subtype',
                    'label': 'Sous-catégorie',
                    'type': 'select',
                    'options': zone_subtypes,
                    'value': 'Toutes'
                }
            ],
            'info': {
                'source': 'Base de données PostGIS',
                'description': 'Zones géographiques'
            }
        },
        'background': {
            'id': 'background',
            'name': 'Background',
            'icon': '🗺️',
            'parameters': [
                {
                    'name': 'variant',
                    'label': 'Type de carte',
                    'type': 'select',
                    'options': ['Plan', 'Sombre', 'Satellite', 'Topographique'],
                    'value': 'Plan'
                }
            ],
            'filters': [],
            'info': {
                'source': 'OpenStreetMap',
                'description': 'Fond de carte'
            }
        }
    }
    
    if layer_id in configs:
        return JsonResponse(configs[layer_id])
    
    return JsonResponse({'error': 'Configuration non trouvée'}, status=404)
