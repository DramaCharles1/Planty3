# Planty3 Frontend and API Quick Start Guide

## What We Built

We've successfully implemented a complete REST API and React frontend for the Planty3 plant monitoring system!

### Features

✅ **Django REST API**
- RESTful endpoints for plants, telemetry, and command history
- OpenAPI/Swagger documentation
- CORS support for frontend

✅ **React Frontend**
- Dashboard showing all plants with status cards
- Plant detail page with telemetry chart and command history
- Responsive design with green theme
- Time range selector for telemetry (1h, 6h, 24h, 7d)

✅ **Docker Integration**
- Frontend runs as a containerized service
- All services orchestrated with docker-compose

## Access Points

Once all services are running:

- **Frontend Dashboard**: http://localhost:5173
- **API Root**: http://localhost:8000/api/
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **Django Admin**: http://localhost:8000/admin/
- **Adminer (DB UI)**: http://localhost:8080

## Quick Start

### 1. Start All Services

```bash
# From the project root
docker compose up -d
```

This will start:
- PostgreSQL database
- MQTT broker (Mosquitto)
- Django backend (with API)
- Django MQTT client (ingests telemetry)
- Plant simulator (generates test data)
- React frontend (dashboard)
- Adminer (database UI)

### 2. Verify Services

Check that all services are running:

```bash
docker compose ps
```

All services should show "Up" status.

### 3. Access the Frontend

Open your browser and navigate to:

**http://localhost:5173**

You should see the Planty3 Dashboard with the simulated plant "sim_plant_01".

### 4. Explore the API

Try the Swagger UI for interactive API documentation:

**http://localhost:8000/api/docs/**

## API Endpoints

### Plants

```bash
# List all plants
GET http://localhost:8000/api/plants/

# Get plant detail
GET http://localhost:8000/api/plants/sim_plant_01/
```

### Telemetry

```bash
# Get last 24 hours of telemetry (default)
GET http://localhost:8000/api/plants/sim_plant_01/telemetry/

# Get last hour of telemetry
GET http://localhost:8000/api/plants/sim_plant_01/telemetry/?hours=1

# Get last 7 days of telemetry
GET http://localhost:8000/api/plants/sim_plant_01/telemetry/?hours=168

# Filter by telemetry type
GET http://localhost:8000/api/plants/sim_plant_01/telemetry/?telemetry_type=moisture
```

### Commands

```bash
# Get command history for a plant
GET http://localhost:8000/api/plants/sim_plant_01/commands/
```

## Frontend Usage

### Dashboard

The main dashboard (http://localhost:5173) shows:

- All plants in a grid layout
- Online/offline status (green = online, red = offline)
- Current moisture reading
- Last seen timestamp
- Click any plant card to view details

### Plant Detail Page

Click a plant card to see:

1. **Plant Info**
   - Plant ID
   - Location
   - Last seen time
   - Current moisture reading

2. **Telemetry Chart**
   - Line chart showing moisture over time
   - Time range selector (1h, 6h, 24h, 7d)
   - Responsive and interactive

3. **Command History**
   - Table showing all commands sent to the plant
   - Status badges (acknowledged, pending, failed)
   - Timestamps and error messages

## Testing with cURL

### Get Plants

```bash
curl http://localhost:8000/api/plants/
```

### Get Telemetry

```bash
curl http://localhost:8000/api/plants/sim_plant_01/telemetry/?hours=1
```

### Get Commands

```bash
curl http://localhost:8000/api/plants/sim_plant_01/commands/
```

## Development

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f mqtt_client
docker compose logs -f simulator
```

### Rebuilding Services

If you make code changes:

```bash
# Rebuild and restart a specific service
docker compose up -d --build backend
docker compose up -d --build frontend

# Rebuild all services
docker compose up -d --build
```

### Restarting Services

```bash
# Restart a specific service
docker compose restart backend
docker compose restart frontend

# Restart all services
docker compose restart
```

### Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes all data)
docker compose down -v
```

## Troubleshooting

### Frontend not loading?

1. Check frontend logs: `docker compose logs frontend`
2. Verify frontend is running: `docker compose ps frontend`
3. Check if port 5173 is available: `curl http://localhost:5173/`

### API not responding?

1. Check backend logs: `docker compose logs backend`
2. Verify backend is healthy: `docker compose ps backend`
3. Test API directly: `curl http://localhost:8000/api/plants/`

### No telemetry data?

1. Check simulator logs: `docker compose logs simulator`
2. Check mqtt_client logs: `docker compose logs mqtt_client`
3. Verify MQTT broker is running: `docker compose ps mqtt`
4. Check if plant exists: `curl http://localhost:8000/api/plants/`

### CORS errors in browser?

1. Check backend settings in `backend/planty/settings.py`
2. Verify `CORS_ALLOWED_ORIGINS` includes `http://localhost:5173`
3. Restart backend: `docker compose restart backend`

## Next Steps

Now that the frontend and API are working, you can:

1. **Add more plants**: Use Django Admin (http://localhost:8000/admin/)
2. **Send commands**: Implement command sending in the frontend
3. **Add authentication**: Secure the API with JWT or session-based auth
4. **Add WebSocket support**: Enable real-time telemetry updates
5. **Implement tests**: Write unit and integration tests for frontend
6. **Add Event timeline**: Implement Event model and timeline view (Phase 4)

## Documentation

For more details, see:

- `docs/frontend-and-api-implementation-summary.md` - Complete implementation summary
- `docs/frontend-and-api-plan.md` - Original implementation plan
- `frontend/README.md` - Frontend-specific documentation
- `AGENTS.md` - Project conventions and guidelines

## Support

If you encounter issues:

1. Check the logs: `docker compose logs -f`
2. Verify all services are running: `docker compose ps`
3. Restart services: `docker compose restart`
4. Rebuild if needed: `docker compose up -d --build`

Enjoy your new Planty3 dashboard! 🌱
