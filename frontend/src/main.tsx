import React from 'react';
import ReactDOM from 'react-dom/client';
import {AccessPortal} from './pages/AccessPortal';
import './index.css';
import 'leaflet/dist/leaflet.css';
import { startOfflineSupport } from './services/offline';
startOfflineSupport();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <AccessPortal />
  </React.StrictMode>
);
