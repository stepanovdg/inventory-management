# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Factory Inventory Management System — a full-stack demo (Claude Code workshop). Vue 3 frontend, Python FastAPI backend, in-memory mock data loaded from JSON (no database). Domain: inventory, orders, demand forecasting, backlog, spending/finance analytics, and reports for factory operations.

## Critical Tool Usage Rules

### Subagents (Task tool)
- **vue-expert** — Vue 3 frontend work (components, styling, reactivity, client state). Scoped to `client/` only; must not touch `server/` or data JSON.
  - **MANDATORY: ANY time you create or significantly modify a `.vue` file, delegate to vue-expert.**
- **code-reviewer** — review after writing significant code.
- **security-auditor** — fast security review of changed files (secrets, `v-html`/XSS, API input validation).
- **Explore** — understand codebase structure / search for patterns.
- **general-purpose** — complex multi-step tasks that don't fit the above.

### Skills
- **backend-api-test** — use when writing/modifying tests in `tests/backend/` (pytest + FastAPI TestClient).

### MCP Tools
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for GitHub operations. Exception: creating *local* branches — use `git checkout -b`. (Requires `GITHUB_PERSONAL_ACCESS_TOKEN` in the environment; `.env.example` is empty and does not document it.)
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing, against `http://localhost:3000` (frontend) and `http://localhost:8001` (API).

## Stack
- **Frontend**: Vue 3 (Composition API) + Vue Router 4 + Vite, port **3000**. Axios for HTTP. No Vuex/Pinia, no vue-i18n library (i18n is hand-rolled).
- **Backend**: Python FastAPI + uvicorn + Pydantic v2, port **8001**, requires Python ≥3.11. Managed with `uv`.
- **Data**: JSON files in `server/data/`, loaded into memory at import time by `server/mock_data.py`. Read-only; no persistence (restart reloads from disk).

## Commands

```bash
# One-command start (installs deps if missing, runs both, Ctrl+C to stop; logs in /tmp/inventory-*.log)
./scripts/start.sh
./scripts/stop.sh            # or stop via the stop script / Ctrl+C

# Backend (from server/) — `uv run` auto-creates/syncs the venv from pyproject.toml
cd server && uv run python main.py     # serves on http://0.0.0.0:8001, docs at /docs

# Frontend (from client/)
cd client && npm install && npm run dev # http://localhost:3000
cd client && npm run build              # output: client/dist/

# Tests — MUST run from tests/ (pytest.ini sets testpaths = backend)
cd tests && uv run pytest -v
cd tests && uv run pytest backend/test_inventory.py -v                                   # one file
cd tests && uv run pytest backend/test_inventory.py::TestInventoryEndpoints::test_get_all_inventory -v  # one test
cd tests && uv run pytest --cov=../server --cov-report=html                              # coverage
```

- There are **40 backend tests in 3 files** (`test_dashboard.py`, `test_inventory.py`, `test_misc_endpoints.py`). The `/api/orders` endpoints have **no dedicated test suite** — adding `test_orders.py` is the obvious coverage gap.
- `conftest.py` injects `server/` onto `sys.path` and imports `app` from `main` — no install needed, but cwd must be `tests/`.
- There are **no frontend tests, lint, or type-check** scripts (`client/package.json` has only `dev`/`build`/`preview`).
- **Do NOT run `server/generate_data.py`** — it is stale and divergent (generates `A/B/C` warehouses and `Widgets/Components/...` categories that do not match the live data). Running it corrupts data consistency.

## Architecture

**Data flow**: Vue view/composable → `client/src/api.js` (axios, base `http://localhost:8001/api`) → FastAPI endpoint → in-memory list filtering in Python → Pydantic validation → JSON → Vue `ref` → `computed` derived data. No Vite proxy; `api.js` hardcodes the absolute backend URL. No `@` path alias exists — all imports are relative (ignore `@/...` examples in `client/CLAUDE.md`).

**Backend** (`server/main.py`): all logic in one file. Shared helpers `apply_filters()` and `filter_by_month()`. Data globals come from `mock_data.py`. Pydantic models: `InventoryItem`, `Order`, `DemandForecast`, `BacklogItem` (the dashboard/spending/reports endpoints return raw dicts with no `response_model`). `PurchaseOrder` / `CreatePurchaseOrderRequest` models exist but are **dead code** (no route uses them; `purchase_orders.json` is empty).

**Frontend** (`client/src/`):
- **Routing** — defined in `main.js` (`createWebHistory`, eager imports, no guards/names): `/`→Dashboard, `/inventory`→Inventory, `/orders`→Orders, `/spending`→Spending (nav label "Finance"), `/demand`→Demand, `/reports`→Reports. `views/Backlog.vue` exists but is **orphaned** (not routed/imported).
- **Composables** (`composables/`, all global module-level singletons):
  - `useFilters` — the 4 global filter refs, all default `'all'`: `selectedPeriod`, `selectedLocation`, `selectedCategory`, `selectedStatus`. `getCurrentFilters()` maps UI→API: `selectedLocation`→`warehouse`, `selectedPeriod`→`month`.
  - `useI18n` — hand-rolled i18n. `t('dot.path')` resolver over `locales/en.js` + `locales/ja.js`; locale persisted in `localStorage['app-locale']` (default `en`); `currentCurrency` = JPY for `ja`, else USD; plus JA domain translators for product/customer/warehouse names.
  - `useAuth` — **mock auth**: `isAuthenticated` is always `true`, `logout()` is a stub, `currentUser` is a language-aware computed with hardcoded profile + tasks.
- **`utils/currency.js`** — `formatCurrency` / `formatCurrencyWithDecimals` / `convertAmount`. Data is stored in USD; JPY computed on the fly with hardcoded `USD_TO_JPY = 150`. Pairs with `useI18n().currentCurrency`.
- **Layout/components** — `App.vue` wires header (logo, nav, `LanguageSwitcher`, `ProfileMenu`) → `FilterBar` (the global 4-filter bar) → `<router-view>` → app-level `ProfileDetailsModal` + `TasksModal`. Detail modals: `BacklogDetailModal`, `ProductDetailModal` (Dashboard), `InventoryDetailModal` (Inventory), `CostDetailModal` (Spending).

## API Endpoints (implemented in `server/main.py`)

All GET, unauthenticated. Filters are optional query params; `'all'` or missing = no filter. `category`/`status` match case-insensitively; `warehouse` exact; `month` accepts `YYYY-MM` or `Q1-2025`..`Q4-2025`.

- `GET /` — API info
- `GET /api/inventory` — filters: `warehouse`, `category` (no month — inventory has no time dimension)
- `GET /api/inventory/{item_id}` — single item (404 if absent)
- `GET /api/orders` — filters: `warehouse`, `category`, `status`, `month`
- `GET /api/orders/{order_id}` — single order (404 if absent)
- `GET /api/dashboard/summary` — filters: `warehouse`, `category`, `status`, `month`
- `GET /api/demand`, `GET /api/backlog` — no filters (`backlog` injects a runtime `has_purchase_order` flag)
- `GET /api/spending/summary` · `/monthly` · `/categories` · `/transactions` — no filters
- `GET /api/reports/quarterly`, `GET /api/reports/monthly-trends` — no filters

**Frontend-expected but NOT yet implemented** (active `new_features` work — `api.js` calls these and the UI references a `PurchaseOrderModal`, but the backend has no routes, so they 404 at runtime): `GET/POST /api/tasks`, `DELETE/PATCH /api/tasks/{id}`, `POST /api/purchase-orders`, `GET /api/purchase-orders/{backlogItemId}`. Implement these on the backend to clear the "Failed to load tasks" / "Failed to resolve component: PurchaseOrderModal" console errors.

## Domain Values (verified against `server/data/`)
- **Categories (5)**: Circuit Boards, Sensors, Actuators, Controllers, **Power Supplies**.
- **Warehouses (3)**: San Francisco, London, Tokyo (city names — *not* A/B/C; only the legacy `transactions.json` still uses A/B/C, and `spending` uses a separate Raw Materials/Components/Equipment/Consumables taxonomy).
- **Order statuses**: Delivered, Shipped, Processing, Backordered (`pending_orders` = Processing + Backordered).
- Order dates are ISO strings (`2025-01-08T10:19:00`); data spans 12 months of 2025.

## Common Gotchas
1. Use unique `:key` in `v-for` (`sku`, `id`, `month`), never array `index`.
2. Validate dates before `.getMonth()` (`!isNaN(date.getTime())`).
3. When changing a JSON data file's shape, update the matching Pydantic model in `main.py`.
4. Keep the filter param-name mapping straight: UI `selectedLocation`→API `warehouse`, `selectedPeriod`→API `month`.
5. Revenue goals: $800K/month single, $9.6M YTD across all months.
6. CORS is wide-open (`allow_origins=["*"]`) — dev only.

## File Locations
- Views: `client/src/views/*.vue` · Components: `client/src/components/*.vue` · Composables: `client/src/composables/*.js`
- Locales: `client/src/locales/{en,ja}.js` · Currency util: `client/src/utils/currency.js`
- API client: `client/src/api.js` · App shell + global styles: `client/src/App.vue` · Routes: `client/src/main.js`
- Backend: `server/main.py`, `server/mock_data.py` · Data: `server/data/*.json`

## Design System
- Colors: slate/gray (`#0f172a`, `#64748b`, `#e2e8f0`); status green/blue/yellow/red.
- Charts: custom SVG; CSS Grid for layouts. **No emojis in UI.**
