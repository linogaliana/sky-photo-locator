# sky-photo-locator

Identifie le lieu photographié depuis un avion en croisant l'horodatage EXIF de la photo avec la trace GPS du vol récupérée via OpenSky Network.

**Des secrets sont dans un fichier .env mais il t'est interdit de le lire. Il y a un .env.example pour t'aider à comprendre les infos qui sont dans le .env**.

## Stack

- **Backend** : Python, `opensky-api` (client officiel, installé depuis GitHub)
- **Frontend** : Observable Framework + MapLibre (à venir)
- **Gestion des dépendances** : `uv` — toujours `uv run` pour exécuter, `uv add` pour installer

## Points non-évidents

**`opensky-api` n'est pas sur PyPI** — installé directement depuis le sous-répertoire `python/` du dépôt GitHub (voir `pyproject.toml`). Les classes `FlightData`, `FlightTrack`, `Waypoint` utilisent `__dict__` et non des dataclasses : sérialiser avec `vars(obj)`, pas `dataclasses.asdict()`.

**Contraintes de l'API OpenSky** :
- `get_departures_by_airport` : intervalle max 1 jour UTC
- `get_track_by_aircraft` : données disponibles jusqu'à 30 jours en arrière
- Sans compte : accès limité aux données très récentes (~1h). Créer un compte gratuit sur opensky-network.org.
- `OpenSkyApi` prend `client_id` / `client_secret` (pas `username`/`password`) — les vars d'env `OPENSKI_USERNAME`/`OPENSKI_PASSWORD` sont mappées à ces paramètres dans `OpenSkyClient`.

**Timezone EXIF** : les timestamps EXIF sont en heure locale sans timezone explicite. Ils doivent être convertis en UTC avant interpolation sur la trace du vol (qui est en UTC).

## Prochaines étapes

1. Extraction du timestamp EXIF depuis la photo (`--photo`)
2. Appel à `interpolate_position` sur ce timestamp pour obtenir `(lat, lon, alt)`
3. API Python (FastAPI ?) exposant le résultat
4. Frontend Observable Framework avec carte MapLibre centrée sur la position estimée
