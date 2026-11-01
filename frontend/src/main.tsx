import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import {AppProvider} from './app/provider';
import {App} from './app/App';
import './shared/styles.css';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><AppProvider><App/></AppProvider></BrowserRouter></React.StrictMode>);
import './features/planning/planning.css';

import './features/event-setup/publication.css';

import './features/sponsor-dashboard/sponsor.css';

import './features/participation/participation.css';
