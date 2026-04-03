import React from 'react';
import Simulator from '../components/Simulator';

const Simulation = () => {
    return (
        <div className="max-w-[1440px] mx-auto px-8 py-12 animate-fade-in">
             <header className="mb-12 border-b border-slate-200 pb-8 flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-headline text-on-surface mb-2">Degradation Simulation</h1>
                    <p className="text-on-surface-variant max-w-2xl text-lg">
                        Finite Element Analysis (FEA) for crack propagation prediction over time subject to environmental loads.
                    </p>
                </div>
            </header>
            
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <Simulator />
            </div>
        </div>
    );
};

export default Simulation;
