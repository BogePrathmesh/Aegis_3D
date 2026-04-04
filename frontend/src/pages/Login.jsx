import React, { useState } from 'react';
import { useNavigate, NavLink } from 'react-router-dom';

const Login = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = (e) => {
    e.preventDefault();
    setLoading(true);
    // Simulate API Network call
    setTimeout(() => {
      navigate('/dashboard');
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Dynamic Background Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[120px] rounded-full mix-blend-screen pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-emerald-600/10 blur-[150px] rounded-full mix-blend-screen pointer-events-none"></div>

      <div className="w-full max-w-md relative z-10 animate-fade-in">
        {/* Logo Header */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-headline font-bold text-white tracking-widest mb-2">AEGIS</h1>
          <p className="text-sm font-body text-slate-400 tracking-wider uppercase">Infrastructure Intelligence</p>
        </div>

        {/* Glassmorphism Card */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-8 shadow-2xl shadow-black/50">
          <div className="mb-8">
            <h2 className="text-2xl font-headline font-semibold text-white mb-1">Enterprise Access</h2>
            <p className="text-slate-400 text-sm font-body">Sign in to your inspection portal.</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Corporate Email</label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-lg">mail</span>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-800/50 border border-slate-700 text-white rounded-lg pl-12 pr-4 py-3 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all font-body text-sm"
                  placeholder="engineer@aegis.com"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center block">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Passkey</label>
                <a href="#" className="text-xs text-primary hover:text-emerald-400 transition-colors">Forgot PIV?</a>
              </div>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-lg">lock</span>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-800/50 border border-slate-700 text-white rounded-lg pl-12 pr-4 py-3 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all font-body text-sm"
                  placeholder="••••••••••••"
                  required
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className={`w-full py-3.5 rounded-lg flex items-center justify-center gap-2 font-bold transition-all duration-300 ${
                loading 
                  ? 'bg-slate-700 text-slate-400 cursor-not-allowed' 
                  : 'bg-primary hover:bg-emerald-500 text-on-primary shadow-lg shadow-primary/25 hover:shadow-emerald-500/40 hover:-translate-y-0.5'
              }`}
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined animate-spin text-xl">progress_activity</span>
                  Authenticating...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-lg">fingerprint</span>
                  Secure Login
                </>
              )}
            </button>
          </form>

          {/* Registration Hook */}
          <div className="mt-8 pt-6 border-t border-slate-800 text-center">
            <p className="text-sm text-slate-400 font-body">
              New to AEGIS? <NavLink to="/register" className="text-primary hover:text-emerald-400 font-bold tracking-wide transition-colors">Request Access</NavLink>
            </p>
          </div>
        </div>

        {/* Footer info */}
        <div className="mt-12 text-center flex flex-col items-center gap-2">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-mono">
            <span className="material-symbols-outlined text-sm">verified_user</span>
            ISO-27001 Certified System
          </div>
          <p className="text-[10px] text-slate-600 uppercase tracking-widest">
            v3.0.0 · Core Engine Active
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
