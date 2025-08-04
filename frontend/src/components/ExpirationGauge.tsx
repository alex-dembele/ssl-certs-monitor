// Fichier: frontend/src/components/ExpirationGauge.tsx
import React from 'react';

const ExpirationGauge = ({ daysLeft, maxDays = 365 }: { daysLeft: number, maxDays?: number }) => {
    const percentage = Math.max(0, Math.min(100, (daysLeft / maxDays) * 100));
    
    let colorClass = 'text-green-400';
    if (percentage < 10) colorClass = 'text-red-400';
    else if (percentage < 30) colorClass = 'text-yellow-400';

    const circumference = 2 * Math.PI * 18; // 2 * pi * radius
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
        <div className="relative w-12 h-12">
            <svg className="w-full h-full" viewBox="0 0 40 40">
                <circle
                    className="text-slate-700"
                    strokeWidth="4"
                    stroke="currentColor"
                    fill="transparent"
                    r="18"
                    cx="20"
                    cy="20"
                />
                <circle
                    className={`${colorClass} transition-all duration-500`}
                    strokeWidth="4"
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r="18"
                    cx="20"
                    cy="20"
                    transform="rotate(-90 20 20)"
                />
            </svg>
            <div className={`absolute inset-0 flex items-center justify-center font-bold text-sm ${colorClass}`}>
                {daysLeft < 0 ? '!' : daysLeft}
            </div>
        </div>
    );
};

export default ExpirationGauge;