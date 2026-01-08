# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files from app directory
COPY app/package*.json ./
RUN npm install

# Copy app source code
COPY app/ .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY app/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
