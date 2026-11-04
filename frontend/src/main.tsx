import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import {AppProvider} from './app/provider';
import {App} from './app/App';
import './shared/styles.css';
// Trusted local CLI bootstrap: fragment is never sent to the HTTP server.
if(import.meta.env.DEV&&import.meta.env.VITE_AROUNDYOU_MODE==='http'){
 const bootstrap=new URLSearchParams(window.location.hash.slice(1)).get('local-session');
 if(bootstrap){sessionStorage.setItem('aroundyou.http.token',bootstrap);window.history.replaceState(null,'',window.location.pathname+window.location.search);}
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><AppProvider><App/></AppProvider></BrowserRouter></React.StrictMode>);
import './features/planning/planning.css';

import './features/event-setup/publication.css';

import './features/sponsor-dashboard/sponsor.css';

import './features/participation/participation.css';
