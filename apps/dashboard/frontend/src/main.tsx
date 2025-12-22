import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Type declaration for intro screen
declare global {
  interface Window {
    __dashboardReady?: () => void;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <App />,
)

// Signal that dashboard is ready (intro will hide when video ends)
window.__dashboardReady?.()
