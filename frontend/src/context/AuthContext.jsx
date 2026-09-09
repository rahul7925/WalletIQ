import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api, setStoredToken } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setTokenState] = useState(() => {
    try {
      return localStorage.getItem('walletiq_token');
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Verify stored session on mount
  useEffect(() => {
    let isMounted = true;

    async function checkAuth() {
      try {
        const storedToken = localStorage.getItem('walletiq_token');
        if (storedToken) {
          const res = await api.getMe();
          if (isMounted && res && res.user) {
            setUser(res.user);
          }
        }
      } catch (err) {
        console.warn('Session verification failed:', err.message);
        setStoredToken(null);
        if (isMounted) {
          setUser(null);
          setTokenState(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    checkAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (username, password, remember = true) => {
    setAuthError(null);
    try {
      const res = await api.login({ username, password, remember });
      if (res.token) {
        setStoredToken(res.token);
        setTokenState(res.token);
      }
      setUser(res.user);
      return res.user;
    } catch (err) {
      setAuthError(err.message || 'Login failed');
      throw err;
    }
  }, []);

  const register = useCallback(async (data) => {
    setAuthError(null);
    try {
      const res = await api.register(data);
      if (res.token) {
        setStoredToken(res.token);
        setTokenState(res.token);
      }
      setUser(res.user);
      return res.user;
    } catch (err) {
      setAuthError(err.message || 'Registration failed');
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch (err) {
      console.warn('Logout API error:', err);
    } finally {
      setStoredToken(null);
      setTokenState(null);
      setUser(null);
    }
  }, []);

  const updateUser = useCallback((updatedUserData) => {
    setUser((prev) => ({ ...prev, ...updatedUserData }));
  }, []);

  const value = {
    user,
    token,
    isAuthenticated: !!user,
    isLoading,
    authError,
    login,
    register,
    logout,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
