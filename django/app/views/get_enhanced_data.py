import requests
import json
from django.http import JsonResponse


def GetEnchancedData (request):
    """
    View to get enhanced data based on request parameters.
    """
    zone_json = request.GET.get('zone', None)
    if not zone_json:
        return JsonResponse({'error': 'Zone parameter is required'}, status=400)
    
    try:
        zone = json.loads(zone_json)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid zone GeoJSON'}, status=400)

    # Liste des paramètres à inclure avec leurs fonctions
    includes_config = [
        ('school', include_schools),
        ('station', include_stations),
        ('supermarket', include_supermarkets),
        ('mall', include_malls),
        ('bakery', include_bakeries),
        ('leisure', include_leisure_centers),
        ('restaurant', include_restaurants),
        ('factory', include_factories),
        ('hospital', include_hospitals),
        ('fire_station', include_fire_stations),
        ('police_station', include_police_stations),
        ('residential_zone', include_residential_zones),
        ('commercial_zone', include_commercial_zones),
        ('industrial_zone', include_industrial_zones),
        ('forest_zone', include_forest_zones),
        ('farmland_zone', include_farmland_zones),
    ]

    # Extraire les coordonnées du polygone
    coords = zone.get('coordinates', [[]])[0]
    if not coords or len(coords) < 3:
        return JsonResponse({'error': 'Invalid polygon coordinates'}, status=400)
    
    # Formater les coordonnées pour Overpass (lat lon, pas lng lat)
    poly_coords = " ".join([f"{coord[1]} {coord[0]}" for coord in coords[:-1]])  # Exclure le dernier point (doublon)
    
    # Construire la requête Overpass de base
    query = f"""[out:json][timeout:60];
(
"""
    
    # Ajouter les éléments demandés
    for param_name, func in includes_config:
        if request.GET.get(param_name, 'false').lower() == 'true':
            query += func(poly_coords)
    
    # Finaliser la requête
    query += """);
out center;"""

    print("🔍 Requête Overpass générée:")
    print(query[:500] + "..." if len(query) > 500 else query)

    print (query)

    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=30
        )
        response.raise_for_status()
        print("✅ Requête Overpass réussie.")
        with open('output.json', 'w') as f:
            f.write(response.text)
        print(response.text)
    except :
        print("❌ Erreur lors de la requête Overpass.")

    return JsonResponse({'status': 'success', 'message': 'Query executed'}, status=200)
'''
        return JsonResponse(response.json())
    except requests.exceptions.Timeout:
        return JsonResponse({'error': 'La requête a pris trop de temps (timeout)'}, status=504)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Overpass API error: {str(e)}'}, status=500)
'''


def include_schools(poly_coords):
    """Include schools data in the Overpass API request."""
    return f"""
  // Schools
  node["amenity"="school"](poly:"{poly_coords}");
  way["amenity"="school"](poly:"{poly_coords}");
  relation["amenity"="school"](poly:"{poly_coords}");
  node["amenity"="kindergarten"](poly:"{poly_coords}");
  way["amenity"="kindergarten"](poly:"{poly_coords}");
  relation["amenity"="kindergarten"](poly:"{poly_coords}");
  node["amenity"="university"](poly:"{poly_coords}");
  way["amenity"="university"](poly:"{poly_coords}");
  relation["amenity"="university"](poly:"{poly_coords}");
  node["amenity"="college"](poly:"{poly_coords}");
  way["amenity"="college"](poly:"{poly_coords}");
  relation["amenity"="college"](poly:"{poly_coords}");
  node["amenity"="library"](poly:"{poly_coords}");
  way["amenity"="library"](poly:"{poly_coords}");
  relation["amenity"="library"](poly:"{poly_coords}");
"""


def include_stations(poly_coords):
    """
    Include stations data in the Overpass API request
    """
    data = f'''
    node["railway"="station"](poly:"{poly_coords}");
    way["railway"="station"](poly:"{poly_coords}");
    relation["railway"="station"](poly:"{poly_coords}");

    node["amenity"="ferry_terminal"](poly:"{poly_coords}");
    way["amenity"="ferry_terminal"](poly:"{poly_coords}");
    relation["amenity"="ferry_terminal"](poly:"{poly_coords}");

    node["public_transport"="station"]["station"="ferry"](poly:"{poly_coords}");
    way["public_transport"="station"]["station"="ferry"](poly:"{poly_coords}");
    relation["public_transport"="station"]["station"="ferry"](poly:"{poly_coords}");

    node["aeroway"="aerodrome"](poly:"{poly_coords}");
    way["aeroway"="aerodrome"](poly:"{poly_coords}");
    relation["aeroway"="aerodrome"](poly:"{poly_coords}");

    '''
    return data

def include_supermarkets(poly_coords):
    """
    Include supermarkets data in the Overpass API request
    """
    data = f'''
    node["shop"="supermarket"](poly:"{poly_coords}");
    way["shop"="supermarket"](poly:"{poly_coords}");
    relation["shop"="supermarket"](poly:"{poly_coords}");
    '''
    return data

def include_malls(poly_coords):
    """
    Include malls data in the Overpass API request
    """
    data = f'''
    node["shop"="mall"](poly:"{poly_coords}");
    way["shop"="mall"](poly:"{poly_coords}");
    relation["shop"="mall"](poly:"{poly_coords}");
    '''
    return data

def include_bakeries(poly_coords):
    """
    Include bakeries data in the Overpass API request
    """

    data = f'''
    node["shop"="bakery"](poly:"{poly_coords}");
    way["shop"="bakery"](poly:"{poly_coords}");
    relation["shop"="bakery"](poly:"{poly_coords}");
    '''
    return data

def include_leisure_centers(poly_coords):
    """
    Include leisure centers data in the Overpass API request
    """
    data = f'''
    node["leisure"="sports_centre"](poly:"{poly_coords}");
    way["leisure"="sports_centre"](poly:"{poly_coords}");
    relation["leisure"="sports_centre"](poly:"{poly_coords}");

    node["leisure"="fitness_centre"](poly:"{poly_coords}");
    way["leisure"="fitness_centre"](poly:"{poly_coords}");
    relation["leisure"="fitness_centre"](poly:"{poly_coords}");

    node["leisure"="stadium"](poly:"{poly_coords}");
    way["leisure"="stadium"](poly:"{poly_coords}");
    relation["leisure"="stadium"](poly:"{poly_coords}");

    node["amenity"="cinema"](poly:"{poly_coords}");
    way["amenity"="cinema"](poly:"{poly_coords}");
    relation["amenity"="cinema"](poly:"{poly_coords}");

    node["amenity"="theatre"](poly:"{poly_coords}");
    way["amenity"="theatre"](poly:"{poly_coords}");
    relation["amenity"="theatre"](poly:"{poly_coords}");

    node["tourism"="museum"](poly:"{poly_coords}");
    way["tourism"="museum"](poly:"{poly_coords}");
    relation["tourism"="museum"](poly:"{poly_coords}");

    node["leisure"="park"](poly:"{poly_coords}");
    way["leisure"="park"](poly:"{poly_coords}");
    relation["leisure"="park"](poly:"{poly_coords}");

    node["amenity"="music_venue"](poly:"{poly_coords}");
    way["amenity"="music_venue"](poly:"{poly_coords}");
    relation["amenity"="music_venue"](poly:"{poly_coords}");

    '''
    return data

def include_restaurants(poly_coords):
    """
    Include restaurants data in the Overpass API request
    """
    data = f'''
    node["amenity"="restaurant"](poly:"{poly_coords}");
    way["amenity"="restaurant"](poly:"{poly_coords}");
    relation["amenity"="restaurant"](poly:"{poly_coords}");
    '''
    return data

def include_factories(poly_coords):
    """
    Include factories data in the Overpass API request
    """
    data = f'''
    node["landuse"="industrial"](poly:"{poly_coords}");
    way["landuse"="industrial"](poly:"{poly_coords}");
    relation["landuse"="industrial"](poly:"{poly_coords}");
    '''
    return data

def include_hospitals(poly_coords):
    """
    Include hospitals data in the Overpass API request
    """
    data = f'''
    node["amenity"="hospital"](poly:"{poly_coords}");
    way["amenity"="hospital"](poly:"{poly_coords}");
    relation["amenity"="hospital"](poly:"{poly_coords}");

    node["amenity"="clinic"](poly:"{poly_coords}");
    way["amenity"="clinic"](poly:"{poly_coords}");
    relation["amenity"="clinic"](poly:"{poly_coords}");
    
    node["amenity"="doctors"](poly:"{poly_coords}");
    way["amenity"="doctors"](poly:"{poly_coords}");
    relation["amenity"="doctors"](poly:"{poly_coords}");
    '''
    return data
    
def include_fire_stations(poly_coords):
    """
    Include fire stations data in the Overpass API request
    """
    data = f'''
    node["amenity"="fire_station"](poly:"{poly_coords}");
    way["amenity"="fire_station"](poly:"{poly_coords}");
    relation["amenity"="fire_station"](poly:"{poly_coords}");
    '''
    return data

def include_police_stations(poly_coords):
    """
    Include police stations data in the Overpass API request
    """
    data = f'''
    node["amenity"="police"](poly:"{poly_coords}");
    way["amenity"="police"](poly:"{poly_coords}");
    relation["amenity"="police"](poly:"{poly_coords}");
    '''
    return data

def include_residential_zones(poly_coords):
    """
    Include residential zones data in the Overpass API request
    """
    data = f'''
    way["landuse"="residential"](poly:"{poly_coords}");
    relation["landuse"="residential"](poly:"{poly_coords}");
    '''
    return data

def include_commercial_zones(poly_coords):
    """
    Include commercial zones data in the Overpass API request
    """
    data = f'''
    way["landuse"="commercial"](poly:"{poly_coords}");
    relation["landuse"="commercial"](poly:"{poly_coords}");
    '''
    return data

def include_industrial_zones(poly_coords):
    """
    Include industrial zones data in the Overpass API request
    """
    data = f'''
    way["landuse"="industrial"](poly:"{poly_coords}");
    relation["landuse"="industrial"](poly:"{poly_coords}");
    '''
    return data

def include_forest_zones(poly_coords):
    """
    Include forest zones data in the Overpass API request
    """
    data = f'''
    way["landuse"="forest"](poly:"{poly_coords}");
    relation["landuse"="forest"](poly:"{poly_coords}");
    '''
    return data

def include_farmland_zones(poly_coords):
    """
    Include farmland zones data in the Overpass API request
    """
    data = f'''
    way["landuse"="farmland"](poly:"{poly_coords}");
    relation["landuse"="farmland"](poly:"{poly_coords}");
    '''
    return data

