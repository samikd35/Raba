import React from "react";
import { SharedReportView } from "@/components/problem-validator/validation-results";
import { fetchSharedReport } from "@/lib/api/reportService";
import { Metadata } from "next";

type Props = {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export async function generateMetadata(
    { params }: Props
): Promise<Metadata> {
    const { id } = await params;

    try {
        const data = await fetchSharedReport(id);

        if (data && data.success && data.data) {
            const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://yubanow.com';
            const report = data.data.content;
            const summary = report.executive_summary?.substring(0, 160) || "View this detailed market validation report on Yuba.";

            return {
                title: `${data.data.title} | Yuba Report`,
                description: summary,
                openGraph: {
                    title: data.data.title,
                    description: summary,
                    type: "article",
                    siteName: "Yuba Playbook",
                    url: `${baseUrl}/shared/${id}`,
                    images: [
                        {
                            url: `${baseUrl}/images/og-report-preview.png`, // Absolute URL
                            width: 1200,
                            height: 630,
                            alt: 'Yuba Report Preview',
                        }
                    ],
                },
                twitter: {
                    card: "summary_large_image",
                    title: data.data.title,
                    description: summary,
                    images: [`${baseUrl}/images/og-report-preview.png`],
                }
            };
        }
    } catch (error) {
        // Fallback for password protected or error (API returns 403 for protected reports)
        console.log("Metadata generation fallback:", error instanceof Error ? error.message : "Access restricted");
    }

    const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://yubanow.com';

    return {
        title: "Shared Market Validation Report | Yuba",
        description: "Access this shared market validation and problem discovery report on Yuba.",
        openGraph: {
            title: "Shared Market Validation Report",
            description: "Access this shared market validation and problem discovery report on Yuba.",
            type: "website",
            siteName: "Yuba Playbook",
            url: `${baseUrl}/shared/${id}`,
            images: [
                {
                    url: `${baseUrl}/images/og-report-default.png`,
                    width: 1200,
                    height: 630,
                    alt: 'Yuba Report',
                }
            ],
        },
        twitter: {
            card: "summary_large_image",
            title: "Shared Market Validation Report | Yuba",
            description: "Access this shared market validation and problem discovery report on Yuba.",
            images: [`${baseUrl}/images/og-report-default.png`],
        }
    };
}

export default async function SharedReportPage({
    params,
}: Props) {
    const resolvedParams = await params;
    return <SharedReportView shareToken={resolvedParams.id} />;
}