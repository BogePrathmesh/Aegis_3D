import React from 'react';
import { NavLink } from 'react-router-dom';

const ToolCard = ({ icon, title, description, link, dark = false }) => (
  <NavLink 
    to={link}
    className={`group text-left p-8 border rounded-2xl transition-all flex flex-col justify-between aspect-square ${
      dark 
        ? 'bg-slate-900 border-none shadow-xl' 
        : 'border-slate-200 hover:border-primary hover:bg-slate-50 shadow-sm'
    }`}
  >
    <div>
      <span className={`material-symbols-outlined text-4xl mb-6 ${dark ? 'text-primary' : 'text-slate-400 group-hover:text-primary transition-colors'}`}>
        {icon}
      </span>
      <h3 className={`text-2xl font-headline mb-3 ${dark ? 'text-white' : 'text-on-surface'}`}>
        {title}
      </h3>
      <p className={`text-sm leading-relaxed ${dark ? 'text-slate-400' : 'text-on-surface-variant'}`}>
        {description}
      </p>
    </div>
    <div className="text-primary font-bold text-xs uppercase tracking-widest flex items-center gap-2">
      {link === '/simulate' ? 'Launch Simulator' : link === '/analyze' ? 'Run Analysis' : 'Enter Workspace'} 
      <span className="material-symbols-outlined text-sm">arrow_forward</span>
    </div>
  </NavLink>
);

const Home = () => {
  return (
    <div className="animate-fade-in">
      {/* Hero Section */}
      <section className="relative min-h-[700px] flex items-center px-8 md:px-16 overflow-hidden pt-12 pb-24">
        <div className="max-w-[1440px] mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
          <div className="lg:col-span-6 z-10">
            <span className="inline-block text-primary px-0 py-1 rounded-full text-xs font-bold tracking-[0.2em] mb-6 uppercase">
              Infrastructure Intelligence Platform
            </span>
            <h1 className="text-6xl md:text-[84px] leading-[0.95] tracking-tight mb-8 text-on-surface font-headline font-bold">
              Precision Intelligence <br/>
              for the Built World
            </h1>
            <p className="text-xl md:text-2xl text-on-surface-variant max-w-xl mb-10 font-body leading-relaxed">
              Autonomous drone-based infrastructure defect detection and severity scoring with human-level accuracy. Built for rigorous engineering workflows.
            </p>
            <div className="flex flex-wrap gap-4 items-center">
              <NavLink to="/dashboard" className="btn-primary">
                Explore the Dashboard
                <span className="material-symbols-outlined text-xl">arrow_forward</span>
              </NavLink>
              <button className="btn-secondary">
                Request Technical Demo
              </button>
            </div>
            <div className="mt-16 flex items-center gap-8 pt-8 border-t border-outline-variant/10">
              <div className="flex -space-x-3">
                <div className="w-10 h-10 rounded-full border-2 border-white bg-slate-200"></div>
                <div className="w-10 h-10 rounded-full border-2 border-white bg-slate-300"></div>
              </div>
              <div className="text-xs font-label tracking-wide text-on-surface-variant uppercase">
                <span className="font-bold text-slate-900 block">12,000+ ASSETS</span>
                Continuously monitored globally
              </div>
            </div>
          </div>
          <div className="lg:col-span-6 relative">
            <div className="relative rounded-2xl overflow-hidden shadow-2xl bg-slate-900 aspect-video">
              {/* Image Placeholder */}
              <div className="absolute inset-0 bg-gradient-to-tr from-slate-900 to-slate-800 flex items-center justify-center">
                <span className="material-symbols-outlined text-white/10 text-9xl">engineering</span>
              </div>
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent"></div>
              <div className="absolute bottom-8 left-8 right-8 flex justify-between items-end">
                <div className="bg-white/10 backdrop-blur-md p-4 rounded-xl border border-white/20 text-white">
                  <div className="text-[10px] uppercase font-bold tracking-widest mb-1 opacity-70">AI Status</div>
                  <div className="text-sm font-medium flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                    Unified Engine Active
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Toolset Grid */}
      <section className="py-24 px-8 md:px-16 bg-white border-y border-slate-100">
        <div className="max-w-[1440px] mx-auto">
          <div className="mb-20">
            <h2 className="text-5xl md:text-6xl text-on-surface mb-6 font-headline">Engineering Toolset</h2>
            <p className="text-xl text-on-surface-variant max-w-2xl font-body">
              Integrated features for the complete asset management lifecycle—from ingestion to boardroom-ready reporting.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <ToolCard 
              icon="dashboard" 
              title="Dashboard" 
              description="Centralized fleet monitoring and asset portfolio health tracking."
              link="/dashboard"
            />
            <ToolCard 
              icon="search_insights" 
              title="Crack Detection" 
              description="AI-powered defect segmentation and surface analysis."
              link="/analyze"
            />
             <ToolCard 
              icon="view_in_ar" 
              title="3D Depth Map" 
              description="Volumetric reconstruction and topographical defect projection."
              link="/analyze" 
            />
            <ToolCard 
              icon="timeline" 
              title="Growth Prediction" 
              description="Finite Element Simulation for longitudinal crack propagation."
              link="/simulate"
            />
            <ToolCard 
              icon="priority_high" 
              title="Risk Ranking" 
              description="Maintenance prioritization through AI-optimized budget allocation."
              link="/budget"
            />
            <ToolCard 
              icon="cloud_upload" 
              title="Data Ingestion" 
              description="Secure high-res drone image upload and processing pipeline."
              link="/analyze"
            />
            <ToolCard 
              icon="picture_as_pdf" 
              title="Report Center" 
              description="Automated, engineering-compliant PDF inspection documentation."
              link="/reports"
            />
            <ToolCard 
              icon="warning" 
              title="Severity Index" 
              description="Standardized assessment metrics to prioritize critical maintenance."
              link="/dashboard"
              dark={true}
            />
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-32 px-8 md:px-16 bg-surface-container-low">
        <div className="max-w-[1440px] mx-auto grid grid-cols-1 md:grid-cols-3 gap-16">
          <div className="border-l border-slate-200 pl-8">
            <div className="label-sm text-primary mb-4">Inspection Accuracy</div>
            <div className="text-7xl font-headline mb-4">99.8%</div>
            <p className="text-on-surface-variant font-body text-sm">
              Exceeding standard human inspection benchmarks through sensor fusion AI.
            </p>
          </div>
          <div className="border-l border-slate-200 pl-8">
            <div className="label-sm text-primary mb-4">Operational Alpha</div>
            <div className="text-7xl font-headline mb-4">65%</div>
            <p className="text-on-surface-variant font-body text-sm">
              Reduction in traditional scaffolding and manual inspection overhead.
            </p>
          </div>
          <div className="border-l border-slate-200 pl-8">
            <div className="label-sm text-primary mb-4">Risk Mitigation</div>
            <div className="text-7xl font-headline mb-4">0.02</div>
            <p className="text-on-surface-variant font-body text-sm">
              Mean Variance reduction in structural failure probability predictions.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
