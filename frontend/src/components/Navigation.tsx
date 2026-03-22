import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export function Navigation() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  function handleSignOut() {
    signOut()
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/" className="brand-link">
          <span className="brand-text">Analyt</span>
          <span className="brand-accent">IQ</span>
        </Link>
      </div>

      <div className="navbar-menu">
        {user && (
          <>
            {user.role === 'student' && (
              <Link to="/classes" className="nav-link">My Classes</Link>
            )}
            {user.role === 'professor' && (
              <Link to="/dashboard" className="nav-link">Dashboard</Link>
            )}
            {(user.role === 'superadmin' || user.role === 'tenant_admin') && (
              <Link to="/admin" className="nav-link">Admin</Link>
            )}
          </>
        )}
      </div>

      <div className="navbar-actions">
        {user ? (
          <div className="user-menu">
            <span className="user-name">{user.name}</span>
            <span className="user-role-badge">{user.role}</span>
            <button onClick={handleSignOut} className="btn-ghost">Sign out</button>
          </div>
        ) : (
          <Link to="/login" className="btn btn-primary">Sign in</Link>
        )}
      </div>
    </nav>
  )
}
