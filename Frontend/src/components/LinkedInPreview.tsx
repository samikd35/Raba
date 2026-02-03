import React from 'react';
import Image from 'next/image';

interface LinkedInPreviewProps {
  title?: string;
  description?: string;
  imageUrl?: string;
  url?: string;
}

const LinkedInPreview: React.FC<LinkedInPreviewProps> = ({
  title = "Yuba - A Sounding Board for African Entrepreneurs",
  description = "Get contextual and actionable market insights to validate your business ideas. Join early-stage founders building the next generation of African startups.",
  imageUrl = "/images/logo/yuba-logo-colored.png",
  url = "https://yuba.app"
}) => {
  return (
    <div className="max-w-[552px] w-full mx-auto">
      {/* LinkedIn Post Preview Card */}
      <div className="bg-white rounded-lg border border-gray-300 overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200">
        {/* Image Section */}
        <div className="relative w-full aspect-[1.91/1] bg-gradient-to-br from-brand-500 to-[#128AA3] flex items-center justify-center">
          <div className="relative w-48 h-48">
            <Image
              src={imageUrl}
              alt="Yuba Logo"
              fill
              className="object-contain"
              priority
            />
          </div>
          {/* Overlay gradient for better logo visibility */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/10 to-transparent" />
        </div>

        {/* Content Section */}
        <div className="p-3 bg-gray-50">
          {/* Title */}
          <h3 className="text-sm font-semibold text-gray-900 mb-1 line-clamp-2 hover:underline cursor-pointer">
            {title}
          </h3>
          
          {/* Description */}
          <p className="text-xs text-gray-600 mb-2 line-clamp-2">
            {description}
          </p>
          
          {/* URL */}
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
            </svg>
            <span className="truncate">{url}</span>
          </div>
        </div>
      </div>

      {/* Preview Label */}
      <div className="mt-4 text-center">
        <p className="text-xs text-gray-500 font-medium">LinkedIn Share Preview</p>
      </div>
    </div>
  );
};

export default LinkedInPreview;
