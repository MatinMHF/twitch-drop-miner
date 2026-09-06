import React, { useState } from 'react';
import { DropCampaignList } from './DropCampaignList';
import { DropHistoryList } from './DropHistoryList';
import { Gift, History } from 'lucide-react';

export const InventoryTab: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'campaigns' | 'history'>('campaigns');

  return (
    <div className="space-y-6">
      {/* Sub navigation buttons */}
      <div className="flex items-center space-x-2 bg-slate-900/60 p-1.5 rounded-2xl border border-slate-800 w-fit">
        <button
          onClick={() => setActiveSubTab('campaigns')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'campaigns'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Gift className="w-4 h-4" />
          <span>Active & Upcoming Campaigns</span>
        </button>

        <button
          onClick={() => setActiveSubTab('history')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'history'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Claimed Rewards History</span>
        </button>
      </div>

      {activeSubTab === 'campaigns' ? (
        <DropCampaignList />
      ) : (
        <DropHistoryList />
      )}
    </div>
  );
};
