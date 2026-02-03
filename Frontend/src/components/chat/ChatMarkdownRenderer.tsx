"use client";

import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChatMarkdownRendererProps } from './types';

// Optimized Chat Markdown Renderer Component
const ChatMarkdownRenderer = React.memo(({ 
  content 
}: ChatMarkdownRendererProps) => {
  // Memoize the content processing to prevent unnecessary re-renders
  const processedContent = useMemo(() => content, [content]);

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:mt-2 prose-headings:mb-2 prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5">
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({node, ...props}) => <h3 className="text-base font-semibold mt-3 mb-2 text-gray-900 dark:text-white" {...props} />,
          h2: ({node, ...props}) => <h4 className="text-sm font-medium mt-2 mb-1 text-gray-900 dark:text-white" {...props} />,
          h3: ({node, ...props}) => <h5 className="text-sm font-medium mt-2 mb-1 text-gray-900 dark:text-white" {...props} />,
          p: ({node, ...props}) => <p className="my-1 text-sm leading-relaxed" {...props} />,
          ul: ({node, ...props}) => <ul className="list-disc list-outside pl-4 my-1 space-y-0.5" {...props} />,
          ol: ({node, ...props}) => <ol className="list-decimal list-outside pl-4 my-1 space-y-0.5" {...props} />,
          li: ({node, ...props}) => <li className="my-0.5 text-sm" {...props} />,
          a: ({node, href, ...props}) => (
            <a 
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-600 underline text-sm" 
              {...props}
            />
          ),
          strong: ({node, ...props}) => <strong className="font-semibold text-gray-900 dark:text-white" {...props} />,
          em: ({node, ...props}) => <em className="italic" {...props} />,
          code: ({node, inline, ...props}) => 
            inline ? (
              <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded text-xs font-mono" {...props} />
            ) : (
              <pre className="bg-gray-100 dark:bg-gray-700 p-2 rounded my-2 overflow-x-auto">
                <code className="text-xs font-mono" {...props} />
              </pre>
            ),
          blockquote: ({node, ...props}) => (
            <blockquote className="border-l-3 border-gray-300 dark:border-gray-600 pl-3 italic my-2 text-sm text-gray-600 dark:text-gray-300" {...props} />
          ),
          table: ({node, ...props}) => (
            <div className="overflow-x-auto my-2">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm" {...props} />
            </div>
          ),
          thead: ({node, ...props}) => <thead className="bg-gray-50 dark:bg-gray-800" {...props} />,
          tbody: ({node, ...props}) => <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700" {...props} />,
          th: ({node, ...props}) => <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider" {...props} />,
          td: ({node, ...props}) => <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300" {...props} />,
          hr: ({node, ...props}) => <hr className="my-2 border-gray-200 dark:border-gray-700" {...props} />,
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
});

ChatMarkdownRenderer.displayName = 'ChatMarkdownRenderer';

export default ChatMarkdownRenderer;
