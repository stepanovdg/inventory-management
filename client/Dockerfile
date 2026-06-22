# Factory Inventory Management System — Frontend (Vue 3 + Vite)
# Multi-stage: `build` compiles static assets, `prod` serves them with nginx,
# and `dev` runs the Vite dev server with hot reload (source bind-mounted by compose).

# ---- Build stage: compile the SPA ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- Development image: Vite dev server ----
FROM node:22-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 3000
# --host exposes the dev server outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---- Production image: nginx serving the static build ----
FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
