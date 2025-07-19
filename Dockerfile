FROM ruby:3.4.4-slim
USER root

# Set build working dir
WORKDIR /build

# Install SOCKS5 support and essential packages
RUN apt-get update && \
    apt-get install -y dante-client python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Copy Ruby app files
COPY wayback-machine-downloader/ /build/

# Install Ruby dependencies
RUN bundle config set jobs "$(nproc)" \
    && bundle config set without 'development test' \
    && bundle install

# Switch to application directory
WORKDIR /app

# Copy Python app files
COPY requirements.txt .
COPY wayback_scraper.py .

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Create downloads directory
RUN mkdir -p downloads