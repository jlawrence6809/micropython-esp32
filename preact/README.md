# MicroJsonLisp Web Interface

A modern, responsive web interface built with Preact for the ESP32-based home automation platform. This interface provides real-time device control, live sensor monitoring, and advanced automation rule management with backend validation integration.

## Overview

This web interface serves as the primary control panel for the MicroJsonLisp home automation platform. Designed to run efficiently on ESP32 microcontrollers while providing a modern web experience with real-time validation and comprehensive device management.

## Features

- **Real-time Device Control**: Manual control of relays with instant feedback and state visualization
- **Live Sensor Monitoring**: Real-time temperature, humidity, light levels, and switch states
- **Advanced Rule Editor**: Backend-validated automation rules with comprehensive error reporting
- **Intelligent Validation**: Server-side rule validation with precise error paths and type checking
- **System Management**: Device status, WiFi configuration, and system diagnostics
- **Responsive Design**: Optimized for desktop and mobile devices
- **Efficient Asset Management**: Optimized bundle size for ESP32 memory constraints
- **Modern Architecture**: Component-based design with TypeScript support

## Technology Stack

- **Framework**: Preact (3KB React alternative) with TypeScript
- **Build System**: Preact CLI with custom Webpack configuration
- **Validation**: Backend integration with comprehensive rule validation
- **State Management**: React hooks with efficient API integration
- **Asset Pipeline**: Custom ESP32 optimization with gzip compression
- **Testing**: Jest with TypeScript support

## Project Structure

```
preact/
├── src/
│   ├── index.tsx              # Main application entry point
│   ├── api.ts                 # Backend API integration layer
│   ├── types.ts               # TypeScript type definitions
│   ├── style.css             # Global application styles
│   ├── components/            # Reusable UI components
│   │   ├── AutomateDialog.tsx # Rule editor with backend validation
│   │   ├── Dialog.tsx         # Modal dialog framework
│   │   └── Section.tsx        # Layout section component
│   └── sections/              # Main application sections
│       ├── RelayControls.tsx  # Device control interface
│       ├── GlobalInfo.tsx     # System information display
│       ├── SensorInfo.tsx     # Live sensor monitoring
│       ├── WifiForm.tsx       # Network configuration
│       └── RestartButton.tsx  # System restart control
├── esp/                       # ESP32 build integration
│   ├── esp-build-plugin.js    # Custom Webpack plugin
│   └── static_files_h.ejs     # C header template
├── build/                     # Generated assets
│   ├── bundle.*.js           # Optimized JavaScript
│   ├── bundle.*.css          # Optimized CSS
│   ├── index.html            # Application HTML
│   └── static_files.h        # ESP32 embedded assets
├── package.json               # Dependencies and scripts
├── preact.config.js          # Build configuration
├── tsconfig.json             # TypeScript configuration
└── jest.config.js            # Test configuration
```

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- ESP32 development environment (PlatformIO)
- Basic understanding of React/Preact patterns

### Installation

1. **Install dependencies**:
   ```bash
   cd preact
   npm install
   ```

2. **Development mode**:
   ```bash
   npm run dev
   ```
   Starts development server at `http://localhost:8080` with hot reloading.

3. **Build for production**:
   ```bash
   npm run build
   ```
   Creates optimized assets and generates ESP32-ready `static_files.h`.

### Available Scripts

- `npm run build` - Full production build (TypeScript + Preact + ESP32 assets)
- `npm run build:ts` - TypeScript compilation only
- `npm run build:preact` - Preact application build only
- `npm run dev` - Development server with hot reloading
- `npm run serve` - Serve built files locally
- `npm run lint` - ESLint code analysis
- `npm test` - Run test suite
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Generate test coverage report
- `npm run format` - Format code with Prettier

## Architecture

### Component Design

**Section Components** (`sections/`):
- **RelayControls**: Main device control with relay management and rule editing
- **GlobalInfo**: System status including chip ID, temperature, and uptime
- **SensorInfo**: Live environmental sensor data display
- **WifiForm**: Network configuration with credential management
- **RestartButton**: System restart functionality

**Reusable Components** (`components/`):
- **AutomateDialog**: Advanced rule editor with backend validation integration
- **Dialog**: Modal framework for overlays and forms
- **Section**: Consistent layout wrapper for all sections

### API Integration

**Core API Layer** (`api.ts`):
```typescript
// Configuration management
fetchRelayConfig() → RelayConfigDto
postRelayConfig(RelayConfig[]) → Response

// Hardware control
fetchGpioOptions() → number[]

// Rule validation (NEW)
validateRule(string) → ValidationResponse
```

**Validation Response Structure**:
```typescript
interface ValidationResponse {
  success: boolean;
  error?: {
    message: string;    // Human-readable error description
    path: number[];     // Precise error location in nested rules
  };
  returnType?: number;  // Function return type for successful validation
}
```

## Advanced Rule Management

### Backend Validation Integration

The interface now leverages the ESP32's sophisticated rule engine for validation:

**Features**:
- **Real-time Validation**: Rules validated as you type using backend engine
- **Precise Error Reporting**: Exact error locations in nested expressions
- **Type Safety**: Comprehensive type checking with automatic conversions
- **Production Quality**: Same validation used for rule execution

**Validation Flow**:
1. User edits rule in AutomateDialog
2. Frontend sends rule to `/validate-rule` endpoint
3. ESP32 rule engine performs comprehensive validation
4. Results displayed with precise error information or success confirmation

### Rule Editor Features

**AutomateDialog Component**:
- **Inline Label Editing**: Click to edit relay labels
- **Syntax Validation**: Real-time feedback with backend validation
- **Error Display**: Visual indicators with detailed error messages
- **Path Tracking**: Shows exact location of errors in nested rules
- **Loading States**: Proper UX during validation requests

### Rule Syntax (JSON-based LISP)

**Basic Structure**:
```json
["FUNCTION_NAME", arg1, arg2, ...]
```

**Example Rules**:

*Simple temperature control*:
```json
["GT", ["getTemperature"], 25]
```

*Complex conditional logic*:
```json
["IF", 
  ["AND", 
    ["GT", ["getTemperature"], 30],
    ["LT", ["getHumidity"], 60]
  ],
  ["setRelay", "exhaust_fan", 1],
  ["setRelay", "exhaust_fan", 0]
]
```

*Time-based automation*:
```json
["IF", 
  ["EQ", ["getCurrentTime"], "@18:00:00"],
  ["setRelay", "lights", 1],
  ["setRelay", "lights", 0]
]
```

## ESP32 Integration

### Asset Optimization Pipeline

**Custom Build Process**:
1. **TypeScript Compilation**: Type checking and transpilation
2. **Preact Build**: Optimized JavaScript and CSS bundling
3. **Asset Compression**: Gzip compression for all static files
4. **C Header Generation**: Embedded assets for ESP32 flash storage

**Generated Output Structure**:
```c
// Generated static_files.h
const unsigned char bundle_js_gz[] PROGMEM = {
  0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00,
  // ... compressed JavaScript bundle
};
const size_t bundle_js_gz_len = 13480;
const char* bundle_js_mime = "application/javascript";
```

### Memory Optimization

**Bundle Size Management**:
- **Eliminated Frontend Validation**: Removed 659-line RuleParser.ts (-769 bytes)
- **Efficient Imports**: Tree-shaking for minimal bundle size
- **Gzip Compression**: Optimal compression for ESP32 flash storage
- **Asset Exclusion**: Removes development files from production build

### API Endpoint Integration

**Core Endpoints**:
- `GET /global-info` - System status and device information
- `GET /sensor-info` - Live sensor readings
- `GET /relay-config` - Relay configuration and rules
- `POST /relay-config` - Update relay settings and automation rules
- `GET /gpio-options` - Available GPIO pins for configuration
- `POST /validate-rule` - **NEW**: Comprehensive rule validation
- `POST /wifi-settings` - WiFi network configuration
- `POST /reset` - System restart

## Development Guidelines

### Code Organization

**TypeScript Standards**:
- Use proper type definitions in `types.ts`
- Leverage interface definitions for API responses
- Prefer type-safe API calls with proper error handling
- Use React hooks for state management

**Component Patterns**:
- Functional components with hooks
- Proper separation of concerns (logic vs. presentation)
- Efficient re-rendering with proper dependency arrays
- Error boundaries for graceful failure handling

### Testing Strategy

**Unit Testing**:
```bash
npm test                 # Run all tests
npm run test:watch      # Watch mode for development
npm run test:coverage   # Generate coverage reports
```

**Test Structure**:
- Component rendering tests
- API integration tests
- User interaction testing
- Validation flow testing

### Performance Optimization

**Bundle Size Constraints**:
- Monitor bundle size for ESP32 memory limits
- Use dynamic imports for large components when possible
- Optimize images and assets for web delivery
- Leverage tree-shaking for unused code elimination

**Runtime Performance**:
- Efficient state updates with React hooks
- Minimize unnecessary re-renders
- Optimize API call patterns
- Use proper loading states for better UX

## Deployment

### Production Build Process

```bash
# Complete build pipeline
npm run build
```

**Build Steps**:
1. TypeScript compilation with type checking
2. Preact bundling with optimization
3. Asset compression and ESP32 preparation
4. C header generation for firmware embedding

**Integration with ESP32**:
- Built assets automatically embedded in firmware
- Served from ESP32 flash memory with proper MIME types
- Gzip compression for efficient memory usage
- Cache headers for optimal browser performance

## Browser Compatibility

**Modern Browser Support**:
- Chrome 70+, Firefox 60+, Safari 12+, Edge 79+
- Mobile: iOS Safari 12+, Chrome Mobile 70+
- **Required Features**: ES6+, Fetch API, CSS Grid, Flexbox

**Graceful Degradation**:
- Core functionality works on older browsers
- Enhanced features for modern browser capabilities
- Mobile-responsive design for various screen sizes

## Security Considerations

**Local Network Design**:
- Designed for trusted local network environments
- No authentication required for local access
- Input validation on both client and server
- XSS protection through proper input sanitization

**Best Practices**:
- Validate all user inputs before submission
- Sanitize rule content before display
- Use HTTPS when available
- Secure API endpoint access patterns

## Contributing

**Development Standards**:
1. Follow TypeScript conventions and proper typing
2. Write tests for new functionality
3. Ensure bundle size optimization for ESP32
4. Update documentation for API changes
5. Test on actual ESP32 hardware when possible

**Code Quality**:
- Use ESLint and Prettier for consistent formatting
- Write meaningful commit messages
- Add proper component documentation
- Maintain backward compatibility when possible

---

*Modern web interface for intelligent ESP32 home automation, built with performance and user experience in mind.*