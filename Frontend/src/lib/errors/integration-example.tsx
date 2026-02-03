/**
 * Integration Examples for Error Handling and Loading States
 * This file demonstrates how to integrate the error handler and loading states
 * into existing Team Leader Workspace components
 * 
 * NOTE: This is a reference/example file only. It contains pseudo-code examples
 * and may have type errors. Use these patterns as a guide when implementing
 * error handling and loading states in actual components.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ErrorHandler } from '@/lib/errors/errorHandler';
import { useLoadingState, useAsyncOperation, useMultipleLoadingStates } from '@/hooks/useLoadingState';
import {
  LoadingSpinner,
  LoadingSpinnerWithText,
  ButtonLoading,
  TeamMetricsCardSkeleton,
  TeamMemberCardSkeleton,
  DashboardSkeleton,
  EmptyState,
  ProgressIndicator,
} from '@/components/ui/loading-states';
import { Button } from '@/components/ui/button';
import { toast } from "react-hot-toast";
import { teamService } from '@/lib/api/teamService';

/**
 * Example 1: Team Leader Dashboard with Loading States
 */
export function TeamLeaderDashboardExample() {
  const router = useRouter();
  const [team, setTeam] = useState(null);
  const [members, setMembers] = useState([]);
  const { loadingStates, startLoading, stopLoading, isAnyLoading } = 
    useMultipleLoadingStates(['team', 'members', 'refresh']);

  useEffect(() => {
    loadTeamData();
  }, []);

  const loadTeamData = async () => {
    startLoading('team');
    startLoading('members');

    try {
      // Fetch team data with retry logic
      const teamData = await ErrorHandler.retry(
        () => teamService.fetchTeams(orgId),
        2,
        'FetchTeams'
      );
      setTeam(teamData);
      stopLoading('team');

      // Fetch members
      const membersData = await teamService.getTeamMembers(teamData.id);
      setMembers(membersData);
      stopLoading('members');
    } catch (error) {
      ErrorHandler.handle(error, 'LoadTeamData', {
        onAuthRequired: () => router.push('/signin'),
      });
      stopLoading('team');
      stopLoading('members');
    }
  };

  const handleRefresh = async () => {
    startLoading('refresh');
    try {
      await loadTeamData();
      toast.success('Data refreshed');
    } catch (error) {
      ErrorHandler.handle(error, 'RefreshData');
    } finally {
      stopLoading('refresh');
    }
  };

  // Show full dashboard skeleton while loading
  if (loadingStates.team || loadingStates.members) {
    return <DashboardSkeleton />;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1>Team Dashboard</h1>
        <Button onClick={handleRefresh} disabled={loadingStates.refresh}>
          {loadingStates.refresh ? (
            <ButtonLoading text="Refreshing..." />
          ) : (
            'Refresh'
          )}
        </Button>
      </div>

      {/* Team metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        {/* Metric cards */}
      </div>

      {/* Members list */}
      <div className="mt-6">
        <h2>Team Members</h2>
        {members.length === 0 ? (
          <EmptyState
            title="No team members yet"
            description="Invite members to get started"
            action={<Button>Invite Members</Button>}
          />
        ) : (
          <div className="space-y-3">
            {members.map(member => (
              <div key={member.id}>{/* Member card */}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Example 2: Team Creation Form with Error Handling
 */
export function TeamCreationFormExample() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    industry: '',
  });
  const { isLoading, startLoading, stopLoading, error, setLoadingError } = useLoadingState();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    startLoading();

    try {
      const result = await teamService.createTeam(orgId, formData);
      toast.success('Team created successfully');
      router.push('/admin/team-leader-dashboard');
    } catch (error: any) {
      // Handle specific error types
      const errorInfo = ErrorHandler.handle(error, 'TeamCreation', {
        silent: true, // Don't show toast, we'll show inline error
        onAuthRequired: () => router.push('/signin'),
      });
      
      setLoadingError(errorInfo.message);
    } finally {
      stopLoading();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label>Team Name</label>
        <input
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          disabled={isLoading}
          className="w-full"
        />
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      <Button type="submit" disabled={isLoading}>
        {isLoading ? <ButtonLoading text="Creating team..." /> : 'Create Team'}
      </Button>
    </form>
  );
}

/**
 * Example 3: Member Invitation with Multiple Loading States
 */
export function MemberInvitationExample() {
  const [emails, setEmails] = useState('');
  const [invitationHistory, setInvitationHistory] = useState([]);
  const { loadingStates, startLoading, stopLoading } = 
    useMultipleLoadingStates(['invite', 'history']);

  useEffect(() => {
    loadInvitationHistory();
  }, []);

  const loadInvitationHistory = async () => {
    startLoading('history');
    try {
      const history = await teamService.getInvitationHistory(teamId);
      setInvitationHistory(history);
    } catch (error) {
      ErrorHandler.handle(error, 'LoadInvitationHistory');
    } finally {
      stopLoading('history');
    }
  };

  const handleSendInvites = async () => {
    startLoading('invite');
    try {
      const emailList = emails.split(',').map(e => e.trim());
      await teamService.inviteTeamMembers(teamId, { 
        emails: emailList, 
        is_admin: false 
      });
      toast.success(`Sent ${emailList.length} invitation(s)`);
      setEmails('');
      await loadInvitationHistory();
    } catch (error) {
      ErrorHandler.handle(error, 'SendInvitations');
    } finally {
      stopLoading('invite');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2>Invite Team Members</h2>
        <input
          value={emails}
          onChange={(e) => setEmails(e.target.value)}
          placeholder="email1@example.com, email2@example.com"
          disabled={loadingStates.invite}
        />
        <Button 
          onClick={handleSendInvites} 
          disabled={loadingStates.invite || !emails}
        >
          {loadingStates.invite ? (
            <ButtonLoading text="Sending invites..." />
          ) : (
            'Send Invites'
          )}
        </Button>
      </div>

      <div>
        <h3>Invitation History</h3>
        {loadingStates.history ? (
          <div className="space-y-3">
            <TeamMemberCardSkeleton />
            <TeamMemberCardSkeleton />
            <TeamMemberCardSkeleton />
          </div>
        ) : invitationHistory.length === 0 ? (
          <EmptyState
            title="No invitations sent yet"
            description="Invite members to see history"
          />
        ) : (
          <div className="space-y-2">
            {invitationHistory.map(invite => (
              <div key={invite.id}>{/* Invitation card */}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Example 4: Using useAsyncOperation Hook
 */
export function TeamDetailsExample({ teamId }: { teamId: string }) {
  const { execute, isLoading, error, data } = useAsyncOperation(
    async (id: string) => {
      return await teamService.fetchTeam(id);
    },
    {
      context: 'FetchTeamDetails',
      onSuccess: () => {
        toast.success('Team details loaded');
      },
      onError: (err) => {
        console.error('Failed to load team:', err);
      },
    }
  );

  useEffect(() => {
    execute(teamId);
  }, [teamId]);

  if (isLoading) {
    return <TeamMetricsCardSkeleton />;
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded">
        <p className="text-red-700">{error}</p>
        <Button onClick={() => execute(teamId)} className="mt-2">
          Retry
        </Button>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div>
      <h2>{data.name}</h2>
      <p>{data.description}</p>
    </div>
  );
}

/**
 * Example 5: Multi-Step Operation with Progress Indicator
 */
export function MultiStepOnboardingExample() {
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const steps = ['Team Details', 'Invite Members', 'Allocate Credits', 'Review'];

  const handleNextStep = async () => {
    setIsLoading(true);
    try {
      // Simulate async operation
      await new Promise(resolve => setTimeout(resolve, 1000));
      setCurrentStep(prev => prev + 1);
    } catch (error) {
      ErrorHandler.handle(error, 'OnboardingStep');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <ProgressIndicator
        currentStep={currentStep}
        totalSteps={steps.length}
        stepLabels={steps}
      />

      <div className="p-6 border rounded">
        {isLoading ? (
          <LoadingSpinnerWithText text={`Processing ${steps[currentStep]}...`} />
        ) : (
          <div>
            <h3>{steps[currentStep]}</h3>
            {/* Step content */}
          </div>
        )}
      </div>

      <Button onClick={handleNextStep} disabled={isLoading}>
        {isLoading ? <ButtonLoading text="Processing..." /> : 'Next Step'}
      </Button>
    </div>
  );
}

/**
 * Example 6: Member Action with Inline Loading
 */
export function MemberActionExample({ member }: { member: any }) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleSuspend = async () => {
    setActionLoading('suspend');
    try {
      await teamService.suspendMember(member.id);
      toast.success('Member suspended');
    } catch (error) {
      ErrorHandler.handle(error, 'SuspendMember');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRemove = async () => {
    setActionLoading('remove');
    try {
      await teamService.removeMember(member.id);
      toast.success('Member removed');
    } catch (error) {
      ErrorHandler.handle(error, 'RemoveMember');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="flex gap-2">
      <Button
        onClick={handleSuspend}
        disabled={actionLoading !== null}
        variant="outline"
      >
        {actionLoading === 'suspend' ? (
          <ButtonLoading text="Suspending..." />
        ) : (
          'Suspend'
        )}
      </Button>
      <Button
        onClick={handleRemove}
        disabled={actionLoading !== null}
        variant="destructive"
      >
        {actionLoading === 'remove' ? (
          <ButtonLoading text="Removing..." />
        ) : (
          'Remove'
        )}
      </Button>
    </div>
  );
}
