-- Schema + tiny dataset for unit tests
DROP TABLE IF EXISTS systems;
DROP TABLE IF EXISTS planets;
DROP TABLE IF EXISTS moons;

CREATE TABLE systems (
    id INTEGER PRIMARY KEY,
    name TEXT,
    x REAL,
    y REAL,
    z REAL,
    security REAL
);

CREATE TABLE planets (
    id INTEGER PRIMARY KEY,
    system_id INTEGER,
    name TEXT,
    orbit_index INTEGER,
    planet_type TEXT,
    FOREIGN KEY(system_id) REFERENCES systems(id)
);

CREATE TABLE moons (
    id INTEGER PRIMARY KEY,
    planet_id INTEGER,
    name TEXT,
    orbit_index INTEGER,
    FOREIGN KEY(planet_id) REFERENCES planets(id)
);

INSERT INTO systems (id, name, x, y, z, security) VALUES
(1, 'Alpha', 1000, 2000, 3000, 0.7),
(2, 'Beta', -500, 0, 1200, NULL);

INSERT INTO planets (id, system_id, name, orbit_index, planet_type) VALUES
(10, 1, 'Alpha I', 1, 'Gas'),
(11, 1, 'Alpha II', 2, 'Rock'),
(12, 2, 'Beta I', 1, 'Rock');

INSERT INTO moons (id, planet_id, name, orbit_index) VALUES
(100, 10, 'Alpha I-a', 1),
(101, 10, 'Alpha I-b', 2),
(102, 11, 'Alpha II-a', 1);
