# Factory Inventory Management System

A full-stack demo application for a Claude Code workshop — inventory management, order tracking, demand forecasting, and analytics for factory operations.

![Dashboard](docs/dashboard-screenshot.png)

## Tech Stack

- **Frontend**: Vue 3 + Vite (port 3000)
- **Backend**: Python FastAPI (port 8001)
- **Data**: In-memory mock data (no database)

## Features

- Dashboard with interactive filtering and key metrics
- Inventory tracking across multiple warehouses
- Order management with status tracking
- Demand forecasting with trend analysis
- Backlog monitoring
- Spending analytics

## Quick Start

**One-command startup:**
```bash
./scripts/start.sh
# Starts both backend and frontend
# Backend: http://localhost:8001
# Frontend: http://localhost:3000
# API Docs: http://localhost:8001/docs
```

**Manual startup:**

Backend:
```bash
cd server
uv venv && uv sync
uv run python main.py
```

Frontend:
```bash
cd client
npm install
npm run dev
```

## Docker

The app is containerized with multi-stage builds and a single `docker-compose.yml`
that exposes two profiles. Both serve the frontend on `http://localhost:3000` and
the API on `http://localhost:8001` (the browser calls the API directly).

**Production** (nginx serves the built SPA, uvicorn serves the API):
```bash
docker compose --profile prod up --build
# Frontend: http://localhost:3000
# API:      http://localhost:8001  (docs at /docs)
docker compose --profile prod down
```

**Development** (hot reload, source bind-mounted):
```bash
docker compose --profile dev up --build
# Edits under client/ and server/ reload automatically
```

Files:
- `server/Dockerfile` — `prod` (uvicorn) and `dev` (uvicorn `--reload`) targets
- `client/Dockerfile` — `build` → `prod` (nginx) and a `dev` (Vite) target
- `client/nginx.conf` — serves the SPA with history-mode fallback
- `docker-compose.yml` — `prod` and `dev` profiles

## API Endpoints

All endpoints support optional filtering via query params: `warehouse`, `category`, `status`, `month`

- `GET /api/inventory` - Inventory items
- `GET /api/orders` - Orders
- `GET /api/demand` - Demand forecasts
- `GET /api/backlog` - Backlog items
- `GET /api/dashboard/summary` - Summary statistics
- `GET /api/spending/*` - Spending data

## Demo Data

Mock data includes:
- Inventory items (Circuit Boards, Sensors, Actuators, Controllers, Power Supplies)
- Orders spanning 12 months (Delivered, Shipped, Processing, Backordered)
- Demand forecasts with trends
- Backlog items
- Spending transactions

Data files: `server/data/*.json`

## Production Build

```bash
cd client
npm run build  # Output: client/dist/
```

## Platform Notes

**macOS/Linux:** The one-command startup script (`./scripts/start.sh`) and stop script (`./scripts/stop.sh`) work out of the box.

**Windows:** The shell scripts in `scripts/` are macOS/Linux only. Use the manual startup commands instead — run each in a separate terminal:

Backend:
```bash
cd server
uv venv && uv sync
uv run python main.py
```

Frontend:
```bash
cd client
npm install
npm run dev
```

To stop the servers, press Ctrl+C in each terminal window.

---

**Note:** Demo application with in-memory data. Not production-ready without database, authentication, and security implementation.
