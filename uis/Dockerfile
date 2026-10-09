FROM node:22.14.0-bookworm-slim

WORKDIR /app
COPY website/package.json website/package-lock.json ./website/
COPY backoffice/package.json backoffice/package-lock.json ./backoffice/
RUN npm ci --prefix website && npm ci --prefix backoffice
COPY . ./

EXPOSE 3000 3001
CMD ["node", "dev.mjs"]