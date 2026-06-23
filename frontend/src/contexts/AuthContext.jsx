import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem('gridlock_token'));
  const [role, setRole] = useState(localStorage.getItem('gridlock_role'));

  useEffect(() => {
    const handleStorageChange = () => {
      setToken(localStorage.getItem('gridlock_token'));
      setRole(localStorage.getItem('gridlock_role'));
    };
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const login = (newToken, newRole) => {
    localStorage.setItem('gridlock_token', newToken);
    localStorage.setItem('gridlock_role', newRole);
    setToken(newToken);
    setRole(newRole);
    window.dispatchEvent(new Event('storage'));
  };

  const logout = () => {
    localStorage.removeItem('gridlock_token');
    localStorage.removeItem('gridlock_role');
    setToken(null);
    setRole(null);
    window.dispatchEvent(new Event('storage'));
  };

  return (
    <AuthContext.Provider value={{ token, role, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
