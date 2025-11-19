"""
Vue pour la page de carte interactive avec OpenStreetMap et Leaflet
"""
from django.http import HttpResponse, JsonResponse
from django.template import loader
import json

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
    API de recherche de lieux
    Endpoint: /api/search?q=...
    Retourne les coordonnées d'un lieu recherché
    """
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'error': 'Aucun terme de recherche fourni'}, status=400)
    
    # Simulation de résultats (à remplacer par un vrai appel à Nominatim ou votre base de données)
    # En production, faire un appel à https://nominatim.openstreetmap.org/search
    
    # Données de démonstration pour Pourrières et environs
    mock_data = {
        'pourrieres': {'lat': 43.4853, 'lng': 5.7246, 'name': 'Pourrières', 'zoom': 14},
        'mairie': {'lat': 43.4853, 'lng': 5.7246, 'name': 'Mairie de Pourrières', 'zoom': 16},
        'ecole': {'lat': 43.4858, 'lng': 5.7251, 'name': 'École élémentaire', 'zoom': 17},
        'aix': {'lat': 43.5297, 'lng': 5.4474, 'name': 'Aix-en-Provence', 'zoom': 13},
        'marseille': {'lat': 43.2965, 'lng': 5.3698, 'name': 'Marseille', 'zoom': 12}
    }
    
    # Recherche simple dans les données de démonstration
    query_lower = query.lower()
    for key, value in mock_data.items():
        if key in query_lower or query_lower in value['name'].lower():
            return JsonResponse({
                'success': True,
                'result': {
                    'lat': value['lat'],
                    'lng': value['lng'],
                    'name': value['name'],
                    'zoom': value['zoom']
                }
            })
    
    # Si aucun résultat trouvé
    return JsonResponse({
        'success': False,
        'message': f'Aucun résultat trouvé pour "{query}"'
    }, status=404)


def api_layers_list(request):
    """
    API pour lister toutes les couches disponibles
    Endpoint: /api/layers/
    """
    layers = [
        {
            'id': 'data',
            'name': 'Data',
            'enabled': True,
            'type': 'geojson',
            'description': 'Données de mobilité',
            'icon': '📊',
            'config': {
                'color': '#1a73e8',
                'opacity': 0.7,
                'weight': 2
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
                'color': '#e74c3c',
                'opacity': 1.0,
                'iconSize': [25, 41]
            }
        },
        {
            'id': 'temp',
            'name': 'Temp',
            'enabled': False,
            'type': 'heatmap',
            'description': 'Données temporelles',
            'icon': '🌡️',
            'config': {
                'radius': 25,
                'blur': 15,
                'maxOpacity': 0.8
            }
        },
        {
            'id': 'background',
            'name': 'Background',
            'enabled': True,
            'type': 'tile',
            'description': 'Fond de carte alternatif',
            'icon': '🗺️',
            'config': {
                'opacity': 1.0,
                'variant': 'standard'
            }
        },
        {
            'id': 'zone',
            'name': 'Zone',
            'enabled': False,
            'type': 'polygon',
            'description': 'Zones d\'analyse',
            'icon': '🔷',
            'config': {
                'fillColor': '#3498db',
                'fillOpacity': 0.3,
                'color': '#2980b9',
                'weight': 2
            }
        }
    ]
    
    return JsonResponse({'layers': layers})


def api_layer_data(request, layer_id):
    """
    API pour récupérer les données d'une couche spécifique
    Endpoint: /api/layers/<id>/data/
    """
    
    # Données GeoJSON de démonstration
    mock_data = {
        'data': {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': [
                            [5.7200, 43.4840],
                            [5.7246, 43.4853],
                            [5.7290, 43.4870]
                        ]
                    },
                    'properties': {
                        'name': 'Route principale',
                        'traffic': 'high',
                        'flow': 1250
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': [
                            [5.7246, 43.4853],
                            [5.7250, 43.4890],
                            [5.7260, 43.4920]
                        ]
                    },
                    'properties': {
                        'name': 'Route secondaire',
                        'traffic': 'medium',
                        'flow': 680
                    }
                }
            ]
        },
        'poi': {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [5.7246, 43.4853]
                    },
                    'properties': {
                        'name': 'Mairie de Pourrières',
                        'type': 'administration',
                        'description': 'Hôtel de ville'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [5.7251, 43.4858]
                    },
                    'properties': {
                        'name': 'École élémentaire',
                        'type': 'education',
                        'description': 'Établissement scolaire'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [5.7245, 43.4851]
                    },
                    'properties': {
                        'name': 'Place du village',
                        'type': 'public',
                        'description': 'Espace public central'
                    }
                }
            ]
        },
        'zone': {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [5.7146, 43.4903],
                            [5.7346, 43.4903],
                            [5.7346, 43.4803],
                            [5.7146, 43.4803],
                            [5.7146, 43.4903]
                        ]]
                    },
                    'properties': {
                        'name': 'Zone d\'analyse principale',
                        'type': 'primary',
                        'population': 3850
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [5.7180, 43.4880],
                            [5.7280, 43.4880],
                            [5.7280, 43.4820],
                            [5.7180, 43.4820],
                            [5.7180, 43.4880]
                        ]]
                    },
                    'properties': {
                        'name': 'Zone résidentielle',
                        'type': 'residential',
                        'population': 1250
                    }
                }
            ]
        }
    }
    
    if layer_id in mock_data:
        return JsonResponse(mock_data[layer_id])
    
    return JsonResponse({'error': 'Couche non trouvée'}, status=404)


def api_layer_config(request, layer_id):
    """
    API pour récupérer la configuration détaillée d'une couche
    Endpoint: /api/layers/<id>/config/
    """
    
    configs = {
        'data': {
            'id': 'data',
            'name': 'Data',
            'parameters': [
                {
                    'name': 'color',
                    'label': 'Couleur',
                    'type': 'color',
                    'value': '#1a73e8'
                },
                {
                    'name': 'opacity',
                    'label': 'Opacité',
                    'type': 'range',
                    'min': 0,
                    'max': 1,
                    'step': 0.1,
                    'value': 0.7
                },
                {
                    'name': 'weight',
                    'label': 'Épaisseur',
                    'type': 'range',
                    'min': 1,
                    'max': 10,
                    'step': 1,
                    'value': 2
                }
            ],
            'filters': [
                {
                    'name': 'traffic',
                    'label': 'Niveau de trafic',
                    'type': 'select',
                    'options': ['all', 'high', 'medium', 'low'],
                    'value': 'all'
                }
            ],
            'info': {
                'source': 'Données de mobilité territoriale',
                'lastUpdate': '2025-10-25',
                'coverage': 'Commune de Pourrières'
            }
        },
        'poi': {
            'id': 'poi',
            'name': 'POI',
            'parameters': [
                {
                    'name': 'iconSize',
                    'label': 'Taille des icônes',
                    'type': 'range',
                    'min': 10,
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
                    'label': 'Type de POI',
                    'type': 'multiselect',
                    'options': ['administration', 'education', 'public', 'commercial'],
                    'value': ['administration', 'education', 'public']
                }
            ],
            'info': {
                'source': 'Base OpenStreetMap + données locales',
                'count': 47,
                'types': 'Administration, éducation, commerce, loisirs'
            }
        },
        'temp': {
            'id': 'temp',
            'name': 'Temp',
            'parameters': [
                {
                    'name': 'radius',
                    'label': 'Rayon',
                    'type': 'range',
                    'min': 10,
                    'max': 50,
                    'step': 5,
                    'value': 25
                },
                {
                    'name': 'blur',
                    'label': 'Flou',
                    'type': 'range',
                    'min': 5,
                    'max': 30,
                    'step': 5,
                    'value': 15
                },
                {
                    'name': 'maxOpacity',
                    'label': 'Opacité maximale',
                    'type': 'range',
                    'min': 0,
                    'max': 1,
                    'step': 0.1,
                    'value': 0.8
                }
            ],
            'filters': [
                {
                    'name': 'timeRange',
                    'label': 'Période',
                    'type': 'select',
                    'options': ['hour', 'day', 'week', 'month'],
                    'value': 'day'
                }
            ],
            'info': {
                'source': 'Données temporelles agrégées',
                'resolution': 'Horaire',
                'period': 'Derniers 30 jours'
            }
        },
        'background': {
            'id': 'background',
            'name': 'Background',
            'parameters': [
                {
                    'name': 'variant',
                    'label': 'Variante',
                    'type': 'select',
                    'options': ['standard', 'satellite', 'terrain', 'dark'],
                    'value': 'standard'
                },
                {
                    'name': 'opacity',
                    'label': 'Opacité',
                    'type': 'range',
                    'min': 0,
                    'max': 1,
                    'step': 0.1,
                    'value': 1.0
                }
            ],
            'filters': [],
            'info': {
                'source': 'OpenStreetMap',
                'attribution': '© OpenStreetMap contributors'
            }
        },
        'zone': {
            'id': 'zone',
            'name': 'Zone',
            'parameters': [
                {
                    'name': 'fillColor',
                    'label': 'Couleur de remplissage',
                    'type': 'color',
                    'value': '#3498db'
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
                    'name': 'strokeColor',
                    'label': 'Couleur du contour',
                    'type': 'color',
                    'value': '#2980b9'
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
                    'name': 'zoneType',
                    'label': 'Type de zone',
                    'type': 'multiselect',
                    'options': ['primary', 'residential', 'commercial', 'industrial'],
                    'value': ['primary', 'residential']
                }
            ],
            'info': {
                'source': 'Zonage territorial',
                'count': 12,
                'totalArea': '25.4 km²'
            }
        }
    }
    
    if layer_id in configs:
        return JsonResponse(configs[layer_id])
    
    return JsonResponse({'error': 'Configuration non trouvée'}, status=404)
