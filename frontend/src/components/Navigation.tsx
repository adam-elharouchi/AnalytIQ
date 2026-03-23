import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export function Navigation() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  function handleSignOut() {
    signOut()
    navigate('/login')
  }

  const initials = user?.name
    ? user.name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2)
    : '?'

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/home" className="brand-link">
          <span className="brand-text">Analyt</span>
          <span className="brand-accent">IQ</span>
        </Link>
      </div>

      <div className="navbar-menu">
        {user && (
          <>
            <NavLink
              to="/home"
              className={({ isActive }) => 'nav-link' + (isActive ? ' nav-link--active' : '')}
            >
              Home
            </NavLink>

            {user.role === 'student' && (
              <NavLink
                to="/classes"
                className={({ isActive }) => 'nav-link' + (isActive ? ' nav-link--active' : '')}
              >
                My Classes
              </NavLink>
            )}

            {user.role === 'professor' && (
              <NavLink
                to="/dashboard"
                className={({ isActive }) => 'nav-link' + (isActive ? ' nav-link--active' : '')}
              >
                My Classes
              </NavLink>
            )}

            {(user.role === 'superadmin' || user.role === 'tenant_admin') && (
              <NavLink
                to="/admin"
                className={({ isActive }) => 'nav-link' + (isActive ? ' nav-link--active' : '')}
              >
                Admin
              </NavLink>
            )}

            <NavLink
              to="/code-assistant"
              className={({ isActive }) => 'nav-link' + (isActive ? ' nav-link--active' : '')}
            >
              Code
            </NavLink>
          </>
        )}
      </div>

      <div className="navbar-actions">
        {user ? (
          <div className="user-menu">
            <NavLink
              to="/profile"
              className={({ isActive }) => 'nav-avatar' + (isActive ? ' nav-avatar--active' : '')}
              title={user.name}
            >
              {initials}
            </NavLink>
            <button onClick={handleSignOut} className="btn-ghost">Sign out</button>
          </div>
        ) : (
          <Link to="/login" className="btn btn-primary">Sign in</Link>
        )}
      </div>
    </nav>
  )
}
