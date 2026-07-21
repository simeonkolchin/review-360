import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import BackgroundFX from './components/BackgroundFX'
import { useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Chats from './pages/Chats'
import ChatDetail from './pages/ChatDetail'
import Results from './pages/Results'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <>
        <BackgroundFX />
        <div className="grid place-items-center h-screen text-[var(--color-text-secondary)]">Загрузка…</div>
      </>
    )
  }

  if (!user) {
    return (
      <>
        <BackgroundFX />
        <Login />
      </>
    )
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Chats />} />
        <Route path="/chats/:chatId" element={<ChatDetail />} />
        <Route path="/rounds/:roundId" element={<Results />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
