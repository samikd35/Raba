"use client";

import React, { useMemo } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { ExternalLink } from "lucide-react";

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

export const MarkdownRenderer = React.memo(({
    content,
    className = ""
}: MarkdownRendererProps) => {
    const processedContent = useMemo(() => content, [content]);

    return (
        <div className={`prose dark:prose-invert max-w-none text-gray-700 dark:text-gray-300 ${className}`}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={{
                    h1: ({ node, ...props }) => <h2 className="text-2xl font-bold mt-6 mb-4 text-gray-900 dark:text-white" {...props} />,
                    h2: ({ node, ...props }) => <h3 className="text-xl font-semibold mt-5 mb-3 text-gray-900 dark:text-white" {...props} />,
                    h3: ({ node, ...props }) => <h4 className="text-lg font-medium mt-4 mb-2 text-gray-900 dark:text-white" {...props} />,
                    p: ({ node, ...props }) => <p className="mb-4 leading-relaxed" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc list-outside pl-16 mb-4 space-y-2" style={{ listStyleType: 'disc' }} {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal list-outside pl-16 mb-4 space-y-2" style={{ listStyleType: 'decimal' }} {...props} />,
                    li: ({ node, ...props }) => <li className="mb-1" style={{ display: 'list-item' }} {...props} />,
                    a: ({ node, href, ...props }) => {
                        const isInternal = href?.startsWith('#') ?? false;
                        const isSourceHref = href?.startsWith('#source-') ?? false;
                        const hasDataSource = (node?.properties as Record<string, unknown>)?.['data-source'];
                        const isCitation = isSourceHref || hasDataSource;

                        const handleCitationClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
                            if (!isCitation) return;

                            e.preventDefault();

                            let targetId: string | null = null;
                            if (hasDataSource) {
                                const sourceNumber = (node?.properties as Record<string, unknown>)?.['data-source'];
                                targetId = `source-${sourceNumber}`;
                            } else if (isSourceHref && href) {
                                targetId = href.replace('#', '');
                            }

                            if (!targetId) return;

                            const targetElement = document.getElementById(targetId) as HTMLElement | null;

                            if (targetElement) {
                                const sourceUrl = targetElement.dataset?.sourceUrl;

                                if (sourceUrl && sourceUrl !== '#') {
                                    window.open(sourceUrl, '_blank', 'noopener,noreferrer');
                                    return;
                                }

                                targetElement.scrollIntoView({ behavior: 'smooth' });
                            }
                        };

                        return (
                            <a
                                href={href}
                                className={`${isCitation ? 'text-blue-600 dark:text-blue-400' : 'text-brand-500 dark:text-brand-400'} font-bold hover:underline flex items-center gap-1`}
                                {...(isInternal ? {} : { target: "_blank", rel: "noopener noreferrer" })}
                                onClick={isCitation ? handleCitationClick : undefined}
                                {...props}
                            >
                                {props.children}
                                {!isInternal && !isCitation && <ExternalLink className="h-3 w-3" />}
                            </a>
                        );
                    },
                    strong: ({ node, ...props }) => <strong className="font-semibold text-gray-900 dark:text-white" {...props} />,
                    code: ({ node, inline, ...props }: { node?: unknown; inline?: boolean; className?: string; children?: React.ReactNode }) =>
                        inline ? (
                            <code className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
                        ) : (
                            <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto my-4">
                                <code className="text-sm font-mono" {...props} />
                            </pre>
                        ),
                    blockquote: ({ node, ...props }) => (
                        <blockquote className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic my-4 text-gray-600 dark:text-gray-300" {...props} />
                    ),
                    table: ({ node, ...props }) => (
                        <div className="overflow-x-auto my-4">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700" {...props} />
                        </div>
                    ),
                    thead: ({ node, ...props }) => <thead className="bg-gray-50 dark:bg-gray-800" {...props} />,
                    tbody: ({ node, ...props }) => <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700" {...props} />,
                    th: ({ node, ...props }) => <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider" {...props} />,
                    td: ({ node, ...props }) => <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300" {...props} />,
                    hr: ({ node, ...props }) => <hr className="my-6 border-gray-200 dark:border-gray-700" {...props} />,
                }}
            >
                {processedContent}
            </ReactMarkdown>
        </div>
    );
});

MarkdownRenderer.displayName = 'MarkdownRenderer';
