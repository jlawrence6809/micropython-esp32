import mime from 'mime-types';
import ejs from 'ejs';
import { readFileSync, writeFileSync } from 'fs';
import { gzipSync } from 'zlib';

/**
 * ESPBuildPlugin - Custom Webpack Plugin for ESP32 Asset Embedding
 *
 * This plugin converts web assets (HTML, CSS, JS) into C header files that can be
 * embedded directly into ESP32 firmware. This allows the ESP32 to serve a complete
 * web interface without requiring external storage.
 *
 * Process:
 * 1. Intercepts Webpack's built assets
 * 2. Compresses each asset with gzip
 * 3. Converts binary data to C byte arrays
 * 4. Generates a C header file with all assets embedded
 *
 * The resulting header file can be #included in ESP32 Arduino code to serve
 * the web interface directly from flash memory.
 */
class ESPBuildPlugin {
  constructor(options) {
    this.compiler = null; // Webpack compiler instance
    this.assets = []; // Array to store processed assets
    this.options = options || {}; // Plugin options (e.g., exclude patterns)
    this.pluginName = this.constructor.name;
  }

  /**
   * Webpack plugin entry point - registers hooks to process assets
   *
   * Hooks into two key Webpack events:
   * - assetEmitted: Called when each asset is written to output directory
   * - afterEmit: Called after all assets are processed, triggers C header generation
   */
  apply(compiler) {
    this.compiler = compiler;

    // Hook: Process each asset as it's emitted by Webpack
    compiler.hooks.assetEmitted.tap(this.pluginName, file => {
      this.addAsset(file);
    });

    // Hook: After all assets are processed, generate the final C header file
    compiler.hooks.afterEmit.tap(this.pluginName, () => {
      this.createESPOutputFile();
    });
  }

  /**
   * Process a single asset file for ESP32 embedding
   *
   * @param {string} file - The filename of the asset to process
   *
   * Steps:
   * 1. Check if file should be excluded (based on options.exclude patterns)
   * 2. Read the file and compress it with gzip
   * 3. Convert to C byte array format
   * 4. Store metadata (path, MIME type, normalized name for C variables)
   */
  addAsset(file) {
    // Skip files that match exclusion patterns (e.g., '200.html', 'push-manifest.json')
    for (var pattern of this.options.exclude || []) {
      if (file.match(pattern) !== null) {
        // Asset is excluded from ESP32 embedding
        return false;
      }
    }

    // Build full file path and determine MIME type for HTTP headers
    const path = this.compiler.options.output.path + '/' + file;
    const mimeType = mime.lookup(path);

    // Read, compress, and convert file to C byte array
    const asset = this.readAndProcessAsset(path);

    // Store asset with metadata needed for C header generation
    this.assets.push({
      path: '/' + file, // URL path for ESP32 web server
      normalizedName: file.replace(/[^0-9a-z]/gi, '_'), // Valid C variable name
      mimeType, // Content-Type for HTTP response
      ...asset, // contents (C byte array) and size
    });

    this.getLogger().info(
      `Added asset ${file} with a size of ${asset.size} bytes.`,
    );
  }

  /**
   * Read a file, compress it, and convert to C byte array format
   *
   * @param {string} path - Full file path to read
   * @returns {Object} - Object with 'contents' (C byte array string) and 'size' (bytes)
   *
   * Process:
   * 1. Read file as binary data
   * 2. Compress with gzip (reduces size significantly for text files)
   * 3. Convert each byte to hexadecimal C format (0x1f, 0x8b, etc.)
   * 4. Format as multi-line C array with 16 bytes per line for readability
   */
  readAndProcessAsset(path) {
    var response = '';

    // Read file and compress with gzip to minimize ESP32 flash usage
    var contents = gzipSync(new Uint8Array(readFileSync(path)));

    // Convert binary data to C byte array format
    for (var i = 0; i < contents.length; i++) {
      // Start new line every 16 bytes for readable C code
      if (i % 16 == 0) response += '\n';

      // Convert byte to hex format: 0x1f, 0x8b, etc.
      response += '0x' + ('00' + contents[i].toString(16)).slice(-2);

      // Add comma separator except for the last byte
      if (i < contents.length - 1) response += ', ';
    }

    return {
      contents: response, // String containing C byte array
      size: contents.length, // Size in bytes (after compression)
    };
  }

  /**
   * Generate the final C header file containing all embedded assets
   *
   * Uses EJS template (static_files_h.ejs) to generate a C header file with:
   * - Byte arrays for each asset (const unsigned char asset_name_gz[])
   * - Size constants (const size_t asset_name_gz_len)
   * - Metadata for MIME types and URL paths
   *
   * The generated static_files.h can be #included in ESP32 Arduino code
   * to serve the complete web interface from flash memory.
   */
  createESPOutputFile() {
    // Render the EJS template with all processed assets
    ejs.renderFile(
      'esp/static_files_h.ejs', // Template file
      { files: this.assets }, // Template data: array of asset objects
      {}, // EJS options (none needed)
      (err, str) => {
        if (err) {
          this.getLogger().error('Failed to generate C header file:', err);
          return;
        }

        // Write the generated C header file to the build directory
        const outputPath =
          this.compiler.options.output.path + '/static_files.h';
        writeFileSync(outputPath, str);

        this.getLogger().info(
          `Build artifact has been written to ${outputPath}.`,
        );
      },
    );
  }

  /**
   * Get Webpack's infrastructure logger for consistent logging
   * @returns {Object} Webpack logger instance
   */
  getLogger() {
    return this.compiler.getInfrastructureLogger(this.pluginName);
  }
}

module.exports = ESPBuildPlugin;
export default ESPBuildPlugin;
