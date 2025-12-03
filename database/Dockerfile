FROM postgres:16.1-alpine

# Install Python, pip, and psycopg2
RUN apk add --no-cache python3 py3-pip py3-psycopg2

# Copy initialization scripts
COPY scripts/ /docker-entrypoint-initdb.d/
COPY migrations/ /migrations/

# Set permissions for scripts and migrations
RUN chmod -R +r /docker-entrypoint-initdb.d/ && \
    chmod -R +r /migrations/

# Set the working directory
WORKDIR /
