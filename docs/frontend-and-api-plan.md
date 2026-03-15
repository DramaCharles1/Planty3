# Frontend and API Implementation Plan

## Overview

This document outlines the plan to build a REST API for the Planty3 backend and a frontend visualization dashboard for plant telemetry data.

## Goals

1. Create a REST API with Django REST Framework to expose plant data
2. Add OpenAPI/Swagger documentation for all API endpoints
3. Build a React-based frontend to visualize plant data
4. Integrate the frontend into the Docker Compose setup

---

## Phase 1: Backend REST API

### 1.1 Install Dependencies

Add to `backend/requirements.txt`:
```
drf-spectacular>=0.27.0
django-cors-headers>=4.3.0
```

### 1.2 Django Settings Configuration

In `backend/planty/settings.py`:

**Add to `INSTALLED_APPS`:**
```python
INSTALLED_APPS = [
    # ... existing apps
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
]
```

**Add to `MIDDLEWARE`** (corsheaders must be high in the list):
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Add this
    'django.middleware.common.CommonMiddleware',
    # ... rest of middleware
]
```

**Add REST Framework config:**
```python
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}
```

**Add CORS config (for development):**
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative frontend port
]
```

**Add drf-spectacular config:**
```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'Planty3 API',
    'DESCRIPTION': 'REST API for Planty3 plant monitoring system',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

### 1.3 Create Serializers

Create/update `backend/motherplant/serializers.py`:

```python
from rest_framework import serializers
from .models import Plant, PlantState, Telemetry, CommandLog, Event


class PlantStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantState
        fields = ['online', 'last_seen', 'last_moisture', 'updated_at']


class PlantListSerializer(serializers.ModelSerializer):
    """Serializer for plant list view with nested state"""
    state = PlantStateSerializer(read_only=True)
    
    class Meta:
        model = Plant
        fields = ['id', 'plant_id', 'name', 'location', 'created_at', 'state']


class PlantDetailSerializer(serializers.ModelSerializer):
    """Serializer for plant detail view"""
    state = PlantStateSerializer(read_only=True)
    
    class Meta:
        model = Plant
        fields = ['id', 'plant_id', 'name', 'location', 'created_at', 'state']


class TelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Telemetry
        fields = ['id', 'type', 'value', 'timestamp', 'received_at']


class CommandLogSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = CommandLog
        fields = ['id', 'command', 'cmd_id', 'sent_at', 'ack_at', 'ok', 'error', 'status', 'created_at']
    
    def get_status(self, obj):
        """Derive command status from fields"""
        if obj.ack_at is None:
            return 'pending'
        return 'ok' if obj.ok else 'error'


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'event_type', 'value', 'timestamp', 'received_at']
```

### 1.4 Create API Views

Create/update `backend/motherplant/views.py`:

```python
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Plant, Telemetry, CommandLog, Event
from .serializers import (
    PlantListSerializer,
    PlantDetailSerializer,
    TelemetrySerializer,
    CommandLogSerializer,
    EventSerializer,
)


class PlantViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Plant model.
    
    list: Get all plants with their current state
    retrieve: Get a single plant by ID
    telemetry: Get telemetry data for a plant (filterable by time range)
    commands: Get command history for a plant
    events: Get event history for a plant
    """
    queryset = Plant.objects.select_related('state').all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['plant_id', 'name', 'location']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PlantListSerializer
        return PlantDetailSerializer
    
    @action(detail=True, methods=['get'])
    def telemetry(self, request, pk=None):
        """Get telemetry data for a plant, optionally filtered by time range"""
        plant = self.get_object()
        queryset = Telemetry.objects.filter(plant=plant)
        
        # Filter by time range if provided
        from_time = request.query_params.get('from')
        to_time = request.query_params.get('to')
        telemetry_type = request.query_params.get('type')
        
        if from_time:
            queryset = queryset.filter(timestamp__gte=from_time)
        if to_time:
            queryset = queryset.filter(timestamp__lte=to_time)
        if telemetry_type:
            queryset = queryset.filter(type=telemetry_type)
        
        queryset = queryset.order_by('-timestamp')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TelemetrySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TelemetrySerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def commands(self, request, pk=None):
        """Get command history for a plant"""
        plant = self.get_object()
        queryset = CommandLog.objects.filter(plant=plant).order_by('-sent_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CommandLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CommandLogSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """Get event history for a plant"""
        plant = self.get_object()
        queryset = Event.objects.filter(plant=plant)
        
        # Filter by event type if provided
        event_type = request.query_params.get('type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        queryset = queryset.order_by('-timestamp')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = EventSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EventSerializer(queryset, many=True)
        return Response(serializer.data)
```

### 1.5 Create URL Routes

Create `backend/motherplant/urls.py`:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlantViewSet

router = DefaultRouter()
router.register(r'plants', PlantViewSet, basename='plant')

urlpatterns = [
    path('', include(router.urls)),
]
```

Update `backend/planty/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('motherplant.urls')),
    
    # OpenAPI schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # ReDoc UI
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

### 1.6 API Endpoints Summary

Once implemented, the following endpoints will be available:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/plants/` | List all plants with their current state |
| GET | `/api/plants/{id}/` | Get details of a specific plant |
| GET | `/api/plants/{id}/telemetry/` | Get telemetry data for a plant |
| GET | `/api/plants/{id}/commands/` | Get command history for a plant |
| GET | `/api/plants/{id}/events/` | Get event history for a plant |
| GET | `/api/schema/` | OpenAPI schema (JSON) |
| GET | `/api/docs/` | Swagger UI documentation |
| GET | `/api/redoc/` | ReDoc documentation |

**Query Parameters:**

- `/api/plants/{id}/telemetry/?from=2026-03-01T00:00:00Z&to=2026-03-14T23:59:59Z&type=moisture`
- `/api/plants/{id}/events/?type=watering_started`

---

## Phase 2: Frontend Application

### 2.1 Technology Stack

- **Framework:** React 18
- **Build Tool:** Vite
- **Routing:** React Router v6
- **HTTP Client:** Axios
- **Charting:** Chart.js + react-chartjs-2 (or Recharts)
- **UI Components:** (Optional) Shadcn/ui, MUI, or plain CSS

### 2.2 Project Structure

```
frontend/
├── Dockerfile
├── package.json
├── vite.config.js
├── index.html
├── .env
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── api/
    │   └── client.js          # Axios instance configured for backend
    ├── components/
    │   ├── PlantCard.jsx      # Dashboard card component
    │   ├── TelemetryChart.jsx # Time-series chart component
    │   ├── EventFeed.jsx      # Event list component
    │   └── CommandHistory.jsx # Command log table component
    ├── pages/
    │   ├── Dashboard.jsx      # Plant overview grid
    │   └── PlantDetail.jsx    # Single plant detail view
    └── styles/
        └── App.css
```

### 2.3 Page Designs

#### Dashboard Page (`/`)

**Layout:**
- Grid of plant cards (responsive: 1-3 columns)
- Each card shows:
  - Plant name and location
  - Online/offline status indicator (colored dot)
  - Last seen timestamp (relative time: "2m ago", "3h ago")
  - Last moisture reading with color coding:
    - Red: < 30%
    - Yellow: 30-50%
    - Green: > 50%
  - "View Details" button → links to `/plants/{id}`

**API Calls:**
- `GET /api/plants/` (fetches all plants with nested state)

#### Plant Detail Page (`/plants/:id`)

**Layout:**
- Header: Plant name, location, online status
- Three sections (tabs or stacked):

**1. Telemetry Chart (primary)**
- Line chart of moisture over time
- Time range selector: 1h / 6h / 24h / 7d / custom date picker
- Y-axis: moisture percentage (0-100%)
- X-axis: time
- Data points from `Telemetry` model

**API Calls:**
- `GET /api/plants/{id}/telemetry/?from={start}&to={end}&type=moisture`

**2. Event Feed**
- Table/list of events
- Columns: timestamp, event_type, value (optional)
- Filter dropdown by event_type
- Paginated (show 20 per page)

**API Calls:**
- `GET /api/plants/{id}/events/?type={filter}`

**3. Command History**
- Table of sent commands
- Columns: command, cmd_id (short), sent_at, status badge, error message
- Status badges:
  - ⏳ Pending (gray)
  - ✓ OK (green)
  - ✗ Error (red)
- Paginated

**API Calls:**
- `GET /api/plants/{id}/commands/`

### 2.4 Dockerfile for Frontend

Create `frontend/Dockerfile`:

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start dev server (for production, use `npm run build` and serve with nginx)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

### 2.5 Docker Compose Integration

Add to `docker-compose.yaml`:

```yaml
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend
```

### 2.6 Environment Configuration

Create `frontend/.env`:

```
VITE_API_URL=http://localhost:8000
```

In `frontend/src/api/client.js`:

```javascript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL + '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;
```

---

## Phase 3: Testing & Quality Assurance

### 3.1 Backend Tests

Add tests for API endpoints in `backend/motherplant/tests.py`:

- Test plant list endpoint returns all plants
- Test plant detail endpoint returns correct plant with state
- Test telemetry endpoint with time range filters
- Test command history endpoint
- Test event history endpoint with type filter
- Test pagination works correctly
- Test CORS headers are present

Run with: `make test`

### 3.2 Frontend Tests

Frontend testing uses a two-tier approach: **unit tests** for presentational components and **integration tests** for data-fetching pages.

#### Testing Tool Stack

- **Vitest** — Fast test runner with native Vite integration
- **React Testing Library (RTL)** — Render components, query DOM, simulate user interactions
- **MSW (Mock Service Worker)** — Intercept HTTP requests at the network level for realistic integration tests
- **Testing Library Jest-DOM** — Additional matchers for DOM assertions

#### Test Organization

```
frontend/src/
├── components/
│   ├── PlantCard.jsx
│   ├── PlantCard.test.jsx        # Co-located unit tests
│   ├── TelemetryChart.jsx
│   ├── TelemetryChart.test.jsx
│   ├── EventFeed.jsx
│   ├── EventFeed.test.jsx
│   ├── CommandHistory.jsx
│   └── CommandHistory.test.jsx
├── pages/
│   ├── Dashboard.jsx
│   ├── Dashboard.test.jsx        # Integration tests
│   ├── PlantDetail.jsx
│   └── PlantDetail.test.jsx      # Integration tests
└── test/
    ├── setup.js                  # RTL cleanup, MSW server lifecycle
    └── mocks/
        └── handlers.js           # MSW request handlers for all API endpoints
```

#### Unit Tests (Presentational Components)

**PlantCard Component**

Pure presentational component receiving plant data via props.

Tests:
- Renders plant name and location correctly
- Shows green dot when `state.online: true`, gray/red dot when `false`
- Displays moisture value with correct CSS class:
  - `moisture-critical` when < 30%
  - `moisture-warning` when 30-50%
  - `moisture-healthy` when > 50%
- Formats "last seen" as relative time ("2m ago", "3h ago")
- "View Details" link points to correct route `/plants/{id}`
- Handles missing state gracefully (plant with no `PlantState` record)

No API mocking needed — pass props directly in tests.

**Status Badge Component** (if extracted)

Tests:
- Renders "Pending" badge (gray) when `ack_at` is null
- Renders "OK" badge (green) when `ok === true`
- Renders "Error" badge (red) when `ok === false`, displays error message

**Time Formatter Utility** (if extracted)

Tests:
- Formats ISO timestamps as relative time
- Handles invalid/null timestamps

#### Integration Tests (Data-Fetching Pages)

**Dashboard Page**

Fetches plant list and renders PlantCard components.

Tests:
- Shows loading indicator while API call is in progress
- Renders one PlantCard per plant from API response
- Shows empty state message when API returns empty array
- Shows error message when API call fails (500/network error)
- Clicking "View Details" navigates to plant detail page

Uses **MSW** to mock `GET /api/plants/` with different scenarios:
- Success response with 2-3 plants
- Empty array response
- 500 error response

**PlantDetail Page**

Composition page that fetches plant detail and renders sub-components.

Tests:
- Fetches plant detail on mount (`GET /api/plants/{id}/`)
- Renders plant header (name, location, online status)
- Renders TelemetryChart, EventFeed, CommandHistory sections
- Handles 404 response (invalid plant ID) with error message
- Handles loading state while fetching

Uses **MSW** to mock:
- `GET /api/plants/{id}/` (success and 404)
- `GET /api/plants/{id}/telemetry/` (with sample data)
- `GET /api/plants/{id}/commands/`
- `GET /api/plants/{id}/events/`

**TelemetryChart Component**

Fetches time-series data and renders Chart.js chart.

Tests:
- Makes API call with correct `from`/`to` query params for selected time range
- Renders `<canvas>` element (Chart.js renders to canvas)
- Time range selector buttons trigger new API calls with updated params
- Shows "No data available" message when API returns empty array
- Shows error message when API call fails

*Note:* Chart.js rendering internals (pixel-level output) are not tested in JSDOM. Focus on:
- Correct API calls
- Correct data transformation
- Fallback states (loading, empty, error)

**EventFeed Component**

Fetches and displays event history.

Tests:
- Renders table rows matching API response
- Filter dropdown triggers new API call with `?type=` query param
- Pagination controls (next/previous) trigger new API calls with page param
- Empty state when no events
- Timestamps are formatted correctly (ISO → human-readable)

**CommandHistory Component**

Fetches and displays command log.

Tests:
- Renders correct status badge per row based on `ack_at`, `ok` fields
- Displays error message when `ok === false`
- Rows are ordered by `sent_at` descending
- Pagination controls work correctly

#### What NOT to Test

- Chart.js rendering internals (visual regression is a separate concern)
- Axios/fetch library behavior itself (assume it works)
- React Router's internal routing logic
- Third-party component libraries (MUI, Shadcn/ui)
- Browser APIs (localStorage, fetch) — mock at boundaries

#### Testing Pyramid

| Level | What | Count |
|-------|------|-------|
| **Unit** | Presentational components, utilities, badges | Many (10-20) |
| **Integration** | Pages that fetch + render with MSW mocked API | Moderate (5-10) |

Unit tests should be **fast** (no network, no timers), **stable** (no flaky async), and **focused** (one concern per test).

Integration tests verify the **data flow** from API client → component → DOM, ensuring query params, pagination, and filters work correctly.

#### Example MSW Handler

```javascript
// frontend/src/test/mocks/handlers.js
import { http, HttpResponse } from 'msw';

export const handlers = [
  // Plant list
  http.get('/api/plants/', () => {
    return HttpResponse.json([
      {
        id: 1,
        plant_id: 'plant01',
        name: 'Basil',
        location: 'Kitchen',
        created_at: '2026-03-01T10:00:00Z',
        state: {
          online: true,
          last_seen: '2026-03-15T12:00:00Z',
          last_moisture: 42.5,
          updated_at: '2026-03-15T12:00:00Z',
        },
      },
    ]);
  }),

  // Plant detail
  http.get('/api/plants/:id/', ({ params }) => {
    return HttpResponse.json({
      id: Number(params.id),
      plant_id: 'plant01',
      name: 'Basil',
      location: 'Kitchen',
      created_at: '2026-03-01T10:00:00Z',
      state: {
        online: true,
        last_seen: '2026-03-15T12:00:00Z',
        last_moisture: 42.5,
        updated_at: '2026-03-15T12:00:00Z',
      },
    });
  }),

  // Telemetry
  http.get('/api/plants/:id/telemetry/', () => {
    return HttpResponse.json([
      {
        id: 1,
        type: 'moisture',
        value: 42.5,
        timestamp: '2026-03-15T12:00:00Z',
        received_at: '2026-03-15T12:00:01Z',
      },
    ]);
  }),
];
```

#### Vitest Configuration

Add to `frontend/vite.config.js`:

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
});
```

Add `frontend/src/test/setup.js`:

```javascript
import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './mocks/server';

// Start MSW server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// Reset handlers and cleanup after each test
afterEach(() => {
  server.resetHandlers();
  cleanup();
});

// Stop MSW server after all tests
afterAll(() => server.close());
```

#### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- PlantCard.test.jsx
```

Add to `frontend/package.json`:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  }
}
```

---

## Phase 4: Deployment Considerations

### 4.1 Production Build

For frontend:
- Change `frontend/Dockerfile` to use multi-stage build
- Stage 1: `npm run build` → generates static files in `dist/`
- Stage 2: Serve with nginx
- Update `docker-compose.yaml` to use production config

### 4.2 Security

- Remove `CORS_ALLOWED_ORIGINS = ["*"]` in production
- Add authentication to API (DRF token auth or JWT)
- Use environment variables for all secrets
- Enable Django's security middleware settings

### 4.3 Database Migrations

Before deploying:
```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

---

## Implementation Checklist

### Backend
- [ ] Add `drf-spectacular` and `django-cors-headers` to requirements.txt
- [ ] Update Django settings (INSTALLED_APPS, MIDDLEWARE, REST_FRAMEWORK, CORS, SPECTACULAR)
- [ ] Create all serializers in `motherplant/serializers.py`
- [ ] Create PlantViewSet with custom actions in `motherplant/views.py`
- [ ] Create `motherplant/urls.py` with router
- [ ] Update `planty/urls.py` to include API routes and schema/docs URLs
- [ ] Install dependencies: `docker compose exec backend pip install -r requirements.txt`
- [ ] Test API endpoints manually
- [ ] Write tests for API endpoints
- [ ] Run `make quality` to verify all checks pass

### Frontend
- [ ] Create `frontend/` directory
- [ ] Initialize Vite + React project: `npm create vite@latest frontend -- --template react`
- [ ] Install dependencies: `axios`, `react-router-dom`, `chart.js`, `react-chartjs-2`, `date-fns`
- [ ] Install test dependencies: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `msw`
- [ ] Configure Vitest in `vite.config.js`
- [ ] Create test setup file and MSW handlers
- [ ] Create API client in `src/api/client.js`
- [ ] Build Dashboard page with PlantCard component
- [ ] Write unit tests for PlantCard component
- [ ] Write integration tests for Dashboard page
- [ ] Build PlantDetail page with TelemetryChart, EventFeed, CommandHistory
- [ ] Write integration tests for PlantDetail page
- [ ] Write unit tests for child components (TelemetryChart, EventFeed, CommandHistory)
- [ ] Verify all tests pass: `npm test`
- [ ] Create Dockerfile for frontend
- [ ] Add frontend service to `docker-compose.yaml`
- [ ] Test frontend locally
- [ ] Verify integration (frontend → API → backend → DB)

### Documentation
- [ ] Verify Swagger UI at `http://localhost:8000/api/docs/`
- [ ] Verify ReDoc UI at `http://localhost:8000/api/redoc/`
- [ ] Update main README.md with API and frontend usage instructions

---

## Timeline Estimate

| Phase | Estimated Time |
|-------|----------------|
| Backend API + Swagger | 3-4 hours |
| Backend API tests | 2-3 hours |
| Frontend scaffold + routing + test setup | 2-3 hours |
| Dashboard page + unit tests | 3-4 hours |
| Plant detail page (chart + tables) + integration tests | 5-6 hours |
| Docker integration | 1-2 hours |
| **Total** | **16-22 hours** |

---

## Additional Features (Future Enhancements)

- **Real-time updates:** WebSocket connection for live telemetry updates (Django Channels)
- **Command sending:** POST endpoint to send commands from the UI
- **Authentication:** User login and per-user plant access control
- **Alerts:** Configurable thresholds with email/push notifications
- **Mobile app:** React Native or PWA version of the dashboard
- **Historical data export:** CSV/JSON download of telemetry data
- **Multi-metric support:** Once additional telemetry types (temperature, light, humidity) are added to the MQTT worker

---

## References

- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [Vite Documentation](https://vitejs.dev/)
- [React Router Documentation](https://reactrouter.com/)
- [Chart.js Documentation](https://www.chartjs.org/)
