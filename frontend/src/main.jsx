import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Intercept global fetch calls to prepend VITE_API_URL in production if specified
const originalFetch = window.fetch;
window.fetch = function (input, init) {
  const apiBase = import.meta.env.VITE_API_URL || '';
  if (apiBase) {
    if (typeof input === 'string' && input.startsWith('/api')) {
      input = `${apiBase}${input}`;
    } else if (input instanceof Request && input.url.startsWith('/api')) {
      const newUrl = `${apiBase}${input.url}`;
      input = new Request(newUrl, input);
    }
  }
  return originalFetch.call(this, input, init);
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
