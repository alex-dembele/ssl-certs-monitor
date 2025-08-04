# Fichier: Dockerfile

# Utiliser une image Python officielle et légère comme base
FROM python:3.10-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers nécessaires de notre projet local vers le conteneur
# On copie tout pour plus de simplicité à ce stade
COPY . .

# Définir la commande à exécuter lorsque le conteneur démarre
CMD ["python", "monitor.py"]