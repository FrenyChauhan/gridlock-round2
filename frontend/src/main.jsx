import React from 'react';
import ReactDOM from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './contexts/AuthContext';
import App from './App';
import './styles/tokens.css';
import 'leaflet/dist/leaflet.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <HashRouter>
          <App />
          <Toaster 
            position="bottom-right"
            toastOptions={{
              style: {
                background: 'var(--panel-raised)',
                color: 'var(--text-bright)',
                border: '1px solid var(--panel-border)',
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
              }
            }}
          />
        </HashRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
