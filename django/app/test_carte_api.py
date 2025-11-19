#!/usr/bin/env python3
"""
Script de test des fonctionnalités de la page carte
Peut être exécuté sans lancer le serveur Django
"""

import json

# Simulation des données retournées par les APIs

def test_search_api():
    """Test de l'API de recherche"""
    print("=== Test API Search ===")
    
    queries = ['pourrieres', 'mairie', 'aix', 'marseille']
    
    for query in queries:
        print(f"\nRecherche: {query}")
        # Simulation de la réponse
        if query == 'pourrieres':
            result = {
                'success': True,
                'result': {
                    'lat': 43.4853,
                    'lng': 5.7246,
                    'name': 'Pourrières',
                    'zoom': 14
                }
            }
        elif query == 'mairie':
            result = {
                'success': True,
                'result': {
                    'lat': 43.4853,
                    'lng': 5.7246,
                    'name': 'Mairie de Pourrières',
                    'zoom': 16
                }
            }
        else:
            result = {
                'success': False,
                'message': f'Résultat trouvé pour {query}'
            }
        
        print(json.dumps(result, indent=2))

def test_layers_list():
    """Test de l'API liste des couches"""
    print("\n\n=== Test API Layers List ===")
    
    layers = [
        {'id': 'data', 'name': 'Data', 'enabled': True, 'icon': '📊'},
        {'id': 'poi', 'name': 'POI', 'enabled': True, 'icon': '📍'},
        {'id': 'temp', 'name': 'Temp', 'enabled': False, 'icon': '🌡️'},
        {'id': 'background', 'name': 'Background', 'enabled': True, 'icon': '🗺️'},
        {'id': 'zone', 'name': 'Zone', 'enabled': False, 'icon': '🔷'},
    ]
    
    for layer in layers:
        status = "✅ Activée" if layer['enabled'] else "⭕ Désactivée"
        print(f"\n{layer['icon']} {layer['name']} ({layer['id']}) - {status}")

def test_layer_data():
    """Test de l'API données de couche"""
    print("\n\n=== Test API Layer Data ===")
    
    print("\nCouche POI - Exemple de données:")
    poi_sample = {
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
    }
    print(json.dumps(poi_sample, indent=2))
    
    print("\nCouche Data - Exemple de flux:")
    data_sample = {
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
    }
    print(json.dumps(data_sample, indent=2))

def test_layer_config():
    """Test de l'API configuration de couche"""
    print("\n\n=== Test API Layer Config ===")
    
    print("\nConfiguration de la couche Data:")
    config = {
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
        ]
    }
    print(json.dumps(config, indent=2))

def main():
    """Fonction principale"""
    print("╔════════════════════════════════════════════════╗")
    print("║  Test des APIs de la Carte Interactive        ║")
    print("║  MobiFlux - Analyse de Mobilité Territoriale  ║")
    print("╚════════════════════════════════════════════════╝")
    
    test_search_api()
    test_layers_list()
    test_layer_data()
    test_layer_config()
    
    print("\n\n" + "="*60)
    print("✅ Tous les tests sont terminés!")
    print("="*60)
    print("\nPour utiliser l'application complète:")
    print("1. Installez Django: pip install django")
    print("2. Lancez le serveur: python test.py runserver 8000")
    print("3. Ouvrez: http://localhost:8000/carte/")

if __name__ == '__main__':
    main()
