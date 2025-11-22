#!/bin/bash

# Build and deploy the Preact web interface to ESP32
# Usage: ./scripts/deploy_web.sh

set -e

# Resolve paths
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
PREACT_DIR="$PROJECT_ROOT/preact"
BUILD_DIR="$PREACT_DIR/build"
REMOTE_SCRIPT="$SCRIPT_DIR/remote.sh"

echo "=== Building Web Interface ==="
cd "$PREACT_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Build the project
echo "Running npm run build..."
npm run build

echo ""
echo "=== Preparing Assets ==="
cd "$BUILD_DIR"

# Create a temporary staging directory
STAGING_DIR="$PROJECT_ROOT/web_staging"
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

# Copy files to staging and gzip them
# We gzip them but keep the original name so we can upload them as ".gz" if needed
# or just upload the compressed file and serve it.
# For MicroPython, it's often easiest to upload "index.html.gz" and have the code serve that.

echo "Compressing assets..."
for file in $(find . -type f -not -name ".*" -not -name "*.map" -not -name "200.html" -not -name "push-manifest.json" -not -name "preact_prerender_data.json"); do
    # strip leading ./
    filename="${file#./}"
    dir=$(dirname "$filename")
    
    mkdir -p "$STAGING_DIR/$dir"
    
    echo "Compressing $filename -> $filename.gz"
    gzip -c "$file" > "$STAGING_DIR/$filename.gz"
done

echo ""
echo "=== Uploading to ESP32 ==="

# Ensure /www directory exists on device
echo "Creating /www directory on device..."
"$REMOTE_SCRIPT" fs mkdir /www 2>/dev/null || true
"$REMOTE_SCRIPT" fs mkdir /www/assets 2>/dev/null || true

# Upload files
cd "$STAGING_DIR"
for file in $(find . -type f); do
    # strip leading ./
    filename="${file#./}"
    
    # Target path on device (e.g., /www/index.html.gz)
    target_path="/www/$filename"
    
    echo "Uploading $filename to $target_path..."
    "$REMOTE_SCRIPT" fs cp "$filename" ":$target_path"
done

# Clean up
rm -rf "$STAGING_DIR"

echo ""
echo "Deployment complete! Web assets are in /www/"

