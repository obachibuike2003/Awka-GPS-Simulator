# Awka Route Navigator<img width="1590" height="932" alt="Screenshot 2026-02-19 120832" src="https://github.com/user-attachments/assets/dc21573c-0c27-43d5-bcc5-be37b5aa00a4" />




A real-time GPS route simulator for Awka, Nigeria. This application downloads live road network data from OpenStreetMap (OSM), calculates optimal driving routes between locations using shortest-path algorithms, and animates a vehicle traversing the route at realistic speeds.

## Features

- **Dynamic Map Loading**: Fetches road networks around Awka via osmnx/OpenStreetMap
- **Route Computation**: Uses Dijkstra's algorithm (NetworkX) to find shortest paths between start/destination points
- **Real-Time Simulation**: Animates vehicle movement along calculated routes with accurate speed (50 km/h default)
- **Interactive UI**: Click-and-type destination input, live distance/ETA display, speed readout
- **Geolocation**: Integrates Nominatim for place-name geocoding (e.g., "unizik" → lat/lon coordinates)
- **Visual Feedback**: Yellow route overlay on gray OSM road network, car sprite with heading/bearing
- **Retry Mechanism**: Press **R** to retry map loading if download fails

## Screenshots

- Real-time navigation display with route visualization
- Speed and ETA tracking
- Interactive destination input box

## Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup

1. Clone or extract the project:
```bash
cd c:\Users\hp\TAT
```

2. Install dependencies:
```bash
pip install pygame osmnx networkx geopy
```

3. Run the application:
```bash
python app.py
```

## Usage

### Controls

| Key/Action | Function |
|-----------|----------|
| **Click** destination box | Activate text input |
| **T** | Toggle destination input (if not focused) |
| **Type** destination name | Enter place name (e.g., "unizik", "Awka High School") |
| **Enter** | Compute route and start navigation |
| **Esc** | Cancel input |
| **R** | Retry map download (if failed) |

### Workflow

1. **Launch** the app — map begins downloading from OpenStreetMap
2. **Wait** for "Map loaded" status
3. **Click** or press **T** to focus the destination input box
4. **Type** a location name within Awka (e.g., "Nnamdi Azikiwe University", "Awka North LGA")
5. **Press Enter** — route is computed and vehicle begins navigation
6. **Watch** the car follow the yellow route with real-time distance & ETA updates

### Status Messages

- `"Map loaded."` — Ready to navigate
- `"Map load failed: ..."` — OSM/network error; press **R** to retry
- `"Navigating to [place] — X.XX km"` — Route active, distance shown
- `"Could not find '[place]'..."` — Destination not found; try a more specific name

## Tech Stack

- **Python 3.x** — Core language
- **Pygame** — Real-time graphics, UI rendering, event handling
- **osmnx** — OpenStreetMap data fetching & road network extraction
- **NetworkX** — Graph algorithms (shortest-path via Dijkstra)
- **Geopy/Nominatim** — Place-name geocoding (text → lat/lon)
- **Haversine** — Geodetic distance calculations between coordinates

## Project Structure

```
c:\Users\hp\TAT\
├── app.py              # Main application (pygame loop, routing logic)
├── README.md           # This file
├── .venv/              # Virtual environment (optional)
└── __pycache__/        # Python bytecode (auto-generated)
```

## How It Works

### Map Loading
1. Nominatim geocodes the base place ("Awka, Nigeria") → center lat/lon
2. osmnx downloads all drivable roads within ~12 km radius
3. Roads are stored as a NetworkX graph (nodes = intersections, edges = streets)

### Route Computation
1. User enters destination → Nominatim finds its coordinates
2. Nearest nodes in the road graph are found for start & destination
3. Dijkstra's algorithm calculates shortest path
4. Path is rendered as a yellow line on the map

### Vehicle Simulation
- Car position updates each frame based on speed (50 km/h)
- Heading/bearing calculated from consecutive route points
- Distance remaining & ETA updated in real-time

## Configuration

Edit these constants in `app.py` to customize:

```python
BASE_PLACE    = "Awka, Nigeria"     # Center location for map download
SCREEN_W      = 1280                # Window width (px)
SCREEN_H      = 720                 # Window height (px)
TARGET_FPS    = 60                  # Refresh rate
SIM_SPEED_KMH = 50.0                # Simulation speed
```

## Troubleshooting

### Map fails to load
- **Cause**: Nominatim/OSM timeout or no internet
- **Fix**: Press **R** to retry; check network connection

### Destination not found
- **Cause**: Place name too vague or not in Awka
- **Fix**: Use full name (e.g., "Nnamdi Azikiwe University, Awka" instead of "unizik")

### Route error: "NoneType object has no attribute 'nodes'"
- **Cause**: Map not fully loaded when route requested
- **Fix**: Wait for "Map loaded" status before entering destination

### Pygame window not responding
- **Cause**: VS Code/IDE capturing keyboard
- **Fix**: Click the game window title bar to refocus

## Future Enhancements

- [ ] Traffic simulation (dynamic congestion)
- [ ] Multiple vehicles/fleet tracking
- [ ] Waypoint routing (multi-stop navigation)
- [ ] Road speed limits (realistic edge weights)
- [ ] Offline map caching
- [ ] Mobile app version (kivy/Flutter)
- [ ] Web UI (Flask + Folium)

## License

Open-source. Free to modify & distribute.

## Author

Awka Route Navigator Contributors

## Contact & Support

For issues, feedback, or contributions, open an issue or submit a PR.

---

**Status**: Beta ✓ Map loading works • ✓ Routing works • ✓ UI responsive • ⚠ OSM data quality dependent on coverage
