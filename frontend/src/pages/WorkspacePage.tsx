import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const rolePaths = {
  STUDENT: '/student',
  ADMIN: '/admin',
  RECRUITER: '/recruiter',
  INTERVIEWER: '/interviewer',
} as const

export default function WorkspacePage() {
  const { user } = useAuth()
  if (!user) return null
  return <Navigate to={rolePaths[user.role]} replace />
}
