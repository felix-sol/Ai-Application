# Verwende exakt die Node-Version, die du lokal hast
FROM node:22.16.0

# Setze Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere package.json und package-lock.json
COPY package*.json ./

# Installiere Abhängigkeiten
RUN npm install

# Kopiere den Rest des Codes
COPY . .

# Öffne den richtigen Port (z. B. 3000 für React-Dev-Server)
EXPOSE 3000

# Starte die Entwicklungsumgebung
CMD ["npm", "start"]
