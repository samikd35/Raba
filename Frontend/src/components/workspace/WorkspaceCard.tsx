"use client";

import { User, CheckCircle2, ArrowRight, Crown, Building, Users, Shield, UserCircle } from 'lucide-react';

interface Workspace {
  id: string;
  name: string;
  type: 'organization' | 'team' | 'personal' | 'individual_member';
  role: string;
  member_count: number;
  total_credits?: number;
  credits_remaining?: number;
  organization_name?: string;
}

interface WorkspaceCardProps {
  workspace: Workspace;
  isSelected: boolean;
  onSelect: () => void;
  formatWorkspaceName: (name: string, type: string) => string;
}

export default function WorkspaceCard({ workspace, isSelected, onSelect, formatWorkspaceName }: WorkspaceCardProps) {
  const getWorkspaceIcon = (type: string, role: string) => {
    if (role === 'owner' || role === 'admin') return <Crown className="w-5 h-5" />;
    if (type === 'individual_member') return <UserCircle className="w-5 h-5" />;
    return type === 'organization' ? <Building className="w-5 h-5" /> : type === 'team' ? <Users className="w-5 h-5" /> : <Shield className="w-5 h-5" />;
  };

  const iconColorClass = workspace.type === 'personal' ? 'text-blue-600 dark:text-blue-400'
    : workspace.type === 'individual_member' ? 'text-purple-600 dark:text-purple-400'
    : workspace.type === 'team' ? 'text-green-600 dark:text-green-400'
    : 'text-orange-600 dark:text-orange-400';

  const typeBadgeClass = workspace.type === 'personal' ? 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700'
    : workspace.type === 'individual_member' ? 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-700'
    : workspace.type === 'team' ? 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700'
    : 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-700';

  const total = workspace.total_credits || 0;
  const remaining = workspace.credits_remaining || 0;
  const percentage = total > 0 ? Math.round((remaining / total) * 100) : 0;
  const progressColor = percentage > 50 ? 'bg-green-500 dark:bg-green-400' : percentage > 20 ? 'bg-yellow-500 dark:bg-yellow-400' : 'bg-red-500 dark:bg-red-400';
  const textColor = percentage > 50 ? 'text-green-600 dark:text-green-400' : percentage > 20 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400';

  const description = workspace.type === 'personal' ? 'Private workspace, self-purchased credits'
    : workspace.type === 'individual_member' ? `Solo workspace with ${workspace.organization_name} credits`
    : workspace.type === 'team' ? `Collaborate with ${workspace.name} Team, part of ${workspace.organization_name} program`
    : 'Manage teams, credits & portfolio';

  return (
    <div
      className={`group relative bg-white dark:bg-brand-800 rounded-xl border p-4 cursor-pointer transition-all duration-200 hover:shadow-md ${
        isSelected
          ? 'border-gray-400 bg-gray-50 dark:bg-gray-700 dark:border-gray-500 shadow-sm'
          : 'border-gray-200 hover:border-gray-300 dark:border-gray-600 dark:hover:border-gray-500'
      }`}
      onClick={onSelect}
    >
      {/* Mobile Layout (<568px) - Full width with proper alignment */}
      <div className="min-[568px]:hidden flex flex-col space-y-2.5 w-full">
        {/* Row 1: Icon + Name (left) | Action (right) */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <div className={`flex-shrink-0 ${iconColorClass}`}>
              {getWorkspaceIcon(workspace.type, workspace.role)}
            </div>
            <h3 className="text-base font-medium text-brand-500 dark:text-gray-100 break-words leading-tight">
              {formatWorkspaceName(workspace.name, workspace.type)}
            </h3>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {isSelected ? <CheckCircle2 className="w-5 h-5 text-brand-500 dark:text-brand-400" /> : <div className="w-5 h-5 border-2 rounded-full border-gray-300 dark:border-gray-600 group-hover:border-gray-400 dark:group-hover:border-gray-500" />}
            <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 group-hover:translate-x-0.5 transition-all duration-200" />
          </div>
        </div>
        {/* Row 2: Badges + Members (flex-wrap, left-aligned) */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${typeBadgeClass}`}>
            {workspace.type === 'personal' ? 'Personal' : workspace.type === 'individual_member' ? 'Individual' : workspace.type}
          </span>
          {workspace.type !== 'personal' && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300">
              {workspace.type === 'team' && workspace.role === 'owner' ? 'admin' : workspace.role}
            </span>
          )}
          {(workspace.type === 'organization' || workspace.type === 'team') && (
            <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <User className="w-3 h-3" />{workspace.member_count}
            </span>
          )}
        </div>
        {/* Row 3: Description (full width) */}
        <div className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{description}</div>
        {/* Row 4: Credits progress (full width) */}
        <div className="w-full">
          <div className="flex items-center justify-between mb-1">
            <span className={`text-[10px] font-medium ${textColor}`}>Credits</span>
            <span className={`text-[10px] font-medium ${textColor}`}>{remaining.toLocaleString()}/{total.toLocaleString()}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div className={`h-full ${progressColor} rounded-full transition-all duration-300`} style={{ width: `${Math.min(percentage, 100)}%` }} />
          </div>
          <div className="text-[9px] text-gray-400 dark:text-gray-500 text-right mt-0.5">{percentage}% remaining</div>
        </div>
      </div>

      {/* Tablet Layout (568px - 768px) - Compact horizontal */}
      <div className="hidden min-[568px]:flex md:hidden items-center gap-4 min-h-[60px]">
        <div className="flex items-center gap-3 min-w-0 flex-shrink-0" style={{ maxWidth: '200px' }}>
          <div className={`flex-shrink-0 ${iconColorClass}`}>
            {getWorkspaceIcon(workspace.type, workspace.role)}
          </div>
          <div className="min-w-0">
            <h3 className="text-base font-medium text-brand-500 dark:text-gray-100 truncate leading-tight">
              {formatWorkspaceName(workspace.name, workspace.type)}
            </h3>
            <div className="flex flex-wrap items-center gap-1 mt-1">
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-medium border ${typeBadgeClass}`}>
                {workspace.type === 'personal' ? 'Personal' : workspace.type === 'individual_member' ? 'Individual' : workspace.type}
              </span>
              {workspace.type !== 'personal' && (
                <span className="inline-flex items-center px-1 py-0.5 rounded text-[10px] font-medium text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300">
                  {workspace.type === 'team' && workspace.role === 'owner' ? 'admin' : workspace.role}
                </span>
              )}
              {(workspace.type === 'organization' || workspace.type === 'team') && (
                <span className="flex items-center gap-0.5 text-[10px] text-gray-500 dark:text-gray-400">
                  <User className="w-2.5 h-2.5" />{workspace.member_count}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex-1 text-xs text-gray-500 dark:text-gray-400 leading-relaxed text-center px-2">{description}</div>
        <div className="flex-shrink-0 w-[120px]">
          <div className="flex items-center justify-between mb-1">
            <span className={`text-[9px] font-medium ${textColor}`}>Credits</span>
            <span className={`text-[9px] font-medium ${textColor}`}>{remaining.toLocaleString()}/{total.toLocaleString()}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div className={`h-full ${progressColor} rounded-full transition-all duration-300`} style={{ width: `${Math.min(percentage, 100)}%` }} />
          </div>
          <div className="text-[8px] text-gray-400 dark:text-gray-500 text-right mt-0.5">{percentage}% remaining</div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {isSelected ? <CheckCircle2 className="w-5 h-5 text-brand-500 dark:text-brand-400" /> : <div className="w-5 h-5 border-2 rounded-full border-gray-300 dark:border-gray-600 group-hover:border-gray-400 dark:group-hover:border-gray-500" />}
          <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 group-hover:translate-x-0.5 transition-all duration-200" />
        </div>
      </div>

      {/* Desktop Layout (>=768px) - Full grid with centered description */}
      <div className="hidden md:grid md:grid-cols-[220px_1fr_140px_auto] md:gap-4 md:items-center md:min-h-[60px]">
        <div className="flex items-center gap-3">
          <div className={`flex-shrink-0 ${iconColorClass}`}>
            {getWorkspaceIcon(workspace.type, workspace.role)}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-base font-medium text-brand-500 dark:text-gray-100 truncate leading-tight">
              {formatWorkspaceName(workspace.name, workspace.type)}
            </h3>
            <div className="flex flex-wrap items-center gap-1.5 mt-1">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${typeBadgeClass}`}>
                {workspace.type === 'personal' ? 'Personal' : workspace.type === 'individual_member' ? 'Individual' : workspace.type}
              </span>
              {workspace.type !== 'personal' && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300">
                  {workspace.type === 'team' && workspace.role === 'owner' ? 'admin' : workspace.role}
                </span>
              )}
              {(workspace.type === 'organization' || workspace.type === 'team') && (
                <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                  <User className="w-3 h-3" />{workspace.member_count}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-center h-full">
          <span className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed text-center">{description}</span>
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className={`text-[10px] font-medium ${textColor}`}>Credits</span>
            <span className={`text-[10px] font-medium ${textColor}`}>{remaining.toLocaleString()}/{total.toLocaleString()}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div className={`h-full ${progressColor} rounded-full transition-all duration-300`} style={{ width: `${Math.min(percentage, 100)}%` }} />
          </div>
          <div className="text-[9px] text-gray-400 dark:text-gray-500 text-right mt-0.5">{percentage}% remaining</div>
        </div>
        <div className="flex items-center gap-2">
          {isSelected ? <CheckCircle2 className="w-5 h-5 text-brand-500 dark:text-brand-400" /> : <div className="w-5 h-5 border-2 rounded-full border-gray-300 dark:border-gray-600 group-hover:border-gray-400 dark:group-hover:border-gray-500" />}
          <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 group-hover:translate-x-0.5 transition-all duration-200" />
        </div>
      </div>
    </div>
  );
}
