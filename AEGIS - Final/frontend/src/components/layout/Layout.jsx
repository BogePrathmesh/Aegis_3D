import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';

const Navbar = () => {
  return (
    <header className="w-full top-0 sticky z-50 bg-white/90 backdrop-blur-md border-b border-outline-variant/10 transition-colors duration-300">
      <div className="flex justify-between items-center w-full px-8 py-4 max-w-[1440px] mx-auto">
        <div className="flex items-center gap-12">
          <NavLink to="/" className="text-2xl font-bold font-headline text-slate-900">
            AEGIS
          </NavLink>
          <nav className="hidden md:flex items-center space-x-8">
            <NavLink 
              to="/dashboard" 
              className={({ isActive }) => 
                `text-slate-600 font-medium hover:text-primary transition-colors duration-300 font-headline tracking-tight text-lg ${isActive ? 'text-primary border-b-2 border-primary pb-1' : ''}`
              }
            >
              Dashboard
            </NavLink>
            <NavLink 
              to="/analyze" 
              className={({ isActive }) => 
                `text-slate-600 font-medium hover:text-primary transition-colors duration-300 font-headline tracking-tight text-lg ${isActive ? 'text-primary border-b-2 border-primary pb-1' : ''}`
              }
            >
              Inspect
            </NavLink>
            <NavLink 
              to="/simulate" 
              className={({ isActive }) => 
                `text-slate-600 font-medium hover:text-primary transition-colors duration-300 font-headline tracking-tight text-lg ${isActive ? 'text-primary border-b-2 border-primary pb-1' : ''}`
              }
            >
              Simulation
            </NavLink>
            <NavLink 
              to="/reports" 
              className={({ isActive }) => 
                `text-slate-600 font-medium hover:text-primary transition-colors duration-300 font-headline tracking-tight text-lg ${isActive ? 'text-primary border-b-2 border-primary pb-1' : ''}`
              }
            >
              Reports
            </NavLink>
             <NavLink 
              to="/budget" 
              className={({ isActive }) => 
                `text-slate-600 font-medium hover:text-primary transition-colors duration-300 font-headline tracking-tight text-lg ${isActive ? 'text-primary border-b-2 border-primary pb-1' : ''}`
              }
            >
              Budget
            </NavLink>
          </nav>
        </div>
        <div className="flex items-center gap-6">
          <button className="px-6 py-2.5 bg-primary text-on-primary rounded-lg font-semibold hover:brightness-95 transition-all">
            Get Started
          </button>
          <span className="material-symbols-outlined text-slate-600 cursor-pointer text-2xl hover:text-primary transition-colors">
            account_circle
          </span>
        </div>
      </div>
    </header>
  );
};

const Footer = () => {
  return (
    <footer className="w-full bg-slate-900 text-white mt-auto">
      <div className="flex flex-col md:flex-row justify-between items-start w-full px-12 py-20 max-w-[1440px] mx-auto">
        <div className="mb-12 md:mb-0 max-w-xs">
          <div className="font-headline text-2xl font-bold mb-4">AEGIS</div>
          <p className="font-body text-sm text-slate-400 leading-relaxed">
            Engineering-first intelligence for the world's most critical infrastructure.
          </p>
          <p className="mt-8 font-body text-xs text-slate-500">
            © 2026 AEGIS Intelligence. All rights reserved.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-16">
          <div>
            <div className="text-xs font-bold uppercase tracking-widest text-primary mb-6">Product</div>
            <nav className="flex flex-col gap-4">
              <span className="text-slate-400 text-sm hover:text-white transition-colors cursor-pointer">Fleet</span>
              <span className="text-slate-400 text-sm hover:text-white transition-colors cursor-pointer">Analysis</span>
              <span className="text-slate-400 text-sm hover:text-white transition-colors cursor-pointer">Pricing</span>
            </nav>
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-widest text-primary mb-6">Company</div>
            <nav className="flex flex-col gap-4">
              <span className="text-slate-400 text-sm hover:text-white transition-colors cursor-pointer">About</span>
              <span className="text-slate-400 text-sm hover:text-white transition-colors cursor-pointer">Careers</span>
              <span className="text-slate-400 text-sm hover:text-white transition-colors cursor-pointer">Contact</span>
            </nav>
          </div>
          <div className="col-span-2 md:col-span-1">
            <div className="text-xs font-bold uppercase tracking-widest text-primary mb-6">Legal</div>
            <nav className="flex flex-col gap-4">
              <span className="text-slate-400 text-sm hover:text-white transition-colors cursor-pointer">Privacy</span>
              <span className="text-slate-400 text-sm hover:text-white transition-colors cursor-pointer">Terms</span>
              <span className="text-slate-400 text-sm hover:text-white transition-colors cursor-pointer">Security</span>
            </nav>
          </div>
        </div>
      </div>
    </footer>
  );
};

const Layout = () => {
  return (
    <div className="min-h-screen flex flex-col bg-surface overflow-x-hidden">
      <Navbar />
      <main className="flex-grow">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
};

export default Layout;
