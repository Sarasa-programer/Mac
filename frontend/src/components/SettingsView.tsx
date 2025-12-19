import { useState, useEffect } from 'react';
import { Save, User, Mail, Shield } from 'lucide-react';

interface SettingsViewProps {
  userEmail: string;
  onSave: (email: string) => void;
}

export function SettingsView({ userEmail, onSave }: SettingsViewProps) {
  const [localEmail, setLocalEmail] = useState(userEmail);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setLocalEmail(userEmail);
  }, [userEmail]);

  const validateEmail = (email: string) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const handleSave = () => {
    if (!validateEmail(localEmail)) {
      setError('Please enter a valid email address.');
      setSuccess(false);
      return;
    }
    setError('');
    onSave(localEmail);
    setSuccess(true);
    setTimeout(() => setSuccess(false), 3000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      
      <div className="glass-card overflow-hidden">
        <div className="p-8 border-b border-white/5">
          <div className="flex items-center gap-6 mb-8">
            <div className="w-20 h-20 rounded-full bg-white/5 border border-white/10 flex items-center justify-center shadow-inner">
              <User className="w-8 h-8 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white">Dr. Ahadinia Profile</h3>
              <p className="text-sm text-apple-gray mt-1">Manage your personal information and notifications</p>
            </div>
          </div>

          <div className="space-y-8 max-w-xl">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-white/80 mb-2">
                Email Address
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-white/40 group-focus-within:text-apple-blue transition-colors" />
                </div>
                <input
                  type="email"
                  id="email"
                  className={`block w-full pl-10 pr-3 py-2.5 bg-black/20 border ${error ? 'border-red-500/50 focus:border-red-500' : 'border-white/10 focus:border-apple-blue/50'} rounded-xl text-white placeholder-white/20 focus:outline-none focus:ring-1 focus:ring-apple-blue/50 transition-all`}
                  placeholder="doctor@hospital.org"
                  value={localEmail}
                  onChange={(e) => {
                    setLocalEmail(e.target.value);
                    setError('');
                    setSuccess(false);
                  }}
                />
              </div>
              {error && <p className="mt-2 text-sm text-red-400 flex items-center gap-2"><span className="w-1 h-1 rounded-full bg-red-400"></span>{error}</p>}
              {success && <p className="mt-2 text-sm text-emerald-400 flex items-center gap-2"><span className="w-1 h-1 rounded-full bg-emerald-400"></span>Settings saved successfully!</p>}
              <p className="mt-3 text-xs text-apple-gray">
                This email will be used for report notifications and account recovery.
              </p>
            </div>

            <div className="pt-4 border-t border-white/5">
                <h4 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-apple-blue" />
                    Security & Compliance
                </h4>
                <div className="bg-white/5 p-4 rounded-xl border border-white/5 text-xs text-apple-gray space-y-2.5">
                    <p className="flex items-center gap-2"><span className="w-1 h-1 rounded-full bg-white/40"></span>Your email is stored locally and securely.</p>
                    <p className="flex items-center gap-2"><span className="w-1 h-1 rounded-full bg-white/40"></span>We do not share your contact information with third parties.</p>
                    <p className="flex items-center gap-2"><span className="w-1 h-1 rounded-full bg-white/40"></span>HIPAA Compliance: No PHI is sent to this email address.</p>
                </div>
            </div>
          </div>
        </div>
        
        <div className="px-8 py-6 bg-white/5 border-t border-white/5 flex justify-end">
          <button
            onClick={handleSave}
            className="flex items-center gap-2 bg-apple-blue/90 hover:bg-apple-blue text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all shadow-lg shadow-apple-blue/20 hover:shadow-apple-blue/40 active:scale-95"
          >
            <Save className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
