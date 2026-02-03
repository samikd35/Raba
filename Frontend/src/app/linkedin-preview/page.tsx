"use client";

import React from 'react';
import LinkedInPreview from '@/components/LinkedInPreview';
import LinkedInMetaTags from '@/components/LinkedInMetaTags';

export default function LinkedInPreviewPage() {
  return (
    <>
      <LinkedInMetaTags
        title="Yuba - A Sounding Board for African Entrepreneurs"
        description="Get contextual and actionable market insights to validate your business ideas. Join early-stage founders building the next generation of African startups."
        imageUrl="https://yuba.app/images/og-image.png"
        url="https://yuba.app"
      />
      
      <div className="min-h-screen bg-gray-100 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              LinkedIn Share Preview
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              This is how your Yuba link will appear when shared on LinkedIn
            </p>
          </div>

          {/* Preview Card */}
          <div className="mb-12">
            <LinkedInPreview />
          </div>

          {/* Instructions */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              How to use:
            </h2>
            <ul className="space-y-3 text-gray-700">
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500 text-white flex items-center justify-center text-sm font-semibold">1</span>
                <span>Copy your Yuba page URL (e.g., https://yuba.app)</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500 text-white flex items-center justify-center text-sm font-semibold">2</span>
                <span>Paste it into a LinkedIn post</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500 text-white flex items-center justify-center text-sm font-semibold">3</span>
                <span>LinkedIn will automatically generate a preview card like the one above</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500 text-white flex items-center justify-center text-sm font-semibold">4</span>
                <span>Add your message and share with your network!</span>
              </li>
            </ul>
          </div>

          {/* Meta Tags Info */}
          <div className="mt-8 bg-blue-50 rounded-lg border border-blue-200 p-6">
            <h3 className="text-lg font-semibold text-blue-900 mb-3">
              📋 Meta Tags Included
            </h3>
            <p className="text-sm text-blue-800 mb-3">
              The following Open Graph meta tags are automatically added to ensure proper LinkedIn sharing:
            </p>
            <ul className="text-sm text-blue-700 space-y-1 font-mono">
              <li>• og:title</li>
              <li>• og:description</li>
              <li>• og:image (1200x630px)</li>
              <li>• og:url</li>
              <li>• og:type</li>
              <li>• twitter:card</li>
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}
