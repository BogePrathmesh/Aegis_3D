import React from 'react';
import DataExplorer from '../components/DataExplorer';
import OnSiteAnalysis from '../components/OnSiteAnalysis';

const Dashboard = () => {
    return (
        <div className="max-w-[1440px] mx-auto px-8 py-12 animate-fade-in">
             <header className="mb-12 border-b border-slate-200 pb-8 flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-headline text-on-surface mb-2">Fleet Dashboard</h1>
                    <p className="text-on-surface-variant max-w-2xl text-lg">
                        Central command for asset performance, risk ranking, and historical analysis.
                    </p>
                </div>
                <div className="hidden md:flex gap-4">
                    <div className="px-4 py-2 border-l border-slate-200">
                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">Total Assets</div>
                        <div className="text-2xl font-headline font-bold">142</div>
                    </div>
                     <div className="px-4 py-2 border-l border-slate-200">
                        <div className="text-[10px] font-bold uppercase tracking-widest text-rose-500 mb-1">Critical Priority</div>
                        <div className="text-2xl font-headline font-bold text-rose-600">3</div>
                    </div>
                </div>
            </header>
            
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <DataExplorer />
            </div>
        </div>
    );
};

export default Dashboard;
