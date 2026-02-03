import React from "react";
import { Coins } from "lucide-react";

interface CreditCostBadgeProps {
  cost: number;
}

const CreditCostBadge: React.FC<CreditCostBadgeProps> = ({ cost }) => {
  return (
    <span 
      className="relative inline-flex bg-amber-100 items-center gap-1 px-2 py-0.5 rounded-full border border-amber-200 dark:bg-amber-800/10 dark:border-amber-700 group cursor-default"
      aria-label="Credit Cost"
    >
      <span className="text-sm font-medium text-amber-800 dark:text-amber-300">
        {cost}
      </span>
      <Coins className="w-3.5 h-3.5 text-amber-500 dark:text-amber-500 flex-shrink-0" />
      
      {/* Custom Tooltip */}
      <span 
        role="tooltip"
        className="
          pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-2
          px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap
          bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900
          shadow-lg shadow-black/10 dark:shadow-black/20
          opacity-0 scale-95 group-hover:opacity-100 group-hover:scale-100
          transition-all duration-150 ease-out
          z-50
        "
      >
        Credit Cost
        {/* Tooltip Arrow */}
        <span 
          className="
            absolute left-1/2 -translate-x-1/2 top-full
            border-4 border-transparent border-t-gray-900 dark:border-t-gray-100
          "
        />
      </span>
    </span>
  );
};

export default CreditCostBadge;
