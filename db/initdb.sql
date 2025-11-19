-- Activation de PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Table des types de transport
CREATE TABLE type_transport (
    id SERIAL PRIMARY KEY,
    nom TEXT UNIQUE NOT NULL
);

-- Table des arrêts
CREATE TABLE arret (
    id SERIAL PRIMARY KEY,
    nom TEXT NOT NULL,
    position GEOMETRY(Point, 4326),
    id_type INTEGER REFERENCES type_transport(id)
);

-- Table des lignes de transport
CREATE TABLE ligne (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    id_type INTEGER REFERENCES type_transport(id),
    capacite INTEGER
);

-- Table de liaison arrêt ↔ ligne (many-to-many)
CREATE TABLE arret_ligne (
    id SERIAL PRIMARY KEY,
    id_arret INTEGER REFERENCES arret(id) ON DELETE CASCADE,
    id_ligne TEXT REFERENCES ligne(id) ON DELETE CASCADE
);

-- Table des horaires
CREATE TABLE horaire (
    id SERIAL PRIMARY KEY,
    id_arret_ligne INTEGER REFERENCES arret_ligne(id),
    num_passage INTEGER,
    horaire TIME
);

-- POI (Points d'Intérêt)
CREATE TABLE poi (
    id SERIAL PRIMARY KEY,
    nom TEXT,
    position GEOMETRY(Point, 4326),
    type TEXT
);

-- Zones (polygones : quartiers, zones d'étude, etc.)
CREATE TABLE zone (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(Polygon, 4326),
    type TEXT
);

-- Indexes spatiaux (important pour les perfs)
CREATE INDEX idx_arret_position ON arret USING GIST(position);
CREATE INDEX idx_poi_position ON poi USING GIST(position);
CREATE INDEX idx_zone_geom ON zone USING GIST(geom);

-- Données de typr de transport de base
INSERT INTO type_transport (nom) VALUES 
('Bus'), ('Tram'), ('Métro'), ('Train'), ('Vélo'), ('Marche'), ('Voiture')
ON CONFLICT (nom) DO NOTHING;