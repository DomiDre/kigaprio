# Development stage - Using standard node image to avoid musl issues
FROM node:20 AS development

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with clean slate
RUN npm ci

# Copy source code
COPY . .

# Expose port for Vite dev server
EXPOSE 5173

# Run development server with proper host binding
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]


# Alternative Development with Alpine (if you need smaller image)
FROM node:20-alpine AS development-alpine

WORKDIR /app

# Install build dependencies and libc6-compat for better compatibility
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    libc6-compat \
    && ln -s /lib/libc.musl-x86_64.so.1 /lib/ld-linux-x86-64.so.2

# Copy package files
COPY package*.json ./

# Force reinstall with proper platform
RUN npm cache clean --force && \
    npm install --platform=linuxmusl --arch=x64 && \
    # Manually ensure rollup musl package is installed
    npm install @rollup/rollup-linux-x64-musl@latest

# Copy source code
COPY . .

# Expose port for Vite dev server
EXPOSE 5173

# Run development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]


# Build stage
FROM node:20 AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Clean install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the SvelteKit app
RUN npm run build


# Production stage
FROM node:20-alpine AS production

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Copy package files first
COPY --from=builder --chown=nodejs:nodejs /app/package*.json ./

# Install only production dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# Copy built application
COPY --from=builder --chown=nodejs:nodejs /app/build ./build

# If you're using @sveltejs/adapter-node, also copy these:
# COPY --from=builder --chown=nodejs:nodejs /app/.svelte-kit ./.svelte-kit

# Switch to non-root user
USER nodejs

# Expose port
EXPOSE 3000

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the application
CMD ["node", "build"]
