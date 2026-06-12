# Stage 1: Build the React application
FROM node:18-alpine AS builder
WORKDIR /app

# Install dependencies first (Docker layer caching)
COPY package*.json ./
RUN npm install

# Copy source code and build
COPY . .
RUN npm run build

# Stage 2: Serve using Nginx
FROM nginx:alpine

# Copy the built assets to /usr/share/nginx/html/dashboard
# so Nginx serves it under the "/dashboard/" subpath
COPY --from=builder /app/dist /usr/share/nginx/html/dashboard

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
