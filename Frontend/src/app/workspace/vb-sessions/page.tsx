import VBSessionsDashboard from '@/components/venture-builder/sessions/VBSessionsDashboard';

export const metadata = {
  title: 'My Sessions | Venture Builder',
  description: 'Manage your coaching sessions',
};

export default function VBSessionsPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <VBSessionsDashboard />
      </div>
    </div>
  );
}
