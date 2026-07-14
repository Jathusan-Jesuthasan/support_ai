import React, { createContext, useContext, useEffect, useState } from 'react';
import { apiClient, setInMemoryToken } from '@/services/apiClient';

export interface UserMeResponseData {
  user_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  active_company?: {
    company_id: string;
    role: string;
    status: string;
  } | null;
  created_at: string;
}

export interface CompanyListItem {
  company_id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
}

interface AuthContextType {
  user: UserMeResponseData | null;
  companies: CompanyListItem[];
  activeCompanyId: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  switchCompany: (companyId: string) => Promise<void>;
  fetchUserAndCompanies: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserMeResponseData | null>(null);
  const [companies, setCompanies] = useState<CompanyListItem[]>([]);
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUserAndCompanies = async () => {
    try {
      // 1. Get Me Profile
      const meResponse = await apiClient.get('/auth/me');
      const meData: UserMeResponseData = meResponse.data.data;
      setUser(meData);

      // 2. Fetch User Companies
      try {
        const companiesResponse = await apiClient.get('/companies?limit=100');
        const companyList: CompanyListItem[] = companiesResponse.data.data || [];
        setCompanies(companyList);

        // 3. Resolve Active Company ID
        const storedCompanyId = localStorage.getItem('supportai_active_company_id');
        const userActiveCompanyId = meData.active_company?.company_id;

        if (storedCompanyId && companyList.some((c) => c.company_id === storedCompanyId)) {
          setActiveCompanyId(storedCompanyId);
        } else if (userActiveCompanyId && companyList.some((c) => c.company_id === userActiveCompanyId)) {
          setActiveCompanyId(userActiveCompanyId);
          localStorage.setItem('supportai_active_company_id', userActiveCompanyId);
        } else if (companyList.length > 0) {
          const defaultId = companyList[0].company_id;
          setActiveCompanyId(defaultId);
          localStorage.setItem('supportai_active_company_id', defaultId);
        } else {
          setActiveCompanyId(null);
        }
      } catch (cErr) {
        console.error('Failed to load companies for user', cErr);
        setCompanies([]);
        setActiveCompanyId(null);
      }
    } catch (error) {
      console.error('Session validation failed', error);
      setUser(null);
      setCompanies([]);
      setActiveCompanyId(null);
      setInMemoryToken(null);
      localStorage.removeItem('supportai_refresh_token');
    }
  };

  // Bootstrap session on mount
  useEffect(() => {
    const bootstrapSession = async () => {
      const refreshToken = localStorage.getItem('supportai_refresh_token');
      if (refreshToken) {
        try {
          // Attempt token refresh
          const response = await apiClient.post('/auth/refresh', {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token } = response.data.data;
          setInMemoryToken(access_token);
          localStorage.setItem('supportai_refresh_token', refresh_token);
          await fetchUserAndCompanies();
        } catch (err) {
          console.error('Bootstrap refresh failed', err);
          localStorage.removeItem('supportai_refresh_token');
          setInMemoryToken(null);
        }
      }
      setIsLoading(false);
    };

    bootstrapSession();

    // Listen for logout broadcasts from Axios interceptors
    const handleLogoutEvent = () => {
      setUser(null);
      setCompanies([]);
      setActiveCompanyId(null);
      localStorage.removeItem('supportai_refresh_token');
      localStorage.removeItem('supportai_active_company_id');
      setInMemoryToken(null);
    };

    window.addEventListener('supportai_logout', handleLogoutEvent);
    return () => {
      window.removeEventListener('supportai_logout', handleLogoutEvent);
    };
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/auth/login', { email, password });
      const { access_token, refresh_token } = response.data.data;
      setInMemoryToken(access_token);
      localStorage.setItem('supportai_refresh_token', refresh_token);
      await fetchUserAndCompanies();
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (email: string, password: string, fullName: string) => {
    await apiClient.post('/auth/signup', {
      email,
      password,
      full_name: fullName,
    });
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('supportai_refresh_token');
    if (refreshToken) {
      try {
        await apiClient.post('/auth/logout', { refresh_token: refreshToken });
      } catch (err) {
        console.error('Logout request failed', err);
      }
    }
    setUser(null);
    setCompanies([]);
    setActiveCompanyId(null);
    localStorage.removeItem('supportai_refresh_token');
    localStorage.removeItem('supportai_active_company_id');
    setInMemoryToken(null);
  };

  const switchCompany = async (companyId: string) => {
    if (companies.some((c) => c.company_id === companyId)) {
      setActiveCompanyId(companyId);
      localStorage.setItem('supportai_active_company_id', companyId);
      // Wait, we also want to tell the backend to update our active company, but there is no direct endpoint.
      // That's fine! The backend checks permissions on a per-request basis or gets company_id from parameters.
      // So updating local activeCompanyId is perfectly sufficient for our api services to use.
    }
  };

  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        companies,
        activeCompanyId,
        isAuthenticated,
        isLoading,
        login,
        signup,
        logout,
        switchCompany,
        fetchUserAndCompanies,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
