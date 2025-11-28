# Docker Deployment Guide

Ce guide explique comment déployer le bot Discord en utilisant Docker et Docker Compose.

## Prérequis

- Docker installé sur votre système
- Docker Compose installé sur votre système
- Un fichier `.env` configuré avec vos variables d'environnement

## Configuration

1. Copiez le fichier `.env.example` vers `.env`:
   ```bash
   cp .env.example .env
   ```

2. Modifiez le fichier `.env` avec vos valeurs:
   ```env
   TOKEN=votre_token_discord
   PREFIX=!
   ALLOWED_USER_IDS=123456789,987654321
   JWT_SECRET=votre_secret_jwt
   CHATGPT_API_KEY=votre_api_key
   N8N_WEBHOOK=https://votre-webhook-n8n.com
   ```

## Démarrage du bot

### Avec Docker Compose (recommandé)

```bash
# Construire et démarrer le bot
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter le bot
docker-compose down

# Redémarrer le bot
docker-compose restart
```

### Avec Docker uniquement

```bash
# Construire l'image
docker build -t discord-bot .

# Démarrer le conteneur
docker run -d \
  --name discord-bot \
  --env-file .env \
  -v $(pwd)/database:/app/database \
  -v $(pwd)/discord.log:/app/discord.log \
  --restart unless-stopped \
  discord-bot

# Voir les logs
docker logs -f discord-bot

# Arrêter le conteneur
docker stop discord-bot

# Supprimer le conteneur
docker rm discord-bot
```

## Gestion des données

Les données persistantes sont stockées dans:
- `./database/` - Base de données du bot
- `./discord.log` - Fichier de logs

Ces dossiers sont montés en tant que volumes, donc les données persisteront même si le conteneur est supprimé.

## Mise à jour du bot

1. Arrêtez le conteneur:
   ```bash
   docker-compose down
   ```

2. Récupérez les dernières modifications:
   ```bash
   git pull
   ```

3. Reconstruisez et redémarrez:
   ```bash
   docker-compose up -d --build
   ```

## Dépannage

### Le bot ne démarre pas
```bash
# Vérifiez les logs
docker-compose logs

# Vérifiez que le fichier .env existe et contient le TOKEN
cat .env | grep TOKEN
```

### Reconstruire l'image complètement
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Accéder au shell du conteneur
```bash
docker-compose exec discord-bot /bin/bash
```

## Variables d'environnement

| Variable | Description | Obligatoire |
|----------|-------------|-------------|
| `TOKEN` | Token du bot Discord | Oui |
| `PREFIX` | Préfixe des commandes | Non (défaut: !) |
| `ALLOWED_USER_IDS` | IDs des utilisateurs autorisés (séparés par des virgules) | Non |
| `JWT_SECRET` | Secret pour la génération de JWT | Oui (si webhook utilisé) |
| `CHATGPT_API_KEY` | Clé API ChatGPT | Non |
| `N8N_WEBHOOK` | URL du webhook N8N | Oui (si webhook utilisé) |

## Architecture Docker

- **Image de base**: `python:3.12-slim`
- **Dépendances système**: `ffmpeg` (pour le traitement audio)
- **Réseau**: Bridge network isolé
- **Volumes**:
  - `./database` -> `/app/database`
  - `./discord.log` -> `/app/discord.log`
- **Restart policy**: `unless-stopped`
