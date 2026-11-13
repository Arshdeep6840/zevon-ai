import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import { isNative } from './api.js'
import './styles.css'

if ('serviceWorker' in navigator && !isNative()) {
  navigator.serviceWorker.register('./sw.js').catch(() => {})
}
createRoot(document.getElementById('root')).render(<App />)
