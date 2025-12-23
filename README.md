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

2. Build and start the containers:
   ```
   docker-compose up -d --build
   ```

3. The application should now be running:
   - Frontend: http://localhost:3000 (or configured port)
   - Backend: http://localhost:5000 (or configured port)

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
   python main.py  # Or the entry point file, e.g., app.py
   ```

#### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install  # Or yarn install
   ```

3. Start the development server:
   ```
   npm start  # Or yarn start
   ```

## Usage

1. **Access the Dashboard**: Open your browser and go to the frontend URL (e.g., http://localhost:3000).
2. **Add Domains**: Use the interface to add domains you want to monitor (e.g., example.com).
3. **View Status**: The dashboard displays current certificate status, expiration dates, and validity.
4. **Configure Alerts**: Set up thresholds for expiration warnings (e.g., alert 30 days before expiry).
5. **Historical View**: Check the history tab to see changes in certificate details over time.

For API usage (if exposed):
- GET `/api/certificates`: Retrieve list of monitored certificates.
- POST `/api/domains`: Add a new domain to monitor.

Refer to the API documentation in the backend for more endpoints (if available).

## Configuration

Configuration files are located in the respective directories:

- **Backend**: Edit `config.py` or `.env` for settings like database URL, check intervals, or notification emails.
- **Frontend**: Update `src/config.ts` for API base URL or other client-side settings.
- **Environment Variables**: Use a `.env` file for sensitive information (e.g., API keys if any).

Example `.env`:
```
DATABASE_URL=postgresql://user:password@localhost/db
CHECK_INTERVAL=3600  # In seconds
EMAIL_ALERTS=true
```

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

For questions or support, open an issue on GitHub or contact the maintainer at [alex.dembele@example.com](mailto:alex.dembele@example.com).

Thank you for using SSL Certificates Monitor! 🔒
