# Fichier: frontend/Dockerfile

# Étape 1: Build de l'application
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Étape 2: Servir l'application optimisée
FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package*.json ./

EXPOSE 3000
ENV PORT=3000

CMD ["sh", "-c", "npm start"]