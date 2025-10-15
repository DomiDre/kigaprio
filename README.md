# KigaPrio

<div align="center">

[![CI Status](https://github.com/DomiDre/kigaprio/actions/workflows/ci.yml/badge.svg)](https://github.com/DomiDre/kigaprio/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen.svg)](https://www.docker.com/)
[![GDPR Compliant](https://img.shields.io/badge/GDPR-Compliant-green.svg)](ARCHITECTURE.md#gdpr-compliance)

**Privacy-First Childcare Priority Management System**

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Contributing](#contributing)

</div>

---

## 📋 Overview

KigaPrio is a secure web application designed for childcare facilities to manage daily priorities with server-side encryption. It enables parents to submit childcare preferences while ensuring complete data privacy through user-controlled encryption and GDPR-compliant architecture.

### Key Capabilities
- 🔐 **Server-side encryption** with user-controlled security levels
- 📊 **Administrative reporting** with Excel generation for monthly overviews
- 👥 **Multi-role support** for parents and administrators
- 🛡️ **GDPR-compliant** data handling and storage
- 📱 **Responsive design** for mobile and desktop access

## 🏗️ Architecture

KigaPrio implements a privacy-first architecture with multiple layers of security. For detailed technical documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | FastAPI + Python 3.11 | Async API server with data validation |
| **Frontend** | SvelteKit | Modern reactive UI framework |
| **Database** | PocketBase | SQLite-based with built-in auth |
| **Cache** | Redis | Session management (memory-only) |
| **Proxy** | Traefik | TLS termination and routing |
| **Container** | Docker + Docker Compose | Consistent deployment environment |

### Security Model

Three-tier security system allowing users to choose their preferred balance:

- **🔒 High Security**: Session-based, no server storage
- **⚖️ Balanced Mode**: Split-key encryption with timeout (default)
- **🔓 Convenience**: Persistent client storage for trusted devices

Details in [ARCHITECTURE.md](ARCHITECTURE.md#three-tier-security-model).

## 🚀 Quick Start

### Prerequisites

- Docker Engine ≥ 24.0
- Docker Compose ≥ 2.20
- [just](https://github.com/casey/just) command runner
- 2GB available RAM
- 1GB available disk space

### Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/DomiDre/kigaprio.git
cd kigaprio
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

2. **Deploy**
```bash
# Build production images
just build

# Start production services
just prod
```

## 📁 Project Structure

```
kigaprio/
├── backend/              # FastAPI application
│   ├── src/kigaprio/     # Application code
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
- **Bug Reports**: [GitHub Issues](https://github.com/DomiDre/kigaprio/issues)
- **Discussions**: [GitHub Discussions](https://github.com/DomiDre/kigaprio/discussions)
