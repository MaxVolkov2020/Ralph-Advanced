import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useStore } from './store';
import apiClient from './api/client';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Projects } from './pages/Projects';
import { CodebaseSettings } from './pages/CodebaseSettings';
import { Prompts } from './pages/Prompts';
import { PRDAnalysis } from './pages/PRDAnalysis';
import { Settings } from './pages/Settings';
import { Layout } from './components/Layout';
import { NotificationSystem } from './components/NotificationSystem';

function App() {
  const { isAuthenticated, setUser } = useStore();
  const [loading, setLoading] = React.useState(true);

  useEffect(() => {
    // Check if user is already authenticated
    const checkAuth = async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          const response = await apiClient.get('/auth/me');
          setUser(response.data);
        } catch (error) {
          localStorage.removeItem('auth_token');
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [setUser]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <>
      <NotificationSystem />
      <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/" /> : <Login />}
        />
        <Route
          path="/*"
          element={
            isAuthenticated ? (
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/projects" element={<Projects />} />
                  <Route path="/projects/:projectId" element={<Projects />} />
                  <Route path="/projects/:projectId/codebases" element={<CodebaseSettings />} />
                  <Route path="/prompts" element={<Prompts />} />
                  <Route path="/prd-analysis" element={<PRDAnalysis />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="*" element={<Navigate to="/" />} />
                </Routes>
              </Layout>
            ) : (
              <Navigate to="/login" />
            )
          }
        />
      </Routes>
    </BrowserRouter>
    </>
  );
}

export default App;
