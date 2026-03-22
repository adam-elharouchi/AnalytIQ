import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="page page--centered">
      <div className="error-state">
        <p className="error-code">404</p>
        <h1 className="error-title">Page not found</h1>
        <p className="error-hint">The page you're looking for doesn't exist.</p>
        <Link to="/" className="btn btn-primary">Go home</Link>
      </div>
    </div>
  )
}
