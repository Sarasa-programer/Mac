import { UserRole } from '../types';
import { LayoutDashboard, UploadCloud, Library, Settings, Stethoscope, LogOut } from 'lucide-react';
import clsx from 'clsx';

interface SidebarProps {
  currentRole: UserRole;
  activeView: string;
  onNavigate: (view: string) => void;
}

export function Sidebar({ currentRole, activeView, onNavigate }: SidebarProps) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload', label: 'Upload Case', icon: UploadCloud, role: UserRole.PROFESSOR },
    { id: 'library', label: 'Case Library', icon: Library },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-72 h-screen fixed left-0 top-0 flex flex-col z-50">
      {/* Glass Background */}
      <div className="absolute inset-0 bg-black/20 backdrop-blur-2xl border-r border-white/5" />

      {/* Content */}
      <div className="relative flex flex-col h-full z-10">
        
        {/* Header */}
        <div className="p-8 pb-4">
          <div className="flex items-center gap-4 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center shadow-lg shadow-blue-500/5">
              <Stethoscope className="w-5 h-5 text-apple-blue" />
            </div>
            <div>
              <h1 className="font-semibold text-white tracking-tight text-lg">PedsMorningAI</h1>
              <p className="text-xs text-apple-gray font-medium">Pediatric Education</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 space-y-2 overflow-y-auto py-6">
          <div className="text-xs font-medium text-white/20 px-4 mb-2 uppercase tracking-wider">Menu</div>
          {navItems.map((item) => {
            if (item.role && item.role !== currentRole) return null;
            
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={clsx(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 group",
                  isActive 
                    ? "bg-white/10 text-white shadow-lg shadow-black/10 border border-white/5" 
                    : "text-apple-gray hover:text-white hover:bg-white/5 border border-transparent"
                )}
              >
                <item.icon className={clsx(
                  "w-5 h-5 transition-colors duration-300", 
                  isActive ? "text-apple-blue" : "text-white/40 group-hover:text-white/80"
                )} />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 m-4 rounded-2xl bg-white/5 border border-white/5 backdrop-blur-md">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-400/20 to-purple-400/20 border border-white/10 flex items-center justify-center text-white/80">
              <span className="font-bold text-xs tracking-wider">
                  {currentRole === UserRole.PROFESSOR ? 'DR' : currentRole === UserRole.RESIDENT ? 'RS' : 'ST'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">Dr. karimian</p>
              <p className="text-xs text-white/40 truncate capitalize">{currentRole.toLowerCase()}</p>
            </div>
          </div>
          <button className="w-full flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium text-white/40 hover:text-white hover:bg-white/5 rounded-lg transition-all duration-200">
              <LogOut className="w-3 h-3" />
              Sign Out
          </button>
        </div>
      </div>
    </aside>
  );
}
