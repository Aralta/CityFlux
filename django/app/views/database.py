"""
Gestionnaire de base de données PostGIS pour la carte interactive.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple
import os


# Configuration de simplification géométrique selon le zoom
ZOOM_TOLERANCE = {
    'low': (8, 0.01),      # zoom <= 8
    'medium': (12, 0.001), # zoom <= 12
    'high': (15, 0.0001),  # zoom <= 15
    'full': (20, 0)        # zoom > 15
}

# Configuration des limites adaptatives selon le zoom
ZOOM_LIMITS = {
    10: 100,
    14: 500,
    20: 1000
}


class DatabaseManager:
    """Gestionnaire de connexion et requêtes à la base PostGIS."""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('SQL_HOST', 'db'),
            'port': os.getenv('SQL_PORT', '5432'),
            'database': os.getenv('SQL_DB', 'mobilite'),
            'user': os.getenv('SQL_USER', 'postgres'),
            'password': os.getenv('SQL_PASSWORD', 'postgres')
        }
        self.conn = None
    
    def connect(self) -> bool:
        """Établir la connexion à la base de données."""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            return True
        except Exception:
            return False
    
    def disconnect(self):
        """Fermer la connexion à la base de données."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """Exécuter une requête SQL et retourner les résultats."""
        if not self.conn and not self.connect():
            return None
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return None
    
    # ========================================================================
    # UTILITAIRES DE REQUÊTE
    # ========================================================================
    
    def _bbox_filter(self, bbox: Tuple[float, float, float, float], 
                     geom_col: str = 'geom', buffer: float = 0.1) -> str:
        """Créer un filtre PostGIS pour une bounding box."""
        min_lng, min_lat, max_lng, max_lat = bbox
        lng_buf = (max_lng - min_lng) * buffer
        lat_buf = (max_lat - min_lat) * buffer
        
        return (f"ST_Intersects({geom_col}, ST_MakeEnvelope("
                f"{min_lng - lng_buf}, {min_lat - lat_buf}, "
                f"{max_lng + lng_buf}, {max_lat + lat_buf}, 4326))")
    
    def _simplify_expr(self, zoom: int, geom_col: str = 'geom', preserve: bool = False) -> str:
        """Déterminer l'expression de simplification selon le zoom."""
        tolerance = 0
        for max_zoom, tol in sorted(ZOOM_TOLERANCE.values()):
            if zoom <= max_zoom:
                tolerance = tol
                break
        
        if tolerance == 0:
            return geom_col
        
        func = 'ST_SimplifyPreserveTopology' if preserve else 'ST_Simplify'
        return f"{func}({geom_col}, {tolerance})"
    
    def _adaptive_limit(self, zoom: int, default: int = 1000) -> int:
        """Calculer une limite adaptative selon le zoom."""
        for max_zoom, limit in sorted(ZOOM_LIMITS.items()):
            if zoom <= max_zoom:
                return min(default, limit)
        return default
    
    def _to_geojson(self, results: List[Dict], feature_type: str) -> Dict:
        """Convertir les résultats SQL en GeoJSON."""
        if not results:
            return {'type': 'FeatureCollection', 'features': []}
        
        features = []
        for row in results:
            geometry = row.pop('geometry', None)
            if geometry is None:
                continue
            
            properties = dict(row)
            if 'feature_type' not in properties:
                properties['feature_type'] = feature_type
            
            features.append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': properties
            })
        
        return {'type': 'FeatureCollection', 'features': features}
    
    def _build_filters(self, conditions: Dict[str, any]) -> Tuple[str, List]:
        """Construire les filtres WHERE et les paramètres."""
        filters = []
        params = []
        
        for field, value in conditions.items():
            if value is not None:
                if isinstance(value, list):
                    if value and 'Tous' not in value and 'Toutes' not in value:
                        placeholders = ', '.join(['%s'] * len(value))
                        filters.append(f"{field} IN ({placeholders})")
                        params.extend(value)
                    elif not value:
                        # Si une liste vide est fournie, on ne veut rien retourner
                        filters.append("1=0") 
                elif value not in ['Tous', 'Toutes']:
                    filters.append(f"{field} = %s")
                    params.append(value)
        
        filter_str = " AND " + " AND ".join(filters) if filters else ""
        return filter_str, params
    
    def _get_distinct_values(self, table: str, column: str, 
                             filter_col: str = None, filter_val: str = None) -> List[str]:
        """Récupérer les valeurs distinctes d'une colonne."""
        if filter_col and filter_val:
            query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL AND {filter_col} = %s ORDER BY {column}"
            results = self.execute_query(query, (filter_val,))
        else:
            query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column}"
            results = self.execute_query(query)
        
        return [r[column] for r in results] if results else []
    
    # ========================================================================
    # TRAJECTOIRES GNSS
    # ========================================================================
    
    def get_trajectories_gnss(self, bbox: Tuple, zoom: int, limit: int = 100, 
                             trajectory_ids: List[str] = None) -> Dict:
        """Récupérer les trajectoires GNSS (lignes et points) avec filtrage optionnel."""
        limit_lines = limit
        limit_points = limit * 5
        
        # Filtres supplémentaires
        extra_filter = ""
        extra_params = []
        if trajectory_ids:
            placeholders = ', '.join(['%s'] * len(trajectory_ids))
            extra_filter = f" AND trajectory_id IN ({placeholders})"
            extra_params = trajectory_ids

        # 1. Trajectoires (Lignes)
        query_lines = f"""
        SELECT trajectory_id, user_id, AVG(speed) as speed, 'trajectory' as feature_type,
               ST_AsGeoJSON(ST_MakeLine(geom ORDER BY timestamp))::json AS geometry
        FROM trajectory_gnss
        WHERE {self._bbox_filter(bbox)} {extra_filter}
        GROUP BY trajectory_id, user_id
        HAVING COUNT(*) > 1
        LIMIT %s
        """
        lines = self.execute_query(query_lines, tuple(extra_params + [limit_lines])) or []
        
        # 2. Points individuels (même si cachés en JS, on les garde en API si besoin)
        query_points = f"""
        SELECT trajectory_id, user_id, speed, timestamp, 'point' as feature_type,
               ST_AsGeoJSON(geom)::json AS geometry
        FROM trajectory_gnss
        WHERE {self._bbox_filter(bbox)} {extra_filter}
        LIMIT %s
        """
        points = self.execute_query(query_points, tuple(extra_params + [limit_points])) or []
        
        return self._to_geojson(lines + points, 'mixed')
    
    def get_trajectories_gnss_aggregated(self, bbox: Tuple, zoom: int, grid_size: float = 0.01) -> Dict:
        """Récupérer les trajectoires GNSS agrégées par grille."""
        query = f"""
        SELECT COUNT(*) as count, AVG(speed) as avg_speed,
               ST_AsGeoJSON(ST_Centroid(ST_SnapToGrid(geom, {grid_size})))::json AS geometry
        FROM trajectory_gnss
        WHERE {self._bbox_filter(bbox)}
        GROUP BY ST_SnapToGrid(geom, {grid_size})
        HAVING COUNT(*) > 5
        """
        return self._to_geojson(self.execute_query(query), 'heatmap')
    
    # ========================================================================
    # TRAJECTOIRES TÉLÉCOM
    # ========================================================================
    
    def get_trajectories_telecom(self, bbox: Tuple, zoom: int, limit: int = 1000) -> Dict:
        """Récupérer les trajectoires télécom dans la zone visible."""
        query = f"""
        SELECT trajectory_id, user_id, timestamp,
               ST_AsGeoJSON({self._simplify_expr(zoom, 'approximate_geom')})::json AS geometry
        FROM trajectory_telecom
        WHERE {self._bbox_filter(bbox, 'approximate_geom')}
        ORDER BY timestamp DESC LIMIT %s
        """
        return self._to_geojson(self.execute_query(query, (limit,)), 'trajectory')
    
    # ========================================================================
    # MATRICE ORIGINE-DESTINATION
    # ========================================================================
    
    def get_od_matrix(self, bbox: Tuple, start_time: str = None, end_time: str = None) -> Dict:
        """Récupérer les flux origine-destination."""
        time_filter = ""
        params = []
        
        if start_time and end_time:
            time_filter = "AND start_time BETWEEN %s AND %s"
            params = [start_time, end_time]
        
        bbox_zo = self._bbox_filter(bbox, 'zo.geom')
        bbox_zd = self._bbox_filter(bbox, 'zd.geom')
        
        query = f"""
        SELECT od.od_id, od.trip_count, od.avg_duration, od.avg_distance,
               zo.nom as origin_name, zd.nom as destination_name,
               ST_AsGeoJSON(ST_MakeLine(ST_Centroid(zo.geom), ST_Centroid(zd.geom)))::json AS geometry
        FROM matrix_od od
        JOIN zone zo ON od.origin_zone = zo.id
        JOIN zone zd ON od.destination_zone = zd.id
        WHERE ({bbox_zo} OR {bbox_zd}) {time_filter}
        ORDER BY od.trip_count DESC LIMIT 500
        """
        return self._to_geojson(self.execute_query(query, tuple(params) if params else None), 'od_flow')
    
    # ========================================================================
    # TRANSPORT PUBLIC
    # ========================================================================
    
    def get_arrets(self, bbox: Tuple, type_transport: str = None) -> Dict:
        """Récupérer les arrêts de transport dans la zone."""
        type_filter, params = self._build_filters({'t.nom': type_transport})
        
        query = f"""
        SELECT a.id_arret, a.nom, t.nom as type_transport,
               ST_AsGeoJSON(a.position)::json AS geometry,
               COUNT(DISTINCT al.id_ligne) as nb_lignes
        FROM arret a
        LEFT JOIN type_transport t ON a.id_type = t.id
        LEFT JOIN arret_ligne al ON a.id_arret = al.id_arret
        WHERE {self._bbox_filter(bbox, 'a.position')} {type_filter}
        GROUP BY a.id_arret, a.nom, t.nom, a.position
        """
        return self._to_geojson(self.execute_query(query, tuple(params) if params else None), 'stop')
    
    def get_lignes(self, bbox: Tuple, type_transport: str = None) -> Dict:
        """Récupérer les lignes de transport traversant la zone."""
        type_filter, params = self._build_filters({'t.nom': type_transport})
        
        query = f"""
        SELECT DISTINCT l.id, l.nom, t.nom as type_transport, l.capacity,
               ST_AsGeoJSON(ST_MakeLine(a.position ORDER BY al.id))::json AS geometry
        FROM ligne l
        JOIN type_transport t ON l.id_type = t.id
        JOIN arret_ligne al ON l.id = al.id_ligne
        JOIN arret a ON al.id_arret = a.id_arret
        WHERE {self._bbox_filter(bbox, 'a.position')} {type_filter}
        GROUP BY l.id, l.nom, t.nom, l.capacity
        """
        return self._to_geojson(self.execute_query(query, tuple(params) if params else None), 'line')
    
    # ========================================================================
    # POINTS D'INTÉRÊT
    # ========================================================================
    
    def get_poi(self, bbox: Tuple, poi_types: List[str] = None, 
                poi_subtypes: List[str] = None, zoom: int = 14, limit: int = 1000) -> Dict:
        """Récupérer les points d'intérêt dans la zone."""
        type_filter, params = self._build_filters({'type': poi_types, 'subtype': poi_subtypes})
        adaptive_limit = self._adaptive_limit(zoom, limit)
        params.append(adaptive_limit)
        
        query = f"""
        SELECT id, nom, type, subtype, description,
               ST_AsGeoJSON(position)::json AS geometry
        FROM poi
        WHERE {self._bbox_filter(bbox, 'position')} {type_filter}
        LIMIT %s
        """
        return self._to_geojson(self.execute_query(query, tuple(params)), 'poi')
    
    # ========================================================================
    # ZONES
    # ========================================================================
    
    def get_zones(self, bbox: Tuple, zone_types: List[str] = None,
                  zone_subtypes: List[str] = None, zoom: int = 14, limit: int = 200) -> Dict:
        """Récupérer les zones géographiques avec simplification adaptative."""
        type_filter, params = self._build_filters({'type': zone_types, 'subtype': zone_subtypes})
        params.append(limit)
        
        geom_expr = self._simplify_expr(zoom, preserve=True)
        
        query = f"""
        SELECT id, type, subtype, description,
               ST_AsGeoJSON({geom_expr})::json AS geometry
        FROM zone
        WHERE {self._bbox_filter(bbox)} {type_filter}
        ORDER BY ST_Area(geom) DESC LIMIT %s
        """
        return self._to_geojson(self.execute_query(query, tuple(params)), 'zone')
    
    # ========================================================================
    # ACCESSEURS TYPES/SUBTYPES
    # ========================================================================
    
    def get_poi_types(self) -> List[str]:
        return self._get_distinct_values('poi', 'type')
    
    def get_poi_subtypes(self, poi_type: str = None) -> List[str]:
        return self._get_distinct_values('poi', 'subtype', 'type', poi_type)
    
    def get_zone_types(self) -> List[str]:
        return self._get_distinct_values('zone', 'type')
    
    def get_zone_subtypes(self, zone_type: str = None) -> List[str]:
        return self._get_distinct_values('zone', 'subtype', 'type', zone_type)

    def get_trajectory_ids(self) -> List[str]:
        """Récupérer tous les identifiants de trajectoires disponibles."""
        return self._get_distinct_values('trajectory_gnss', 'trajectory_id')

    def get_poi_structure(self) -> Dict[str, List[str]]:
        """Récupérer la hiérarchie type -> subtypes pour les POI."""
        query = "SELECT DISTINCT type, subtype FROM poi WHERE type IS NOT NULL AND subtype IS NOT NULL ORDER BY type, subtype"
        results = self.execute_query(query)
        structure = {}
        if results:
            for row in results:
                t, st = row['type'], row['subtype']
                if t not in structure: structure[t] = []
                structure[t].append(st)
        return structure

    def get_zone_structure(self) -> Dict[str, List[str]]:
        """Récupérer la hiérarchie type -> subtypes pour les zones."""
        query = "SELECT DISTINCT type, subtype FROM zone WHERE type IS NOT NULL AND subtype IS NOT NULL ORDER BY type, subtype"
        results = self.execute_query(query)
        structure = {}
        if results:
            for row in results:
                t, st = row['type'], row['subtype']
                if t not in structure: structure[t] = []
                structure[t].append(st)
        return structure
    
    # ========================================================================
    # STATISTIQUES
    # ========================================================================
    
    def get_statistics(self, bbox: Tuple) -> Dict:
        """Obtenir des statistiques sur les données dans la zone."""
        tables = {
            'gnss_trajectories': ('trajectory_gnss', 'geom'),
            'stops': ('arret', 'position'),
            'poi': ('poi', 'position')
        }
        
        stats = {}
        for key, (table, geom_col) in tables.items():
            query = f"SELECT COUNT(*) as count FROM {table} WHERE {self._bbox_filter(bbox, geom_col)}"
            result = self.execute_query(query)
            stats[key] = result[0]['count'] if result else 0
        
        return stats


# Instance globale
db_manager = DatabaseManager()
