import { ReportResponse } from "@/types/validation";

// Enhanced Validation Results Data
export interface EnhancedValidationResultsData {
    report: ReportResponse;
    sessionId: string;
    generatedAt?: string;
    problemStatement?: string;
    reportId?: string;
}

// PDF Export State
export interface PDFExportState {
    isExporting: boolean;
    progress: number;
    error: string | null;
}

// Source Item for References
export interface SourceItem {
    number?: number;
    source_url: string;
    source_title?: string;
    credibility_score?: number;
    publication_date?: string;
}

// Chat Message
export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

// Chat Response from API
export interface ChatResponse {
    id: string;
    content: string;
    success: boolean;
    error?: string;
    chat_session_id: string;
    metadata?: Record<string, unknown>;
}

// Share Settings
export interface ShareSettings {
    isPublic: boolean;
    password: string;
    allowedEmails: string;
    maxViews: number | null;
    expiresInDays: number;
    shareMessage: string;
}

// Share Response from API
export interface ShareResponse {
    success: boolean;
    message: string;
    share: {
        id: string;
        share_token: string;
        share_url: string;
        session_id: string;
        report_id: string;
        report_title: string;
        access_type: string;
        is_public: boolean;
        has_password: boolean;
        allowed_emails: string[];
        max_views: number | null;
        view_count: number;
        expires_at: string;
        is_active: boolean;
        is_expired: boolean;
        is_view_limit_reached: boolean;
        share_message: string;
        created_at: string;
        last_accessed_at: string | null;
        revoked_at: string | null;
    };
}

// Report Content Interface (used for accessing report.report fields)
export interface ReportContent {
    title?: string;
    executive_summary?: string;
    industry_analysis?: string;
    challenges_analysis?: string;
    recommendations?: string;
    sources?: SourceItem[];
    tenant_id?: string;
}

// Main ValidationResultsView Props
export interface ValidationResultsViewProps {
    params: Promise<{ id: string }>;
    workspaceType: 'workspace' | 'team-workspace';
    basePath: string;
    ActionableInsightsComponent: React.ComponentType<{ reportId?: string }>;
}
