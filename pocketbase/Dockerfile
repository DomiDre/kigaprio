# from https://pocketbase.io/docs/going-to-production/#using-docker
FROM alpine:latest

ARG PB_VERSION=0.30.0
ARG USER_UID=1000
ARG USER_GID=1000

RUN apk add --no-cache \
    unzip \
    ca-certificates \
    su-exec

# Create a non-root user with specific UID/GID
RUN addgroup -g ${USER_GID} pocketbase && \
    adduser -D -u ${USER_UID} -G pocketbase -h /pb -s /bin/sh pocketbase

# download and unzip PocketBase
ADD https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_amd64.zip /tmp/pb.zip
RUN unzip /tmp/pb.zip -d /pb/ && \
    rm /tmp/pb.zip && \
    chmod +x /pb/pocketbase

# Create necessary directories with correct permissions
RUN mkdir -p /pb/pb_data /pb/pb_public /pb/pb_migrations /pb/pb_hooks && \
    chown -R ${USER_UID}:${USER_GID} /pb


# Copy the secrets loading script
COPY --chown=root:root load-secrets.sh /usr/local/bin/load-secrets.sh
RUN chmod +x /usr/local/bin/load-secrets.sh

# Switch to non-root user
USER pocketbase

WORKDIR /pb

EXPOSE 8090

ENTRYPOINT ["/usr/local/bin/load-secrets.sh"]
CMD ["./pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb/pb_data", "--publicDir=/pb/pb_public", "--migrationsDir=/pb/pb_migrations"]
