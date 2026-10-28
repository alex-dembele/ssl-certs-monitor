# OpenCert

![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)  
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)  
![TypeScript](https://img.shields.io/badge/TypeScript-4.0%2B-blue)  
![Docker](https://img.shields.io/badge/Docker-Supported-blue)  

## Description

OpenCert (formerly SSL Certificates Monitor) is the certificate monitoring product of the [OpenDefender](https://github.com/opendefender) suite. It is a comprehensive solution designed to monitor the status, expiration, and validity of SSL/TLS certificates for multiple domains. This tool helps ensure your websites remain secure by providing real-time insights into certificate health, preventing unexpected downtimes due to expired or invalid certificates.

The application consists of a backend service for certificate checking and a frontend user interface for visualization and management. It supports monitoring multiple domains, historical tracking, and basic alerting mechanisms.

## Features

- **Certificate Monitoring**: Automatically check SSL/TLS certificates for expiration dates, validity, and status.
- **Multi-Domain Support**: Monitor certificates for multiple domains simultaneously.
- **Historical Data**: View past certificate details and changes over time.
- **User-Friendly Interface**: A modern web dashboard to add domains, view statuses, and configure settings.
- **Alerts and Notifications**: Basic notifications for upcoming expirations or issues (configurable via email or in-app).
- **Containerized Deployment**: Easy setup using Docker Compose for development and production environments.
- **Secure and Efficient**: Uses industry-standard libraries for certificate validation without compromising performance.

## Tech Stack

- **Backend**: Python (with libraries like `cryptography`, `requests`, and possibly FastAPI or Flask for API endpoints).
- **Frontend**: TypeScript with React (including dependencies like React Router, Axios for API calls).
- **Deployment**: Docker and Docker Compose for containerization.
- **Other**: Git for version control, with support for additional tools like Celery for scheduled tasks if implemented.

## Prerequisites

- Docker and Docker Compose installed (for containerized setup).
- Python 3.12+ (if running without Docker).
- Node.js 22+ and npm (for frontend development).
- Git for cloning the repository.

## Installation

### Using Docker (Recommended)

1. Clone the repository:
   ```
   git clone https://github.com/opendefender/OpenCert.git
   cd OpenCert
   ```

2. Create a `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

3. Build and start the containers:
   ```
   docker-compose up -d --build
   ```

4. The application should now be running:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

### Manual Installation (Without Docker)

#### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the backend server:
   ```
   uvicorn main:app --reload
   ```

#### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Create a `.env.local` file:
   ```
   BACKEND_API_URL=http://localhost:8000
   ```

4. Start the development server:
   ```
   npm run dev
   ```

## Deployment

### Free Deployment Options

This project can be deployed for **free** on several platforms:

#### 🚀 **Render.com** (Recommended)
- **Plan**: Free tier (750 hours/month per service)
- **Deploy in 1 click**: [Deploy to Render](https://render.com/deploy?repo=https://github.com/opendefender/OpenCert)
- Frontend: `ssl-cert-monitor-frontend.onrender.com`
- Backend: `ssl-cert-monitor-api.onrender.com`

#### 🚂 **Railway.app**
- **Plan**: Free $5/month credit
- Very intuitive interface
- Perfect for microservices

#### 🚀 **Fly.io**
- **Plan**: Always free (3 instances limit)
- Global performance
- Deploy with: `flyctl deploy`

#### **Vercel** (Frontend only)
- Perfect for Next.js
- Deploy to Vercel with one click
- Set `BACKEND_API_URL` environment variable on the frontend service

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed step-by-step instructions for each platform.

## Usage

1. **Access the Dashboard**: Open your browser and go to the frontend URL (e.g., http://localhost:3000).
2. **Add Domains**: Use the interface to add domains you want to monitor (e.g., example.com).
3. **View Status**: The dashboard displays current certificate status, expiration dates, and validity.
4. **Configure Alerts**: Email alerts can be configured via environment variables.
5. **Automatic Checks**: The scheduler (`backend/scheduler.py`) checks every domain at the interval set in *Settings → Organization* (see below).

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Service | Rôle |
|---|---|---|
| `BACKEND_API_TOKEN` | API, frontend | Jeton qui protège `/api/*`. **Obligatoire en production**, identique des deux côtés. |
| `APP_ENV` | API | `production` refuse de démarrer sans `BACKEND_API_TOKEN`. |
| `CORS_ORIGINS` | API | Origines autorisées à appeler l'API directement, séparées par des virgules. |
| `DATABASE_URL` | API, scheduler | Connexion PostgreSQL (`postgresql+psycopg://…`). SQLite local par défaut. |
| `BACKEND_API_URL` | frontend | URL de l'API vue par le serveur Next.js, **lue à l'exécution** : la changer ne demande pas de rebuild. |
| `CHECK_INTERVAL_MINUTES` | scheduler | Intervalle utilisé tant qu'aucun n'est enregistré dans *Paramètres → Organisation* (60 par défaut). |
| `SSL_CHECK_MAX_CONCURRENCY`, `SSL_CHECK_*_TIMEOUT`, `SSL_CHECK_MAX_RETRIES` | API, scheduler | Limites des vérifications TLS. |
| `SMTP_SERVER`, `SMTP_PORT`, `SMTP_SENDER_EMAIL`, `SMTP_PASSWORD` | scheduler | Envoi des alertes email. |
| `ALERT_RECIPIENTS` | scheduler | Destinataires email utilisés si aucun n'est saisi dans *Paramètres → Organisation*. |
| `LEGACY_DOMAINS_FILE` | API | Import unique d'une ancienne liste JSON de domaines (optionnel). |

`.env.example` contient une configuration de départ.

### Planification des vérifications

`backend/scheduler.py` lance une vérification complète, puis attend l'intervalle enregistré dans *Paramètres → Organisation* (`check_interval_minutes`), à défaut `CHECK_INTERVAL_MINUTES`, à défaut 60 minutes. Il relit ce paramètre chaque minute : un intervalle raccourci s'applique sans redémarrage. Un échec de vérification n'arrête pas la boucle.

Les paramètres de la portée **Organisation** sont la configuration globale des alertes planifiées : l'interrupteur *Notifications activées* les coupe toutes, le seuil et le canal s'appliquent aux domaines sans politique dédiée, et les destinataires reçoivent les emails. La portée **Personnel** ne sert qu'aux notifications de test.

### Production

- Définir `APP_ENV=production` et un `BACKEND_API_TOKEN` long et aléatoire sur l'API **et** le frontend.
- Ne pas exposer l'API publiquement : le navigateur passe par le proxy `/api/*` du frontend, qui ajoute le jeton côté serveur.
- Utiliser PostgreSQL (`DATABASE_URL`) et déployer trois services : API (`uvicorn main:app`), scheduler (`python scheduler.py`) et frontend.

Le frontend transmet `BACKEND_API_TOKEN` côté serveur via son proxy `/api/*` ; le jeton n'est jamais exposé au navigateur.

Les canaux de notification disponibles sont `email`, `webhook`, `slack`, `teams` et `discord`. Les webhooks utilisent `ALERT_WEBHOOK_URL`/`ALERT_WEBHOOK_SECRET`; les intégrations dédiées utilisent respectivement `SLACK_WEBHOOK_URL`/`SLACK_WEBHOOK_SECRET`, `TEAMS_WEBHOOK_URL`/`TEAMS_WEBHOOK_SECRET` et `DISCORD_WEBHOOK_URL`/`DISCORD_WEBHOOK_SECRET`. Chaque livraison porte une clé d'idempotence et une signature HMAC avec timestamp.

Les domaines et les derniers statuts sont stockés dans PostgreSQL via `DATABASE_URL`. Au premier démarrage, `LEGACY_DOMAINS_FILE` permet d'importer les domaines de l'ancien fichier JSON ; cette migration est idempotente. Avec Docker Compose, PostgreSQL et le volume persistant sont configurés automatiquement.

### Vérifications locales

```bash
pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q   # depuis la racine du dépôt
python -m compileall -q backend

cd frontend
npm ci
npm run lint
npm run typecheck
npm run build
```

Ces mêmes contrôles sont exécutés automatiquement par [la CI](.github/workflows/ci.yml) sur chaque pull request et chaque push vers `main`.

### API Endpoints

- `GET /api/domains` - List all monitored domains
- `POST /api/domains/bulk` - Add multiple domains
- `DELETE /api/domains/{domain_name}` - Remove a domain
- `GET /api/domains/{domain_name}/alert-policy` - Read a domain alert policy
- `PUT /api/domains/{domain_name}/alert-policy` - Configure threshold, reminders and channel
- `GET /api/check/{domain_name}` - Check single domain certificate
- `GET /api/settings` - Read personal and organization settings
- `PUT /api/settings/{scope}` - Update `personal` or `organization` settings
- `POST /api/notifications/test` - Send a test notification
- `GET /health` - Health check endpoint

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch: `git checkout -b feature/your-feature`.
3. Make your changes and commit: `git commit -m 'Add some feature'`.
4. Push to the branch: `git push origin feature/your-feature`.
5. Open a pull request.

Please ensure your code follows the project's style guidelines and includes tests where applicable.

## License

OpenCert is open-core: the Community Edition is licensed under the GNU AGPL v3.0 (see [LICENSE](LICENSE)), and commercial licensing is available. See [LICENSING.md](LICENSING.md) for details.

## Contact

For questions or support, open an issue on GitHub or contact the maintainer.

Thank you for using OpenCert! 🔒
