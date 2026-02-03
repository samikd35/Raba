import UserSessionsDashboard from '@/components/venture-builder/sessions/UserSessionsDashboard';

export const metadata = {
  title: 'My Sessions | Workspace',
  description: 'View your booked coaching sessions',
};

export default function MySessionsPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <UserSessionsDashboard />
      </div>
    </div>
  );
}
