"use client";
import { useAuth } from "@/hooks/useAuth";

export default function UserMetaCard() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="p-5 border border-gray-200 rounded-2xl dark:border-gray-800 lg:p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-col items-center w-full gap-6 xl:flex-row">
            <div className="w-20 h-20 bg-gray-200 rounded-full animate-pulse"></div>
            <div className="order-3 xl:order-2 space-y-2">
              <div className="h-6 bg-gray-200 rounded animate-pulse w-32"></div>
              <div className="h-4 bg-gray-200 rounded animate-pulse w-48"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getUserRole = () => {
    // You can extend this based on your user data structure
    return user?.roles[0] || 'Team Member';
  };

  const formatJoinDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long' 
    });
  };

  return (
    <div className="p-5 border border-gray-200 rounded-2xl dark:border-gray-800 lg:p-6">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-col items-center w-full gap-6 xl:flex-row">
          {/* User Avatar */}
          <div className="relative">
        
              <div className="flex items-center justify-center w-20 h-20 text-2xl font-semibold text-white bg-[#128AA3] rounded-full border-2 border-gray-200 dark:border-gray-700">
                {user?.full_name ? getInitials(user.full_name) : user?.email ? getInitials(user.email) : 'U'}
              </div>
            
            {/* Online Status Indicator */}
            <div className="absolute bottom-1 right-1 w-4 h-4 bg-green-500 border-2 border-white dark:border-gray-800 rounded-full"></div>
          </div>

          {/* User Information */}
          <div className="order-3 xl:order-2 text-center xl:text-left">
            <h4 className="mb-2 text-lg font-semibold text-gray-800 dark:text-white/90">
              {user?.full_name || 'User Name'}
            </h4>
            <div className="flex flex-col items-center gap-1 text-center xl:flex-row xl:gap-3 xl:text-left">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {getUserRole()}
              </p>
              <div className="hidden h-3.5 w-px bg-gray-300 dark:bg-gray-700 xl:block"></div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {user?.email}
              </p>
            </div>
            {user?.created_at && (
              <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                Member since {formatJoinDate(user.created_at)}
              </p>
            )}
          </div>
        </div>

       
      </div>
    </div>
  );
}
