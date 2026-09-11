// ==============================================================================
// File: client/src/main.tsx
// Purpose: The JavaScript/TypeScript doorway for our React application.
//
// What this file does:
// 1. Finds the HTML element with id="root" in index.html.
// 2. Uses ReactDOM.createRoot to mount our top-level <App /> component into that element.
// 3. Imports global styles (Tailwind CSS).
//
// Flow:
// [Browser requests index.html]
//       │
//       ▼
// [HTML loads main.tsx]
//       │
//       ▼
// [createRoot mounts App component inside #root]
// ==============================================================================

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Mount the App component into the HTML DOM container
const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error("Failed to find the root element. Ensure index.html contains <div id='root'></div>");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
