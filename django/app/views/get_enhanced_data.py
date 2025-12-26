"""
Module pour récupérer des données enrichies depuis l'API Overpass.
"""
import requests
import json
from django.http import JsonResponse


# Configuration des types de données avec leurs tags OSM
OSM_DATA_CONFIG = {
    'school': {
        'tags': [
            ('amenity', 'school'),
            ('amenity', 'kindergarten'),
            ('amenity', 'university'),
            ('amenity', 'college'),
            ('amenity', 'library'),
        ],
        'elements': ['node', 'way', 'relation']
    },
    'station': {
        'tags': [
            ('railway', 'station'),
            ('amenity', 'ferry_terminal'),
            ('public_transport', 'station', 'station', 'ferry'),
            ('aeroway', 'aerodrome'),
        ],
        'elements': ['node', 'way', 'relation']
    },
    'supermarket': {
        'tags': [('shop', 'supermarket')],
        'elements': ['node', 'way', 'relation']
    },
    'mall': {
        'tags': [('shop', 'mall')],
        'elements': ['node', 'way', 'relation']
    },
    'bakery': {
        'tags': [('shop', 'bakery')],
        'elements': ['node', 'way', 'relation']
    },
    'leisure': {
        'tags': [
            ('leisure', 'sports_centre'),
            ('leisure', 'fitness_centre'),
            ('leisure', 'stadium'),
            ('amenity', 'cinema'),
            ('amenity', 'theatre'),
            ('tourism', 'museum'),
            ('leisure', 'park'),
            ('amenity', 'music_venue'),
        ],
        'elements': ['node', 'way', 'relation']
    },
    'restaurant': {
        'tags': [('amenity', 'restaurant')],
        'elements': ['node', 'way', 'relation']
    },
    'factory': {
        'tags': [
            ('landuse', 'industrial'),
            ('landuse', 'warehouse'),
        ],
        'elements': ['node', 'way', 'relation']
    },
    'hospital': {
        'tags': [
            ('amenity', 'hospital'),
            ('amenity', 'clinic'),
            ('amenity', 'doctors'),
            ('amenity', 'pharmacy'),
        ],
        'elements': ['node', 'way', 'relation']
    },
    'fire_station': {
        'tags': [('amenity', 'fire_station')],
        'elements': ['node', 'way', 'relation']
    },
    'police_station': {
        'tags': [('amenity', 'police')],
        'elements': ['node', 'way', 'relation']
    },
    'residential_zone': {
        'tags': [('landuse', 'residential')],
        'elements': ['way', 'relation']
    },
    'commercial_zone': {
        'tags': [('landuse', 'commercial')],
        'elements': ['way', 'relation']
    },
    'industrial_zone': {
        'tags': [('landuse', 'industrial')],
        'elements': ['way', 'relation']
    },
    'forest_zone': {
        'tags': [('landuse', 'forest')],
        'elements': ['way', 'relation']
    },
    'farmland_zone': {
        'tags': [('landuse', 'farmland')],
        'elements': ['way', 'relation']
    },
}


def build_overpass_filter(tag_tuple, poly_coords):
    """
    Construit un filtre Overpass à partir d'un tuple de tags.
    Supporte les tags simples (key, value) et composés (key1, value1, key2, value2).
    """
    if len(tag_tuple) == 2:
        return f'["{tag_tuple[0]}"="{tag_tuple[1]}"](poly:"{poly_coords}")'
    elif len(tag_tuple) == 4:
        return f'["{tag_tuple[0]}"="{tag_tuple[1]}"]["{tag_tuple[2]}"="{tag_tuple[3]}"](poly:"{poly_coords}")'
    return ''


def build_query_section(data_type, poly_coords):
    """
    Construit une section de requête Overpass pour un type de données.
    """
    config = OSM_DATA_CONFIG.get(data_type)
    if not config:
        return ''
    
    lines = []
    for tag_tuple in config['tags']:
        filter_str = build_overpass_filter(tag_tuple, poly_coords)
        for element in config['elements']:
            lines.append(f'  {element}{filter_str};')
    
    return '\n'.join(lines) + '\n'


def extract_polygon_coords(zone):
    """
    Extrait et formate les coordonnées d'un polygone GeoJSON pour Overpass.
    Retourne les coordonnées au format "lat lon lat lon ..." ou None si invalide.
    """
    coords = zone.get('coordinates', [[]])[0]
    if not coords or len(coords) < 3:
        return None
    
    # Format Overpass: lat lon (inversé par rapport à GeoJSON qui est lng lat)
    # Exclure le dernier point (doublon de fermeture du polygone)
    return " ".join([f"{coord[1]} {coord[0]}" for coord in coords[:-1]])


def GetEnchancedData(request):
    """
    Vue pour récupérer des données enrichies depuis l'API Overpass.
    
    Paramètres GET:
        zone: GeoJSON du polygone de la zone à analyser (requis)
        school, station, supermarket, etc.: 'true' pour inclure ce type de données
    """
    zone_json = request.GET.get('zone', None)
    if not zone_json:
        return JsonResponse({'error': 'Zone parameter is required'}, status=400)
    
    try:
        zone = json.loads(zone_json)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid zone GeoJSON'}, status=400)

    poly_coords = extract_polygon_coords(zone)
    if not poly_coords:
        return JsonResponse({'error': 'Invalid polygon coordinates'}, status=400)
    
    # Construire la requête Overpass
    query_parts = ['[out:json][timeout:60];', '(']
    
    for data_type in OSM_DATA_CONFIG.keys():
        if request.GET.get(data_type, 'false').lower() == 'true':
            query_parts.append(build_query_section(data_type, poly_coords))
    
    query_parts.append(');')
    query_parts.append('out geom;')
    
    query = '\n'.join(query_parts)

    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=60
        )
        response.raise_for_status()

        from tasks import run_spark_job
        run_spark_job.delay(response.text, "map_data_process.py")

        return JsonResponse("Données traitées avec succès", status=200, safe=False)

    except requests.exceptions.Timeout:
        return JsonResponse({'error': 'La requête a pris trop de temps (timeout)'}, status=504)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Overpass API error: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

