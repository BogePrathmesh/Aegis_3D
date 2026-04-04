import React from 'react';
import BudgetOptimizer from '../components/BudgetOptimizer';

const Budget = () => {
    return (
        <div className="max-w-[1440px] mx-auto px-8 py-12 animate-fade-in">
             <header className="mb-12 border-b border-slate-200 pb-8 flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-headline text-on-surface mb-2">Budget Optimizer</h1>
                    <p className="text-on-surface-variant max-w-2xl text-lg">
                        AI-optimized maintenance planning and capital allocation across infrastructure assets to minimize risk.
                    </p>
                </div>
            </header>
            
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <BudgetOptimizer />
            </div>
        </div>
    );
};

export default Budget;
