import React, { useState } from 'react';
import { NavLink, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '@/components/ui/Button';
import {
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  ShoppingBag,
  Sliders,
  Users,
  BarChart3,
  User,
  LogOut,
  Building,
  Sun,
  Moon,
  ChevronDown,
  Menu,
  X,
  Bell,
  Settings
} from 'lucide-react';
import { cn } from '@/utils/cn';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const { user, companies, activeCompanyId, switchCompany, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isCompanyDropdownOpen, setIsCompanyDropdownOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  // Active company name
  const activeCompany = companies.find((c) => c.company_id === activeCompanyId);

  // Build breadcrumbs
  const pathnames = location.pathname.split('/').filter((x) => x);

  const navItems = [
    { label: 'Overview', path: '/dashboard', icon: LayoutDashboard },
    { label: 'Live Chat', path: '/chat', icon: MessageSquare },
    { label: 'Knowledge Base', path: '/knowledge', icon: BookOpen },
    { label: 'Product Catalog', path: '/products', icon: ShoppingBag },
    { label: 'Widget Settings', path: '/widget', icon: Sliders },
    { label: 'Team Members', path: '/members', icon: Users },
    { label: 'Analytics Reports', path: '/analytics', icon: BarChart3 },
    { label: 'Workspace Settings', path: '/companies', icon: Settings },
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-background flex text-foreground transition-colors duration-300">
      
      {/* 1. Sidebar - Desktop view */}
      <aside className="hidden lg:flex flex-col w-64 border-r border-border/40 bg-card/60 backdrop-blur-md sticky top-0 h-screen shrink-0">
        {/* Branding header */}
        <div className="h-16 flex items-center gap-2.5 px-6 border-b border-border/40">
          <Building className="h-5 w-5 text-primary" />
          <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-primary to-indigo-500 bg-clip-text text-transparent">
            SupportAI
          </span>
        </div>

        {/* Sidebar Nav items */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-250 hover:bg-accent/60",
                  {
                    "bg-primary text-primary-foreground hover:bg-primary/95 shadow-sm shadow-primary/20": isActive,
                    "text-muted-foreground hover:text-foreground": !isActive,
                  }
                )
              }
            >
              <item.icon className="h-4.5 w-4.5" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer Profile summary */}
        <div className="p-4 border-t border-border/40 bg-muted/15 flex flex-col gap-2">
          <div className="flex items-center gap-3 px-2 py-1.5">
            <div className="h-9 w-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center font-bold text-sm text-primary uppercase">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate leading-none mb-1">
                {user?.full_name}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {user?.email}
              </p>
            </div>
          </div>
          <Link
            to="/profile"
            className="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-all"
          >
            <User className="h-3.5 w-3.5" />
            <span>Account Settings</span>
          </Link>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium text-destructive hover:bg-destructive/10 transition-all text-left w-full"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Log Out</span>
          </button>
        </div>
      </aside>

      {/* 2. Mobile Drawer Navigation Overlay */}
      {isSidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="fixed inset-0 bg-background/80 backdrop-blur-sm" onClick={() => setIsSidebarOpen(false)} />
          <aside className="fixed top-0 bottom-0 left-0 w-64 bg-card border-r border-border/40 p-6 flex flex-col gap-6 shadow-xl animate-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building className="h-5 w-5 text-primary" />
                <span className="font-bold text-lg">SupportAI</span>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setIsSidebarOpen(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>

            <nav className="flex-1 space-y-1.5 overflow-y-auto">
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsSidebarOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all hover:bg-accent",
                      {
                        "bg-primary text-primary-foreground": isActive,
                        "text-muted-foreground hover:text-foreground": !isActive,
                      }
                    )
                  }
                >
                  <item.icon className="h-4.5 w-4.5" />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </nav>

            <div className="border-t border-border/40 pt-4 flex flex-col gap-2">
              <div className="flex items-center gap-3 py-1.5">
                <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center font-bold text-sm text-primary uppercase">
                  {user?.full_name?.charAt(0) || 'U'}
                </div>
                <div>
                  <p className="text-sm font-semibold truncate leading-none mb-1">{user?.full_name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                </div>
              </div>
              <Link
                to="/profile"
                onClick={() => setIsSidebarOpen(false)}
                className="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <User className="h-3.5 w-3.5" />
                <span>Account Settings</span>
              </Link>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium text-destructive hover:bg-destructive/10 text-left w-full"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Log Out</span>
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* 3. Main Workspace Container */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        
        {/* Top Navbar */}
        <header className="h-16 border-b border-border/40 bg-card/45 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-30">
          
          {/* Left section: Hamburger + Switcher */}
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setIsSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>

            {/* Workspace Company Switcher */}
            <div className="relative">
              <button
                onClick={() => setIsCompanyDropdownOpen(!isCompanyDropdownOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border/40 bg-background/50 hover:bg-accent/40 text-sm font-medium transition-all max-w-[200px]"
              >
                <Building className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="truncate">
                  {activeCompany ? activeCompany.name : 'Select Company'}
                </span>
                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0 ml-1" />
              </button>

              {isCompanyDropdownOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setIsCompanyDropdownOpen(false)} />
                  <div className="absolute left-0 mt-2 w-56 rounded-xl border border-border bg-card p-1 shadow-lg z-50 animate-in fade-in-50 slide-in-from-top-1 duration-150">
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Workspaces
                    </div>
                    {companies.map((co) => (
                      <button
                        key={co.company_id}
                        onClick={async () => {
                          await switchCompany(co.company_id);
                          setIsCompanyDropdownOpen(false);
                        }}
                        className={cn(
                          "w-full text-left px-2.5 py-2 rounded-lg text-sm transition-all flex items-center justify-between",
                          co.company_id === activeCompanyId
                            ? "bg-primary/10 text-primary font-medium"
                            : "hover:bg-accent text-foreground"
                        )}
                      >
                        <span className="truncate">{co.name}</span>
                        {co.company_id === activeCompanyId && (
                          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                        )}
                      </button>
                    ))}
                    <div className="border-t border-border/40 my-1" />
                    <Link
                      to="/companies"
                      onClick={() => setIsCompanyDropdownOpen(false)}
                      className="flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm hover:bg-accent text-primary font-medium"
                    >
                      <Building className="h-3.5 w-3.5" />
                      <span>Manage Workspaces</span>
                    </Link>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Right section: Actions + Notifications + Profile */}
          <div className="flex items-center gap-3">
            {/* Theme Toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              className="rounded-full h-9 w-9 text-muted-foreground hover:text-foreground"
            >
              {theme === 'dark' ? <Sun className="h-4.5 w-4.5" /> : <Moon className="h-4.5 w-4.5" />}
            </Button>

            {/* Notifications Panel */}
            <div className="relative">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
                className="rounded-full h-9 w-9 text-muted-foreground hover:text-foreground"
              >
                <Bell className="h-4.5 w-4.5" />
              </Button>

              {isNotificationsOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setIsNotificationsOpen(false)} />
                  <div className="absolute right-0 mt-2 w-80 rounded-xl border border-border bg-card p-3 shadow-lg z-50 animate-in fade-in-50 slide-in-from-top-1 duration-150">
                    <div className="flex items-center justify-between pb-2 border-b border-border/40 mb-2">
                      <span className="text-sm font-semibold">Notifications</span>
                      <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">
                        0 New
                      </span>
                    </div>
                    <div className="py-6 text-center text-xs text-muted-foreground">
                      No notifications at this time.
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Profile Circle Dropdown */}
            <div className="relative">
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="h-9 w-9 rounded-full bg-primary/10 border border-primary/20 hover:border-primary/45 flex items-center justify-center font-bold text-sm text-primary uppercase transition-all shrink-0"
              >
                {user?.full_name?.charAt(0) || 'U'}
              </button>

              {isUserMenuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setIsUserMenuOpen(false)} />
                  <div className="absolute right-0 mt-2 w-48 rounded-xl border border-border bg-card p-1 shadow-lg z-50 animate-in fade-in-50 slide-in-from-top-1 duration-150">
                    <div className="px-2.5 py-2 text-xs border-b border-border/40 mb-1">
                      <p className="font-semibold text-foreground truncate">{user?.full_name}</p>
                      <p className="text-muted-foreground truncate">{user?.email}</p>
                    </div>
                    <Link
                      to="/profile"
                      onClick={() => setIsUserMenuOpen(false)}
                      className="flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent"
                    >
                      <User className="h-4 w-4" />
                      <span>My Profile</span>
                    </Link>
                    <button
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        handleLogout();
                      }}
                      className="w-full text-left flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm text-destructive hover:bg-destructive/10"
                    >
                      <LogOut className="h-4 w-4" />
                      <span>Log Out</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Content container */}
        <main className="flex-1 p-6 md:p-8 flex flex-col gap-6 overflow-y-auto max-w-7xl w-full mx-auto">
          
          {/* Breadcrumbs */}
          {pathnames.length > 0 && (
            <nav className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <Link to="/dashboard" className="hover:text-foreground transition-all">
                Home
              </Link>
              {pathnames.map((name, index) => {
                const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
                const isLast = index === pathnames.length - 1;
                const formattedName = name.charAt(0).toUpperCase() + name.slice(1);

                return (
                  <React.Fragment key={name}>
                    <span>/</span>
                    {isLast ? (
                      <span className="text-foreground font-semibold">
                        {formattedName}
                      </span>
                    ) : (
                      <Link to={routeTo} className="hover:text-foreground transition-all">
                        {formattedName}
                      </Link>
                    )}
                  </React.Fragment>
                );
              })}
            </nav>
          )}

          {/* Children View Slot */}
          <div className="flex-1 flex flex-col min-h-0">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
