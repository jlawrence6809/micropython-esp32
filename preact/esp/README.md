# ESP32 Build System

This directory contains the custom build system that embeds web assets directly into ESP32 firmware. This allows the ESP32 to serve a complete web interface without requiring external storage like an SD card or SPIFFS.

## Overview

The ESP32 build system converts web assets (HTML, CSS, JavaScript) into C header files that can be compiled directly into the ESP32 firmware. This approach provides several benefits:

- **No External Storage**: Everything is stored in flash memory
- **Fast Access**: Assets are served directly from memory
- **Reliability**: No file system corruption issues
- **Simplicity**: Single firmware file contains everything

## Files

### `esp-build-plugin.js`

Custom Webpack plugin that handles the asset embedding process. This is the main component that:

1. **Intercepts Webpack Assets**: Hooks into Webpack's build process to capture generated files
2. **Compresses Assets**: Uses gzip compression to minimize memory usage
3. **Converts to C Format**: Transforms binary data into C byte arrays
4. **Generates Header**: Creates a complete C header file with all assets

### `static_files_h.ejs`

EJS template that generates the final C header file. This template creates:

- Individual byte arrays for each asset
- Size constants for each asset
- A structured array containing metadata (path, MIME type, size, contents)
- Helper constants for iteration

## How It Works

### 1. Asset Collection

When Webpack builds the web interface, the plugin intercepts each generated file:

```javascript
// Files like: index.html, bundle.js, bundle.css, etc.
compiler.hooks.assetEmitted.tap('ESPBuildPlugin', file => {
  this.addAsset(file);
});
```

### 2. Asset Processing

Each asset goes through several transformations:

```javascript
// 1. Read file as binary data
const fileContent = readFileSync(path);

// 2. Compress with gzip (often 70-80% size reduction)
const compressed = gzipSync(fileContent);

// 3. Convert to C byte array format
// Before: [0x1f, 0x8b, 0x08, ...]
// After: "0x1f, 0x8b, 0x08, ..."
```

### 3. C Header Generation

The EJS template generates a header file like this:

```c
#pragma once

namespace static_files {
    // Individual asset arrays
    const uint8_t f_index_html_contents[] PROGMEM = {
        0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00,
        // ... compressed HTML content
    };
    const uint32_t f_index_html_size PROGMEM = 1234;

    // Metadata structure
    struct file {
        const char *path;
        uint32_t size;
        const char *type;
        const uint8_t *contents;
    };

    // Array of all files
    const file files[] PROGMEM = {
        {
            .path = "/",
            .size = f_index_html_size,
            .type = "text/html",
            .contents = f_index_html_contents
        },
        // ... more files
    };
}
```

## Usage in ESP32 Code

The generated header can be used in ESP32 Arduino code like this:

```cpp
#include "static_files.h"

// Serve a file from embedded assets
void serveFile(const String& path, AsyncWebServerRequest* request) {
    for (int i = 0; i < static_files::num_of_files; i++) {
        if (strcmp(static_files::files[i].path, path.c_str()) == 0) {
            AsyncWebServerResponse* response = request->beginResponse_P(
                200,
                static_files::files[i].type,
                static_files::files[i].contents,
                static_files::files[i].size
            );
            response->addHeader("Content-Encoding", "gzip");
            request->send(response);
            return;
        }
    }
    request->send(404, "text/plain", "Not Found");
}
```

## Configuration

### Exclusion Patterns

Files can be excluded from embedding using the plugin options:

```javascript
// In preact.config.js
new ESPBuildPlugin({
  exclude: [
    '200.html', // SPA fallback page
    'preact_prerender_data.json', // Build metadata
    'push-manifest.json', // PWA manifest
  ],
});
```

### Memory Considerations

The ESP32 has limited flash memory, so assets are optimized:

- **Gzip Compression**: Typically reduces size by 70-80%
- **Tree Shaking**: Unused code is eliminated
- **Minification**: JavaScript and CSS are minified
- **Asset Exclusion**: Unnecessary files are skipped

## Generated Output Example

A typical build might generate something like:

```
Assets processed:
- index.html (2.1KB → 0.8KB after gzip)
- bundle.js (45.2KB → 12.3KB after gzip)
- bundle.css (3.4KB → 1.1KB after gzip)

Total embedded size: ~14.2KB
```

## Template Details (`static_files_h.ejs`)

The EJS template uses several variables:

- `files`: Array of processed assets
- `files[i].path`: URL path (e.g., "/", "/bundle.js")
- `files[i].normalizedName`: C-safe variable name (e.g., "index_html", "bundle_js")
- `files[i].mimeType`: Content-Type header (e.g., "text/html", "application/javascript")
- `files[i].contents`: C byte array string
- `files[i].size`: Compressed size in bytes

### Template Flow

1. **Generate Individual Arrays**: Creates byte arrays for each asset
2. **Create Metadata Structure**: Defines the file structure
3. **Build File Array**: Creates array of all files with metadata
4. **Add Helper Constants**: Provides count and utility functions

## Integration with Webpack

The plugin integrates with Webpack through the standard plugin API:

```javascript
// Webpack calls this when plugin is added
apply(compiler) {
    // Hook into asset emission
    compiler.hooks.assetEmitted.tap('ESPBuildPlugin', (file) => {
        this.addAsset(file);
    });

    // Hook into completion
    compiler.hooks.afterEmit.tap('ESPBuildPlugin', () => {
        this.createESPOutputFile();
    });
}
```

## Debugging

### Build Logs

The plugin provides detailed logging:

```
Added asset index.html with a size of 832 bytes.
Added asset bundle.7a1aa.js with a size of 12567 bytes.
Added asset bundle.b8d1a.css with a size of 1098 bytes.
Build artifact has been written to /path/to/build/static_files.h.
```

### Common Issues

1. **Memory Overflow**: If total assets exceed ESP32 flash capacity
   - Solution: Add more exclusion patterns or optimize assets

2. **Invalid C Names**: If filenames contain special characters
   - Solution: The plugin automatically normalizes names (e.g., "app-bundle.js" → "app_bundle_js")

3. **MIME Type Issues**: If files aren't served with correct headers
   - Solution: Check that `mime-types` package recognizes the file extension

## Performance Considerations

### Build Time

- Asset processing adds ~1-2 seconds to build time
- Gzip compression is the most time-intensive step
- Template rendering is typically <100ms

### Runtime Performance

- **Memory Usage**: Assets consume RAM when served (temporary)
- **Serving Speed**: Very fast (direct memory access)
- **CPU Usage**: Minimal (no file system operations)

## Future Enhancements

Potential improvements to the build system:

1. **Brotli Compression**: Better compression than gzip (requires ESP32 support)
2. **Asset Chunking**: Split large files across multiple headers
3. **Dynamic Loading**: Load assets on-demand rather than all at once
4. **Cache Headers**: Generate appropriate cache control headers
5. **Source Maps**: Embed source maps for debugging (development builds)

## Troubleshooting

### Build Failures

If the build fails, check:

1. **File Permissions**: Ensure write access to build directory
2. **Memory Limits**: Very large assets may cause issues
3. **Template Syntax**: EJS template must be valid
4. **Path Issues**: File paths must be accessible from build directory

### Runtime Issues

If assets don't serve correctly:

1. **Content-Encoding**: Ensure "gzip" header is set
2. **MIME Types**: Verify correct Content-Type headers
3. **Path Matching**: Check URL paths match exactly
4. **Flash Memory**: Ensure ESP32 has sufficient flash space

---

This build system enables the ESP32 to serve a complete modern web interface while maintaining the simplicity and reliability of embedded systems.
