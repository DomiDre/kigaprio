# PrioTag

<div align="center">

[![CI Status](https://github.com/DomiDre/priotag/actions/workflows/ci.yml/badge.svg)](https://github.com/DomiDre/priotag/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen.svg)](https://www.docker.com/)
[![GDPR Compliant](https://img.shields.io/badge/GDPR-Compliant-green.svg)](ARCHITECTURE.md#gdpr-compliance)

**Privacy-First Childcare Priority Management System**

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Contributing](#contributing)

</div>

---

## 📋 Overview

PrioTag is a secure web application designed for a single childcare facility to manage daily priorities with server-side encryption. It enables parents to submit childcare preferences while ensuring complete data privacy through user-controlled encryption and GDPR-compliant architecture.

### Key Capabilities
- 🔐 **Server-side encryption** with user-controlled security levels
- 📊 **Administrative reporting** with Excel generation for monthly overviews
- 👥 **Multi-role support** for parents and administrators
- 🛡️ **GDPR-compliant** data handling and storage
- 📱 **Responsive design** for mobile and desktop access

## 🏗️ Architecture

PrioTag implements a privacy-first architecture with multiple layers of security. For detailed technical documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

### Technology Stack

| Component      | Technology              | Purpose                                                           |
| -------------- | ----------------------- | ----------------------------------------------------------------- |
| **Backend**    | FastAPI + Python 3.11   | Async API server for data validation & server-side encryption     |
| **Frontend**   | SvelteKit               | Modern reactive UI framework                                      |
| **Database**   | PocketBase              | SQLite-based with built-in auth                                   |
| **Cache**      | Redis                   | Session management                                                |
| **Proxy**      | Traefik                 | TLS termination and routing                                       |
| **Monitoring** | Prometheus              | Active monitoring for malicious access attempts with e-mail alert |
| **Container**  | Docker + Docker Compose | Consistent deployment environment                                 |

### Security Model

When registering, a data encryption key (DEK) is generated and stored once encrypted by the user password and once by the public key of the administration. 
To read and write data the DEK is send at login together with the session token as httpOnly cookie.
For proper data validation and to rely on proper encryption libraries, the encryption happens server-side during a request.

Details in [ARCHITECTURE.md](ARCHITECTURE.md).

## 🚀 Quick Start

### Prerequisites

- Docker Engine ≥ 24.0
- Docker Compose ≥ 2.20
- [just](https://github.com/casey/just) command runner
- 2 GB available RAM (usage actually < 500 MB)
- 3 GB available disk space

### Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/DomiDre/priotag.git
cd priotag
```

2. **Start development environment**
```bash
# Build development containers
just dev-build

# Start all services (FastAPI, SvelteKit, PocketBase, Redis)
just dev
```

3. **Access the application**
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/api/docs
- PocketBase Admin: http://localhost:8090/_/

### Production Deployment

1. **Initialize environment**
```bash
# Generate secure secrets
just init-secrets

# Initialize PocketBase storage
just pocketbase-init
```

On a local device perform
```bash
just init-admin-key
```
to generate public/private key pair. Move public key to server and keep private key safe.

Run
```bash
just services-init
```
to generate folders with proper permissions and seperate user + groups for each service.


2. **Deploy**
```bash
# Build production images
just build

# Start production services
just prod
```

## 📁 Project Structure

```
priotag/
├── backend/              # FastAPI application
│   ├── src/priotag/     # Application code
│   │   ├── api/          # API endpoints
│   │   ├── middleware/   # Middleware in requests, e.g. token refresh
│   │   ├── models/       # Data models
│   │   ├── scripts/      # Python scripts, e.g. initial admin private key generation
│   │   └── services/     # Business logic
│   └── pyproject.toml    # Python dependencies
├── frontend/             # SvelteKit application
│   ├── src/              # Source code
│   │   ├── routes/       # Page routes
│   │   ├── lib/          # Shared components
│   └── static/           # Static assets
├── admin_ui/             # SvelteKit application for admin access
├── monitoring/           # Setup for prometheus monitoring service
├── justfile              # Command automation
└── docker-compose.yml    # Service orchestration
```

## 🔧 Development

### Available Commands

```bash
# Development
just dev           # Start development environment
just dev-build     # Build development containers
just lint          # Run linters
just format        # Auto-format code

# Production
just build         # Build production images
just prod          # Start production environment
just logs          # View production logs
```

### Code Quality

The project maintains code quality through:

- **Linting**: Ruff for Python, ESLint for JavaScript
- **Formatting**: Ruff for Python, Prettier for JavaScript
- **Type Checking**: mypy for Python, TypeScript for frontend
- **Pre-commit Hooks**: Automated checks before commits
- **Testing**: Unit and integration tests with pytest, coverage reports via [Codecov](https://codecov.io/gh/DomiDre/priotag)

Tests run automatically in CI using docker-compose services for production-like testing. Run tests locally:
```bash
# Local development (uses testcontainers)
cd backend && uv run pytest

# CI mode (uses docker-compose, tests built container)
./scripts/test-ci-locally.sh
```

### API Documentation

Interactive API documentation is available via Swagger UI:
- Development: http://localhost:8000/api/docs

## 🔒 Security

### Data Protection

- **Encryption at Rest**: AES-256-GCM for all sensitive data
- **Encryption in Transit**: TLS 1.3 for all connections
- **Key Management**: User-specific keys with secure derivation
- **No Persistent Storage**: Plaintext data exists only transiently during processing, immediately discarded after use

### GDPR Compliance

Full compliance with GDPR requirements including:
- Right to access (data export)
- Right to rectification (data editing)
- Right to erasure (account deletion)
- Data portability (JSON/CSV export)
- Privacy by design

See [ARCHITECTURE.md](ARCHITECTURE.md#gdpr-compliance) for details.

### Security Headers

All responses include security headers:
- `Strict-Transport-Security`
- `Content-Security-Policy`
- `X-Frame-Options`
- `X-Content-Type-Options`

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Check existing issues** or create a new one
2. **Fork the repository**
3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** following code style guidelines
5. **Test thoroughly**
6. **Submit a pull request** with clear description

### Development Guidelines

- Follow existing code style
- Add tests for new functionality
- Update documentation as needed
- Ensure all checks pass before submitting PR

## 📚 Documentation

- [Architecture Document](ARCHITECTURE.md) - Detailed system design
- [API Documentation](http://localhost:8000/api/docs) - Interactive API docs (need to run dev server)

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SvelteKit](https://kit.svelte.dev/) - Full-stack web framework
- [PocketBase](https://pocketbase.io/) - Open source backend
- [Docker](https://www.docker.com/) - Container platform

## 📞 Support

For issues and questions:
- **Bug Reports**: [GitHub Issues](https://github.com/DomiDre/priotag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/DomiDre/priotag/discussions)
