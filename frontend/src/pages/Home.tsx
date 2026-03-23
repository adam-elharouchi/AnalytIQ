import { Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

const TILES = [
  {
    icon: '⊞',
    title: 'My Classes',
    description: 'Access your enrolled classes, view modules, practice exercises, and resources for each course.',
    to: '/classes',
    roles: ['student'],
  },
  {
    icon: '⊞',
    title: 'Dashboard',
    description: 'Manage your classes, upload materials, create exercises, and track student progress.',
    to: '/dashboard',
    roles: ['professor'],
  },
  {
    icon: '</> ',
    title: 'Code',
    description: 'AI-powered assistant that helps you write code, analyze data, derive insights, and create visualizations.',
    to: '/code-assistant',
    roles: ['student', 'professor', 'superadmin', 'tenant_admin'],
  },
  {
    icon: '⊙',
    title: 'Profile',
    description: 'Manage your profile information, update your account settings, and customize your preferences.',
    to: '/profile',
    roles: ['student', 'professor', 'superadmin', 'tenant_admin'],
  },
]

export default function Home() {
  const { user } = useAuth()

  const visibleTiles = TILES.filter(t => user?.role && t.roles.includes(user.role))

  return (
    <div className="home-page">
      <div className="home-hero">
        <h1 className="home-title">
          Welcome to <span className="brand-accent">AnalytIQ</span>
        </h1>
        <p className="home-subtitle">
          Your comprehensive platform for mastering data analytics. Learn, practice, and master
          data analytics skills with interactive tools and resources.
        </p>
      </div>

      <div className="home-tiles">
        {visibleTiles.map(tile => (
          <Link key={tile.to} to={tile.to} className="home-tile">
            <div className="home-tile-icon">{tile.icon}</div>
            <div className="home-tile-body">
              <div className="home-tile-title">{tile.title}</div>
              <div className="home-tile-desc">{tile.description}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
