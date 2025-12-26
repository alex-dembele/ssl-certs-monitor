# SSL Certificates Monitor

![SSL Certificates Monitor](https://img.shields.io/badge/License-MIT-blue.svg)  
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)  
![TypeScript](https://img.shields.io/badge/TypeScript-4.0%2B-blue)  
![Docker](https://img.shields.io/badge/Docker-Supported-blue)  

## Description

SSL Certificates Monitor is a comprehensive solution designed to monitor the status, expiration, and validity of SSL/TLS certificates for multiple domains. This tool helps ensure your websites remain secure by providing real-time insights into certificate health, preventing unexpected downtimes due to expired or invalid certificates.

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
- Python 3.8+ (if running without Docker).
- Node.js 14+ and Yarn or npm (for frontend development).
- Git for cloning the repository.

## Installation

### Using Docker (Recommended)

1. Clone the repository:
   ```
   git clone https://github.com/alex-dembele/ssl-certs-monitor.git
   cd ssl-certs-monitor
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
   NEXT_PUBLIC_API_URL=http://localhost:8000
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
- **Deploy in 1 click**: [Deploy to Render](https://render.com/deploy?repo=https://github.com/alex-dembele/ssl-certs-monitor)
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
- Set `NEXT_PUBLIC_API_URL` environment variable

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed step-by-step instructions for each platform.

## Usage

1. **Access the Dashboard**: Open your browser and go to the frontend URL (e.g., http://localhost:3000).
2. **Add Domains**: Use the interface to add domains you want to monitor (e.g., example.com).
3. **View Status**: The dashboard displays current certificate status, expiration dates, and validity.
4. **Configure Alerts**: Email alerts can be configured via environment variables.
5. **Automatic Checks**: The backend cron job automatically checks certificates daily.

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Backend API Configuration
API_URL=http://localhost:8000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Email Alerts (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_SENDER_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_RECIPIENTS=recipient@example.com
```

### API Endpoints

- `GET /api/domains` - List all monitored domains
- `POST /api/domains/bulk` - Add multiple domains
- `DELETE /api/domains/{domain_name}` - Remove a domain
- `GET /api/check/{domain_name}` - Check single domain certificate
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

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, open an issue on GitHub or contact the maintainer.

Thank you for using SSL Certificates Monitor! 🔒
