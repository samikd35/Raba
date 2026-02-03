/**
 * OrganizationMetricsCard Usage Examples
 * 
 * This file demonstrates how to use the OrganizationMetricsCard component
 * in different scenarios.
 */

import { OrganizationMetricsCard } from './OrganizationMetricsCard';
import { OrganizationMetrics } from '@/stores/organizationStore';

// Example 1: Basic usage with metrics data
export function BasicExample() {
  const metrics: OrganizationMetrics = {
    invitations: {
      sent: 50,
      accepted: 35,
    },
    membership: {
      total: 35,
      team_members: 25,
      individual_members: 10,
    },
    credits: {
      total: 10000,
      used: 3500,
      remaining: 6500,
      monthly_limit: 10000,
    },
  };

  return <OrganizationMetricsCard metrics={metrics} />;
}

// Example 2: Loading state
export function LoadingExample() {
  return <OrganizationMetricsCard metrics={null} isLoading={true} />;
}

// Example 3: High usage (red indicator)
export function HighUsageExample() {
  const metrics: OrganizationMetrics = {
    invitations: {
      sent: 100,
      accepted: 85,
    },
    membership: {
      total: 85,
      team_members: 60,
      individual_members: 25,
    },
    credits: {
      total: 10000,
      used: 8500, // 85% usage - should show red
      remaining: 1500,
      monthly_limit: 10000,
    },
  };

  return <OrganizationMetricsCard metrics={metrics} />;
}

// Example 4: Moderate usage (yellow indicator)
export function ModerateUsageExample() {
  const metrics: OrganizationMetrics = {
    invitations: {
      sent: 75,
      accepted: 60,
    },
    membership: {
      total: 60,
      team_members: 45,
      individual_members: 15,
    },
    credits: {
      total: 10000,
      used: 6500, // 65% usage - should show yellow
      remaining: 3500,
      monthly_limit: 10000,
    },
  };

  return <OrganizationMetricsCard metrics={metrics} />;
}

// Example 5: Low usage (green indicator)
export function LowUsageExample() {
  const metrics: OrganizationMetrics = {
    invitations: {
      sent: 30,
      accepted: 25,
    },
    membership: {
      total: 25,
      team_members: 18,
      individual_members: 7,
    },
    credits: {
      total: 10000,
      used: 2000, // 20% usage - should show green
      remaining: 8000,
      monthly_limit: 10000,
    },
  };

  return <OrganizationMetricsCard metrics={metrics} />;
}

// Example 6: Integration with organization store
export function StoreIntegrationExample() {
  // In a real component, you would use:
  // const metrics = useOrganizationMetrics();
  // const isLoading = useOrganizationLoading();
  
  // return <OrganizationMetricsCard metrics={metrics} isLoading={isLoading} />;
  
  return null; // Placeholder for documentation
}

// Example 7: Usage in organization details page
export function OrganizationDetailsPageExample() {
  /*
  import { OrganizationMetricsCard } from '@/components/admin/OrganizationMetricsCard';
  import { useOrganizationMetrics, useOrganizationLoading } from '@/stores/organizationStore';
  
  export default function OrganizationDetailPage() {
    const metrics = useOrganizationMetrics();
    const isLoading = useOrganizationLoading();
    
    return (
      <div className="space-y-6">
        <h1>Organization Dashboard</h1>
        
        <OrganizationMetricsCard 
          metrics={metrics} 
          isLoading={isLoading}
          className="max-w-4xl"
        />
        
        // ... other components
      </div>
    );
  }
  */
  
  return null; // Placeholder for documentation
}

// Example 8: Custom styling
export function CustomStyledExample() {
  const metrics: OrganizationMetrics = {
    invitations: {
      sent: 50,
      accepted: 35,
    },
    membership: {
      total: 35,
      team_members: 25,
      individual_members: 10,
    },
    credits: {
      total: 10000,
      used: 3500,
      remaining: 6500,
      monthly_limit: 10000,
    },
  };

  return (
    <OrganizationMetricsCard 
      metrics={metrics} 
      className="shadow-lg border-2 border-brand-500"
    />
  );
}
