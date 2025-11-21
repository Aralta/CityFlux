"""
Gestionnaire de base de données PostGIS pour la carte interactive
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from typing import Dict, List, Optional, Tuple
import os


class DatabaseManager:
    """
    Gestionnaire de connexion et requêtes à la base PostGIS
    """
    
    def __init__(self):
        """
        Initialisation de la connexion à la base de données
        """
        self.connection_params = {
            'host': os.getenv('SQL_HOST', 'db'),
            'port': os.getenv('SQL_PORT', '5432'),
            'database': os.getenv('SQL_DB', 'mobilite'),
            'user': os.getenv('SQL_USER', 'postgres'),
            'password': os.getenv('SQL_PASSWORD', 'postgres')
        }
        self.conn = None
    
    def connect(self):
        """Établir la connexion à la base de données"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            return True
        except Exception as e:
            print(f"Erreur de connexion à la base de données: {e}")
            return False
    
    def disconnect(self):
        """Fermer la connexion à la base de données"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """
        Exécuter une requête SQL et retourner les résultats
        
        Args:
            query: Requête SQL à exécuter
            params: Paramètres de la requête (optionnel)
        
        Returns:
            Liste de dictionnaires contenant les résultats
        """
        if not self.conn:
            if not self.connect():
                return None
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            print(f"Erreur lors de l'exécution de la requête: {e}")
            return None
    
    def get_bbox_filter(self, bbox: Tuple[float, float, float, float]) -> str:
        """
        Créer un filtre PostGIS pour une bounding box
        
        Args:
            bbox: Tuple (min_lng, min_lat, max_lng, max_lat)
        
        Returns:
            Clause WHERE PostGIS pour filtrer par bbox
        """
        min_lng, min_lat, max_lng, max_lat = bbox
        return f"ST_Intersects(geom, ST_MakeEnvelope({min_lng}, {min_lat}, {max_lng}, {max_lat}, 4326))"
    
    def simplify_geometry(self, zoom_level: int) -> str:
        """
        Déterminer le niveau de simplification selon le zoom
        
        Args:
            zoom_level: Niveau de zoom de la carte (1-20)
        
        Returns:
            Fragment SQL pour simplifier la géométrie
        """
        # Plus le zoom est faible, plus on simplifie
        if zoom_level <= 8:
            tolerance = 0.01  # Très simplifié
        elif zoom_level <= 12:
            tolerance = 0.001  # Simplifié
        elif zoom_level <= 15:
            tolerance = 0.0001  # Peu simplifié
        else:
            tolerance = 0  # Pas de simplification
        
        if tolerance > 0:
            return f"ST_Simplify(geom, {tolerance})"
        return "geom"
    
    # ========================================================================
    # TRAJECTOIRES GNSS
    # ========================================================================
    
    def get_trajectories_gnss(self, bbox: Tuple[float, float, float, float], 
                              zoom: int, limit: int = 1000) -> Dict:
        """
        Récupérer les trajectoires GNSS dans la zone visible
        
        Args:
            bbox: Bounding box (min_lng, min_lat, max_lng, max_lat)
            zoom: Niveau de zoom
            limit: Nombre maximum de points à retourner
        
        Returns:
            GeoJSON FeatureCollection
        """
        geom_field = self.simplify_geometry(zoom)
        bbox_filter = self.get_bbox_filter(bbox)
        
        query = f"""
        SELECT 
            trajectory_id,
            user_id,
            timestamp,
            speed,
            ST_AsGeoJSON({geom_field})::json AS geometry
        FROM trajectory_gnss
        WHERE {bbox_filter}
        ORDER BY timestamp DESC
        LIMIT %s
        """
        
        results = self.execute_query(query, (limit,))
        return self._to_geojson(results, 'trajectory')
    
    def get_trajectories_gnss_aggregated(self, bbox: Tuple[float, float, float, float],
                                         zoom: int, grid_size: float = 0.01) -> Dict:
        """
        Récupérer les trajectoires GNSS agrégées par grille (pour zoom faible)
        
        Args:
            bbox: Bounding box
            zoom: Niveau de zoom
            grid_size: Taille de la grille en degrés
        
        Returns:
            GeoJSON avec densité par cellule
        """
        bbox_filter = self.get_bbox_filter(bbox)
        
        query = f"""
        SELECT 
            COUNT(*) as count,
            AVG(speed) as avg_speed,
            ST_AsGeoJSON(ST_Centroid(
                ST_SnapToGrid(geom, {grid_size})
            ))::json AS geometry
        FROM trajectory_gnss
        WHERE {bbox_filter}
        GROUP BY ST_SnapToGrid(geom, {grid_size})
        HAVING COUNT(*) > 5
        """
        
        results = self.execute_query(query)
        return self._to_geojson(results, 'heatmap')
    
    # ========================================================================
    # TRAJECTOIRES TÉLÉCOM
    # ========================================================================
    
    def get_trajectories_telecom(self, bbox: Tuple[float, float, float, float],
                                 zoom: int, limit: int = 1000) -> Dict:
        """
        Récupérer les trajectoires télécom dans la zone visible
        """
        geom_field = self.simplify_geometry(zoom)
        bbox_filter = self.get_bbox_filter(bbox)
        
        query = f"""
        SELECT 
            trajectory_id,
            user_id,
            timestamp,
            ST_AsGeoJSON({geom_field.replace('geom', 'approximate_geom')})::json AS geometry
        FROM trajectory_telecom
        WHERE {bbox_filter.replace('geom', 'approximate_geom')}
        ORDER BY timestamp DESC
        LIMIT %s
        """
        
        results = self.execute_query(query, (limit,))
        return self._to_geojson(results, 'trajectory')
    
    # ========================================================================
    # MATRICE ORIGINE-DESTINATION
    # ========================================================================
    
    def get_od_matrix(self, bbox: Tuple[float, float, float, float],
                      start_time: str = None, end_time: str = None) -> Dict:
        """
        Récupérer les flux origine-destination
        
        Args:
            bbox: Bounding box
            start_time: Heure de début (format ISO)
            end_time: Heure de fin (format ISO)
        
        Returns:
            GeoJSON avec lignes représentant les flux
        """
        bbox_filter = self.get_bbox_filter(bbox)
        time_filter = ""
        params = []
        
        if start_time and end_time:
            time_filter = "AND start_time BETWEEN %s AND %s"
            params = [start_time, end_time]
        
        query = f"""
        SELECT 
            od.od_id,
            od.trip_count,
            od.avg_duration,
            od.avg_distance,
            zo.nom as origin_name,
            zd.nom as destination_name,
            ST_AsGeoJSON(
                ST_MakeLine(
                    ST_Centroid(zo.geom),
                    ST_Centroid(zd.geom)
                )
            )::json AS geometry
        FROM matrix_od od
        JOIN zone zo ON od.origin_zone = zo.id
        JOIN zone zd ON od.destination_zone = zd.id
        WHERE ({bbox_filter.replace('geom', 'zo.geom')} 
               OR {bbox_filter.replace('geom', 'zd.geom')})
        {time_filter}
        ORDER BY od.trip_count DESC
        LIMIT 500
        """
        
        results = self.execute_query(query, tuple(params) if params else None)
        return self._to_geojson(results, 'od_flow')
    
    # ========================================================================
    # TRANSPORT PUBLIC
    # ========================================================================
    
    def get_arrets(self, bbox: Tuple[float, float, float, float],
                   type_transport: str = None) -> Dict:
        """
        Récupérer les arrêts de transport dans la zone
        
        Args:
            bbox: Bounding box
            type_transport: Filtrer par type (Bus, Tram, etc.)
        
        Returns:
            GeoJSON FeatureCollection des arrêts
        """
        bbox_filter = self.get_bbox_filter(bbox)
        type_filter = ""
        params = []
        
        if type_transport:
            type_filter = "AND t.nom = %s"
            params = [type_transport]
        
        query = f"""
        SELECT 
            a.id_arret,
            a.nom,
            t.nom as type_transport,
            ST_AsGeoJSON(a.position)::json AS geometry,
            COUNT(DISTINCT al.id_ligne) as nb_lignes
        FROM arret a
        LEFT JOIN type_transport t ON a.id_type = t.id
        LEFT JOIN arret_ligne al ON a.id_arret = al.id_arret
        WHERE {bbox_filter.replace('geom', 'a.position')}
        {type_filter}
        GROUP BY a.id_arret, a.nom, t.nom, a.position
        """
        
        results = self.execute_query(query, tuple(params) if params else None)
        return self._to_geojson(results, 'stop')
    
    def get_lignes(self, bbox: Tuple[float, float, float, float],
                   type_transport: str = None) -> Dict:
        """
        Récupérer les lignes de transport traversant la zone
        
        Returns:
            GeoJSON avec les tracés des lignes
        """
        bbox_filter = self.get_bbox_filter(bbox)
        type_filter = ""
        params = []
        
        if type_transport:
            type_filter = "AND t.nom = %s"
            params = [type_transport]
        
        query = f"""
        SELECT DISTINCT
            l.id,
            l.nom,
            t.nom as type_transport,
            l.capacity,
            ST_AsGeoJSON(
                ST_MakeLine(a.position ORDER BY al.id)
            )::json AS geometry
        FROM ligne l
        JOIN type_transport t ON l.id_type = t.id
        JOIN arret_ligne al ON l.id = al.id_ligne
        JOIN arret a ON al.id_arret = a.id_arret
        WHERE {bbox_filter.replace('geom', 'a.position')}
        {type_filter}
        GROUP BY l.id, l.nom, t.nom, l.capacity
        """
        
        results = self.execute_query(query, tuple(params) if params else None)
        return self._to_geojson(results, 'line')
    
    # ========================================================================
    # POINTS D'INTÉRÊT
    # ========================================================================
    
    def get_poi(self, bbox: Tuple[float, float, float, float],
                poi_type: str = None, limit: int = 500) -> Dict:
        """
        Récupérer les points d'intérêt dans la zone
        
        Args:
            bbox: Bounding box
            poi_type: Filtrer par type de POI
            limit: Nombre maximum de POI
        
        Returns:
            GeoJSON FeatureCollection des POI
        """
        bbox_filter = self.get_bbox_filter(bbox)
        type_filter = ""
        params = [limit]
        
        if poi_type:
            type_filter = "AND type = %s"
            params.insert(0, poi_type)
        
        query = f"""
        SELECT 
            id,
            nom,
            type,
            ST_AsGeoJSON(position)::json AS geometry
        FROM poi
        WHERE {bbox_filter.replace('geom', 'position')}
        {type_filter}
        LIMIT %s
        """
        
        results = self.execute_query(query, tuple(params))
        return self._to_geojson(results, 'poi')
    
    # ========================================================================
    # ZONES
    # ========================================================================
    
    def get_zones(self, bbox: Tuple[float, float, float, float],
                  zone_type: str = None) -> Dict:
        """
        Récupérer les zones géographiques
        
        Args:
            bbox: Bounding box
            zone_type: Filtrer par type de zone
        
        Returns:
            GeoJSON FeatureCollection des zones
        """
        bbox_filter = self.get_bbox_filter(bbox)
        type_filter = ""
        params = []
        
        if zone_type:
            type_filter = "AND type = %s"
            params = [zone_type]
        
        query = f"""
        SELECT 
            id,
            nom,
            type,
            ST_AsGeoJSON(ST_Simplify(geom, 0.0001))::json AS geometry
        FROM zone
        WHERE {bbox_filter}
        {type_filter}
        LIMIT 100
        """
        
        results = self.execute_query(query, tuple(params) if params else None)
        return self._to_geojson(results, 'zone')
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def _to_geojson(self, results: List[Dict], feature_type: str) -> Dict:
        """
        Convertir les résultats SQL en GeoJSON
        
        Args:
            results: Résultats de la requête
            feature_type: Type de feature pour les propriétés
        
        Returns:
            GeoJSON FeatureCollection
        """
        if not results:
            return {
                'type': 'FeatureCollection',
                'features': []
            }
        
        features = []
        for row in results:
            # Extraire la géométrie
            geometry = row.pop('geometry', None)
            
            # Le reste devient les propriétés
            properties = {k: v for k, v in row.items()}
            properties['feature_type'] = feature_type
            
            feature = {
                'type': 'Feature',
                'geometry': geometry,
                'properties': properties
            }
            features.append(feature)
        
        return {
            'type': 'FeatureCollection',
            'features': features
        }
    
    def get_statistics(self, bbox: Tuple[float, float, float, float]) -> Dict:
        """
        Obtenir des statistiques sur les données dans la zone
        
        Returns:
            Dictionnaire avec les comptages par type de données
        """
        bbox_filter = self.get_bbox_filter(bbox)
        
        stats = {}
        
        # Compter les trajectoires GNSS
        query = f"SELECT COUNT(*) as count FROM trajectory_gnss WHERE {bbox_filter}"
        result = self.execute_query(query)
        stats['gnss_trajectories'] = result[0]['count'] if result else 0
        
        # Compter les arrêts
        query = f"SELECT COUNT(*) as count FROM arret WHERE {bbox_filter.replace('geom', 'position')}"
        result = self.execute_query(query)
        stats['stops'] = result[0]['count'] if result else 0
        
        # Compter les POI
        query = f"SELECT COUNT(*) as count FROM poi WHERE {bbox_filter.replace('geom', 'position')}"
        result = self.execute_query(query)
        stats['poi'] = result[0]['count'] if result else 0
        
        return stats


# Instance globale du gestionnaire
db_manager = DatabaseManager()
