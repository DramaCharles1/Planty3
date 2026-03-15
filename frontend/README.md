# Planty3 Frontend

React-based dashboard for monitoring plant telemetry and status via the Planty3 MQTT system.

## Features

- **Dashboard**: Overview of all plants with status cards showing online/offline state and current moisture
- **Plant Detail**: Detailed view for individual plants with:
  - Telemetry chart (moisture over time) with configurable time ranges (1h, 6h, 24h, 7d)
  - Command history table showing sent commands and their acknowledgment status
- **Real-time data**: Fetches data from Django REST API

## Tech Stack

- **React 18** with React Router for navigation
- **Vite** for fast development and builds
- **Chart.js** with react-chartjs-2 for telemetry visualization
- **Axios** for API requests
- **Vitest** + React Testing Library for tests (not yet implemented)

## Development

### Prerequisites

- Docker + Docker Compose
- Backend API running on http://localhost:8000

### Quick Start

Start the frontend service:

```bash
docker compose up -d frontend
```

The frontend will be available at: **http://localhost:5173**

### Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.js          # Axios API client
│   ├── components/
│   │   ├── PlantCard.jsx      # Plant status card
│   │   ├── TelemetryChart.jsx # Chart.js line chart for moisture
│   │   └── CommandHistory.jsx # Command log table
│   ├── pages/
│   │   ├── Dashboard.jsx      # Main dashboard
│   │   └── PlantDetail.jsx    # Single plant detail view
│   ├── styles/
│   │   └── App.css            # Global styles
│   ├── App.jsx                # Main app component with routing
│   └── main.jsx               # React entry point
├── Dockerfile                  # Frontend container
├── package.json                # Node dependencies
├── vite.config.js              # Vite + Vitest config
└── index.html                  # HTML entry point
```

### API Integration

The frontend connects to the Django REST API at `/api/` with the following endpoints:

- `GET /api/plants/` - List all plants
- `GET /api/plants/{plant_id}/` - Get plant details
- `GET /api/plants/{plant_id}/telemetry/?hours={hours}` - Get telemetry data
- `GET /api/plants/{plant_id}/commands/` - Get command history

The API base URL is configured via the `VITE_API_BASE_URL` environment variable (default: `http://localhost:8000/api`).

### Environment Variables

Create a `.env` file in the `frontend/` directory:

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

### Building for Production

```bash
docker compose exec frontend npm run build
```

Build artifacts will be in `frontend/dist/`.

### Running Tests

Tests are configured with Vitest but not yet implemented:

```bash
docker compose exec frontend npm test
```

## Future Enhancements

- [ ] Implement unit and integration tests
- [ ] Add command sending UI (currently read-only)
- [ ] Add WebSocket support for real-time updates
- [ ] Add Event timeline view (when Event model is implemented in Phase 4)
- [ ] Add authentication/authorization
- [ ] Add dark mode toggle
- [ ] Add plant management (CRUD) UI

## Notes

- The frontend currently displays moisture telemetry only. Additional metrics (temperature, light, etc.) can be added when the backend supports them.
- Command history shows sent commands and their acks, but there's no UI for sending new commands yet.
- Events are not yet implemented in the backend (deferred to Phase 4).
