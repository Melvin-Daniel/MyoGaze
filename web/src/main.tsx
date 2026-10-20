import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/myogaze.css'
import { applyTheme } from './theme'
import App from './App.tsx'

applyTheme()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
