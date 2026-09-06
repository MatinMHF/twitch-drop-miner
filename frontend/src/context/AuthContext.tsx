import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../services/api';
import { UserProfile, TwitchAccount } from '../services/types';

interface AuthContextType {
  user: UserProfile | null;
  twitchAccount: TwitchAccount | null;
  isLoading: boolean;
  login: (data: { username: string; password: string }) => Promise<void>;
  setupAdmin: (data: { username: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshTwitchAccount: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [twitchAccount, setTwitchAccount] = useState<TwitchAccount | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchAuth = async () => {
    try {
      const authStatus = await api.getAuthStatus();
      setUser(authStatus);
      if (authStatus.is_active) {
        const tw = await api.getTwitchAccount();
        setTwitchAccount(tw);
      }
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAuth();
  }, []);

  const login = async (credentials: { username: string; password: string }) => {
    await api.login(credentials);
    await fetchAuth();
  };

  const setupAdmin = async (credentials: { username: string; password: string }) => {
    await api.setupAdmin(credentials);
    await fetchAuth();
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    setTwitchAccount(null);
  };

  const refreshTwitchAccount = async () => {
    try {
      const tw = await api.getTwitchAccount();
      setTwitchAccount(tw);
    } catch {
      setTwitchAccount(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        twitchAccount,
        isLoading,
        login,
        setupAdmin,
        logout,
        refreshTwitchAccount,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
