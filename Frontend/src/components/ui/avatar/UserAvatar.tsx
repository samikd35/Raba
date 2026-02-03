'use client';

import React, { useState } from 'react';

interface UserAvatarProps {
  src?: string | null;
  name: string;
  size?: 'xsmall' | 'small' | 'medium' | 'large' | 'xlarge' | 'xxlarge';
  className?: string;
}

const sizeClasses = {
  xsmall: 'h-6 w-6 text-xs',
  small: 'h-8 w-8 text-xs',
  medium: 'h-10 w-10 text-sm',
  large: 'h-12 w-12 text-base',
  xlarge: 'h-14 w-14 text-lg',
  xxlarge: 'h-16 w-16 text-xl',
};

const UserAvatar: React.FC<UserAvatarProps> = ({
  src,
  name,
  size = 'medium',
  className = '',
}) => {
  const [imageError, setImageError] = useState(false);
  const resolvedSizeClass = sizeClasses[size] ?? sizeClasses.medium;
  const textSizeClass = resolvedSizeClass.split(' ')[2] || 'text-sm';

  // Generate initials from name (first letter only for cofounder profiles)
  const initial = name?.trim()?.[0]?.toUpperCase() || 'U';

  // Generate a consistent color based on the name
  const getColorClass = (name: string) => {
    const colors = [
      'bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400',
      'bg-pink-100 dark:bg-pink-900/30 text-pink-600 dark:text-pink-400',
      'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400',
      'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
      'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
      'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
      'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
      'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
    ];

    if (!name || typeof name !== 'string') {
      return colors[0]; // Default color
    }

    const index = name
      .split('')
      .reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[index % colors.length];
  };

  const shouldShowImage = src && src.trim() !== '' && !imageError;

  return (
    <div
      className={`${resolvedSizeClass} ${className} rounded-full flex items-center justify-center overflow-hidden flex-shrink-0 ${
        shouldShowImage ? '' : getColorClass(name)
      }`}
    >
      {shouldShowImage ? (
        <img
          src={src}
          alt={name}
          className="w-full h-full object-cover"
          onError={() => setImageError(true)}
        />
      ) : (
        <span className={`${textSizeClass} font-semibold`}>
          {initial}
        </span>
      )}
    </div>
  );
};

export default UserAvatar;
