FROM node:20-alpine AS base
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --only=production

COPY frontend/ .

EXPOSE 3000

# Development (with hot reload)
FROM base AS development
RUN npm install
CMD ["npm", "run", "dev"]

# Production
FROM base AS production
RUN npm run build
CMD ["npm", "run", "start"]
