# KigaPrio

A FastAPI application for analyzing images and PDFs with Excel report generation.

## Features

- 📁 Multi-file upload support (images and PDFs)
- 🔍 Automated analysis of uploaded files
- 📊 Excel report generation
- 🚀 FastAPI with async processing
- 🐳 Docker support for development and production
- 🎨 Frontend-ready (serves compiled Svelte apps)
- ⚡ Built with UV for fast dependency management


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

Run development setup
```bash
just dev
```

### Production Setup

**Run production environment**:
```bash
just build
just prod
```

## API Endpoints

### This is just a first suggestion. This is bound to be changed soon.


### Health Check
- `GET /api/health` - Health check endpoint

### File Upload
- `POST /api/upload` - Upload files for analysis
  - Accepts multiple files
  - Supports: JPG, PNG, PDF, GIF, BMP, TIFF
  - Max file size: 50MB (configurable)

### Analysis
- `POST /api/analyze` - Start analysis job
- `GET /api/analyze/{job_id}/status` - Check job status
- `GET /api/analyze/{job_id}/download` - Download Excel results

### Frontend
- `GET /` - Serves Svelte frontend (when built)
- `GET /static/*` - Static assets


## Development Workflow

1. **Code changes**: The development setup includes volume mounts, so code changes are reflected immediately
2. **Add dependencies**: 
   ```bash
   uv add package-name
   # Rebuild Docker image
   docker compose -f docker-compose.dev.yml up --build app
   ```
4. **Testing**: 
   ```bash
   uv run pytest
   ```

## Customization

### Configuration
Edit `src/kigaprio/config.py` to modify:
- File size limits
- Allowed file types
- Processing timeouts
- CORS settings

### Processing Logic
Extend `src/kigaprio/services/file_processor.py` to add:
- New file type support
- Advanced image analysis
- OCR capabilities
- AI-powered analysis

### Excel Output
Modify `src/kigaprio/services/excel_generator.py` to customize:
- Report format
- Charts and visualizations
- Multiple sheets
- Custom styling

## Production Considerations

### Security
- Use docker secrets for secrets
- Implement authentication if needed
- Configure proper CORS origins
- Use HTTPS in production

### Scaling
- Use proper database instead of in-memory storage
- Configure multiple workers

### Monitoring
- Add logging with structured format
- Implement health checks
- Monitor file storage usage
- Set up alerts

## Troubleshooting

### Common Issues

1. **File upload fails**:
   - Check file size limits
   - Verify file extensions
   - Ensure upload directory permissions

2. **Docker build fails**:
   - Clear Docker cache: `docker system prune -a`
   - Check Dockerfile syntax
   - Verify uv.lock file exists

3. **Frontend not served**:
   - Ensure Svelte app is built
   - Check static files are copied correctly
   - Verify file permissions

### Logs
```bash
# Development
docker compose -f docker-compose.dev.yml logs -f app

# Production
docker compose logs -f app
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test
4. Submit pull request

## License

GNU GPLv3 - see LICENSE file for details.
