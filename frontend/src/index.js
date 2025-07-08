/* This is the entry point of the React application.
   It renders the main App component into the root element of the HTML to integrate it */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
