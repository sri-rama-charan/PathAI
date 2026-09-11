// ==============================================================================
// File: client/vite.config.ts
// Purpose: Configuration file for Vite (the build tool and local dev server).
//
// What this file does:
// 1. Configures React support via @vitejs/plugin-react (enables JSX/TSX and Fast Refresh).
// 2. Configures Tailwind CSS support via @tailwindcss/vite.
// 3. Defines dev server port (default 5173).
// ==============================================================================

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    // Optional: Enables automatic opening in the browser if desired
    open: false,
  },
});
