import React, { useState } from 'react';
import { useNavigate, NavLink } from 'react-router-dom';

const Register = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  
  // Form placeholders
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [department, setDepartment] = useState('engineering');
  const [password, setPassword] = useState('');

  const handleRegister = (e) => {
    e.preventDefault();
    setLoading(true);
    // Simulate API Network call to provision workspace
    setTimeout(() => {
      navigate('/dashboard');
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Dynamic Background Elements */}
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[120px] rounded-full mix-blend-screen pointer-events-none"></div>
      <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-600/10 blur-[150px] rounded-full mix-blend-screen pointer-events-none"></div>

      <div className="w-full max-w-lg relative z-10 animate-fade-in py-8">
        {/* Logo Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-headline font-bold text-white tracking-widest mb-2">AEGIS</h1>
          <p className="text-sm font-body text-slate-400 tracking-wider uppercase">Infrastructure Intelligence</p>
        </div>

        {/* Glassmorphism Card */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-8 shadow-2xl shadow-black/50">
          <div className="mb-8">
            <h2 className="text-2xl font-headline font-semibold text-white mb-1">Request Enterprise Access</h2>
            <p className="text-slate-400 text-sm font-body">Provision a new inspector workspace.</p>
          </div>

          <form onSubmit={handleRegister} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Full Name</label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-lg">badge</span>
                  <input 
                    type="text" 
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-slate-800/50 border border-slate-700 text-white rounded-lg pl-11 pr-4 py-3 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all font-body text-sm"
                    placeholder="Jane Doe"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Department</label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-lg">corporate_fare</span>
                  <select 
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full bg-slate-800/50 border border-slate-700 text-white rounded-lg pl-11 pr-4 py-3 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all font-body text-sm appearance-none"
                  >
                    <option value="engineering">Structural Engineering</option>
                    <option value="inspection">Field Inspection</option>
                    <option value="executive">Executive Board</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Corporate Email</label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-lg">mail</span>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-800/50 border border-slate-700 text-white rounded-lg pl-11 pr-4 py-3 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all font-body text-sm"
                  placeholder="engineer@aegis.com"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Create Passkey</label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-lg">enhanced_encryption</span>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-800/50 border border-slate-700 text-white rounded-lg pl-11 pr-4 py-3 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all font-body text-sm"
                  placeholder="••••••••••••"
                  required
                  minLength={8}
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className={`w-full py-3.5 mt-2 rounded-lg flex items-center justify-center gap-2 font-bold transition-all duration-300 ${
                loading 
                  ? 'bg-slate-700 text-slate-400 cursor-not-allowed' 
                  : 'bg-primary hover:bg-emerald-500 text-on-primary shadow-lg shadow-primary/25 hover:shadow-emerald-500/40 hover:-translate-y-0.5'
              }`}
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined animate-spin text-xl">progress_activity</span>
                  Provisioning Workspace...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-lg">person_add</span>
                  Create Account
                </>
              )}
            </button>
          </form>

          {/* Login Hook */}
          <div className="mt-8 pt-6 border-t border-slate-800 text-center">
            <p className="text-sm text-slate-400 font-body">
              Already have authorized access? <NavLink to="/login" className="text-primary hover:text-emerald-400 font-bold tracking-wide transition-colors">Sign In</NavLink>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
