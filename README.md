# KigaPrio

[![CI](https://github.com/DomiDre/kigaprio/actions/workflows/ci.yml/badge.svg)](https://github.com/DomiDre/kigaprio/actions/workflows/ci.yml)

A web application to submit priorities of each day respective for each week allow the administration to generate spreadsheets for overview.

## Features
### Performance & Architecture

⚡ Async Processing - Non-blocking request handling with FastAPI's async capabilities
🎨 Modern Frontend - Compiled Svelte app served as static assets
🚀 Fast Dependencies - UV-powered backend for rapid package installation and management

### Data & Reporting

📊 Excel Generation - Automated report creation and export functionality
💾 PocketBase Integration - Lightweight database accessible exclusively through FastAPI

### Security

🔐 Authentication - PocketBase auth system protecting all API endpoints
👥 Role-Based Access - Granular permission control for different user roles

### DevOps

🐳 Docker Support - Containerized setup for both development and production environments
🔧 Environment Flexibility - Easy switching between dev and prod configurations

## Quick Start

### Development Setup

1. **Clone and setup**:
```bash
git clone https://github.com/DomiDre/kigaprio
cd kigaprio
```

2. **Install just & docker**
All default scripts are collected in the `justfile`. Consider [installing it](https://github.com/casey/just) or look up commands from it.

The environment is defined for usage in docker containers.

3. **Development setup**:
Build dev containers
```bash
just dev-build
```

Run development setup (both backend, frontend and also loads pocketbase and redis instance)
```bash
just dev
```

### Production Setup

**Prepare production environment**:
Initialize secrets with
```bash
just init-secrets
```

And initialize pocketbase folders with
```bash
just pocketbase-init
```

**Run production environment**:
```bash
just build
just prod
```

## API Endpoints

To get backend API endpoints, run for example `just dev` and go to `http://localhost:8000/api/docs`
to view swagger-ui interface.

## Development Workflow

1. **Code changes**: The development setup includes volume mounts, so code changes are reflected immediately
2. **Linting**: 
   ```bash
   just lint
   just format
   ```

Unit tests are not yet properly implemented, so there is no workflow for that.


## Contributing

See issues for open problems that are going to be worked upon. If something is missing feel free to add issues.

To provide an implementation of anything:
1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test
4. Submit pull request


## License

GNU GPLv3 - see LICENSE file for details.
