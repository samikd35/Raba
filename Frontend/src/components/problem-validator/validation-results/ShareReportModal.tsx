"use client";

import React, { useState, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter
} from "@/components/ui/dialog";
import {
    Share2,
    Copy,
    Check,
    Lock,
    Globe,
    Calendar,
    Eye,
    EyeOff,
    Link2,
    Users,
    RefreshCw,
    ChevronDown
} from "lucide-react";
import toast from "react-hot-toast";
import { ShareSettings, ShareResponse } from "./types";

interface ShareReportModalProps {
    isOpen: boolean;
    onClose: () => void;
    sessionId: string | null;
    token: string | null;
    reportTitle: string;
}

export const ShareReportModal = React.memo(({
    isOpen,
    onClose,
    sessionId,
    token,
    reportTitle
}: ShareReportModalProps) => {
    const [isGenerating, setIsGenerating] = useState(false);
    const [shareUrl, setShareUrl] = useState<string | null>(null);
    const [isCopied, setIsCopied] = useState(false);
    const [shareSettings, setShareSettings] = useState<ShareSettings>({
        isPublic: true,
        password: '',
        allowedEmails: '',
        maxViews: null,
        expiresInDays: 7,
        shareMessage: ''
    });
    const [shareDetails, setShareDetails] = useState<ShareResponse['share'] | null>(null);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    useEffect(() => {
        if (!isOpen) {
            setShareUrl(null);
            setIsCopied(false);
            setShareDetails(null);
            setShareSettings({
                isPublic: true,
                password: '',
                allowedEmails: '',
                maxViews: null,
                expiresInDays: 7,
                shareMessage: ''
            });
            setShowAdvanced(false);
            setShowPassword(false);
        }
    }, [isOpen]);

    const generateShareLink = useCallback(async () => {
        if (!sessionId || !token) {
            toast.error('Session ID or authentication is missing');
            return;
        }

        if (!shareSettings.isPublic && !shareSettings.password) {
            toast.error('Password is required for restricted access');
            return;
        }

        setIsGenerating(true);

        try {
            const allowedEmailsArray = shareSettings.allowedEmails
                .split(',')
                .map(email => email.trim())
                .filter(email => email.length > 0 && email.includes('@'));

            const requestBody: Record<string, unknown> = {
                session_id: sessionId,
                access_type: 'view',
                is_public: shareSettings.isPublic,
                allowed_emails: allowedEmailsArray.length > 0 ? allowedEmailsArray : [],
                max_views: shareSettings.maxViews || 10,
                expires_in_days: shareSettings.expiresInDays || 1,
                share_message: shareSettings.shareMessage || ''
            };

            // Only include password if user actually set one
            if (shareSettings.password && shareSettings.password.trim()) {
                requestBody.password = shareSettings.password;
            }

            console.log("Creating share with request body:", JSON.stringify(requestBody, null, 2));

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/workflow/share`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || errorData.message || `Failed to create share link (${response.status})`);
            }

            const data: ShareResponse = await response.json();

            if (data.success && data.share?.share_url) {
                setShareUrl(data.share.share_url);
                setShareDetails(data.share);
                toast.success('Share link created successfully!');
            } else {
                throw new Error(data.message || 'Failed to create share link');
            }
        } catch (error: unknown) {
            console.error('Share link creation error:', error);
            toast.error(error instanceof Error ? error.message : 'Failed to create share link');
        } finally {
            setIsGenerating(false);
        }
    }, [sessionId, token, shareSettings]);

    const copyToClipboard = useCallback(async () => {
        if (!shareUrl) return;

        try {
            await navigator.clipboard.writeText(shareUrl);
            setIsCopied(true);
            toast.success('Link copied to clipboard!');
            setTimeout(() => setIsCopied(false), 2000);
        } catch {
            const textArea = document.createElement('textarea');
            textArea.value = shareUrl;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            setIsCopied(true);
            toast.success('Link copied to clipboard!');
            setTimeout(() => setIsCopied(false), 2000);
        }
    }, [shareUrl]);

    const formatExpiryDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
                <DialogHeader className="bg-brand-25 dark:bg-gray-800 -mx-6 -mt-6 px-6 pt-6 pb-4 rounded-t-lg border-b border-brand-200 dark:border-brand-700">
                    <DialogTitle className="flex items-center gap-2">
                        <Share2 className="h-5 w-5 text-brand-500" />
                        <span className="text-lg font-medium text-brand-500">Share Report</span>
                    </DialogTitle>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        Create a shareable link for <span className="font-medium text-gray-700 dark:text-gray-300">&quot;{reportTitle.length > 50 ? reportTitle.substring(0, 50) + '...' : reportTitle}&quot;</span>
                    </p>
                </DialogHeader>

                {!shareUrl ? (
                    <div className="space-y-4 py-2">
                        <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                            <div className="flex items-center gap-3">
                                {shareSettings.isPublic ? (
                                    <Globe className="h-5 w-5 text-green-500" />
                                ) : (
                                    <Lock className="h-5 w-5 text-amber-500" />
                                )}
                                <div>
                                    <p className="font-medium text-gray-900 dark:text-white text-sm">
                                        {shareSettings.isPublic ? 'Public Access' : 'Restricted Access'}
                                    </p>
                                    <p className="text-xs text-gray-500 dark:text-gray-400">
                                        {shareSettings.isPublic
                                            ? 'Anyone with the link can view'
                                            : 'Only specified emails can view'}
                                    </p>
                                </div>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setShareSettings(prev => ({ ...prev, isPublic: !prev.isPublic }))}
                                className="text-xs"
                            >
                                {shareSettings.isPublic ? 'Make Private' : 'Make Public'}
                            </Button>
                        </div>

                        {!shareSettings.isPublic && (
                            <div className="space-y-2">
                                <Label className="text-sm flex items-center gap-2">
                                    <Lock className="h-4 w-4 text-gray-500" />
                                    Password Protection <span className="text-red-500">*</span>
                                </Label>
                                <div className="relative">
                                    <Input
                                        type={showPassword ? "text" : "password"}
                                        placeholder="Enter password"
                                        value={shareSettings.password}
                                        onChange={(e) => setShareSettings(prev => ({ ...prev, password: e.target.value }))}
                                        className="text-sm pr-10"
                                        autoComplete="new-password"
                                        data-lpignore="true"
                                        data-form-type="other"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none"
                                    >
                                        {showPassword ? (
                                            <EyeOff className="h-4 w-4" />
                                        ) : (
                                            <Eye className="h-4 w-4" />
                                        )}
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Advanced Settings Dropdown - Only visible for restricted access */}
                        {!shareSettings.isPublic && (
                            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                                <button
                                    type="button"
                                    onClick={() => setShowAdvanced(!showAdvanced)}
                                    className="w-full flex items-center justify-between p-2 rounded-lg bg-gray-25 border border-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                                >
                                    <span className="text-sm font-medium text-brand-500 dark:text-brand-300">Advanced Settings</span>
                                    <ChevronDown
                                        className={`h-4 w-4 text-gray-500 transition-transform duration-200 ${showAdvanced ? 'rotate-180' : ''}`}
                                    />
                                </button>

                                <div className={`overflow-hidden transition-all duration-200 ease-in-out ${showAdvanced ? 'max-h-[500px] opacity-100 mt-3' : 'max-h-0 opacity-0'
                                    }`}>
                                    <div className="space-y-4 pb-1">
                                        {/* Password Protection */}
                                        {/* Link Expiry */}
                                        <div className="space-y-2">
                                            <Label className="text-sm flex items-center gap-2">
                                                <Calendar className="h-4 w-4 text-gray-500" />
                                                Link Expiry
                                            </Label>
                                            <div className="flex gap-2">
                                                {[1, 7, 30, 90].map(days => (
                                                    <Button
                                                        key={days}
                                                        variant={shareSettings.expiresInDays === days ? 'default' : 'outline'}
                                                        size="sm"
                                                        onClick={() => setShareSettings(prev => ({ ...prev, expiresInDays: days }))}
                                                        className={`flex-1 text-xs ${shareSettings.expiresInDays === days ? 'bg-brand-500' : ''}`}
                                                    >
                                                        {days === 1 ? '1 Day' : days === 7 ? '1 Week' : days === 30 ? '1 Month' : '3 Months'}
                                                    </Button>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Allowed Emails */}
                                        <div className="space-y-2">
                                            <Label className="text-sm flex items-center gap-2">
                                                <Users className="h-4 w-4 text-gray-500" />
                                                Allowed Emails
                                            </Label>
                                            <Input
                                                type="text"
                                                placeholder="email1@example.com, email2@example.com"
                                                value={shareSettings.allowedEmails}
                                                onChange={(e) => setShareSettings(prev => ({ ...prev, allowedEmails: e.target.value }))}
                                                className="text-sm"
                                            />
                                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                                Comma-separated list of email addresses
                                            </p>
                                        </div>

                                        {/* Max Views */}
                                        <div className="space-y-2">
                                            <Label className="text-sm flex items-center gap-2">
                                                <Eye className="h-4 w-4 text-gray-500" />
                                                Max Views (Optional)
                                            </Label>
                                            <Input
                                                type="number"
                                                placeholder="Unlimited"
                                                min={1}
                                                value={shareSettings.maxViews || ''}
                                                onChange={(e) => setShareSettings(prev => ({
                                                    ...prev,
                                                    maxViews: e.target.value ? parseInt(e.target.value) : null
                                                }))}
                                                className="text-sm"
                                            />
                                        </div>

                                        {/* Share Message */}
                                        <div className="space-y-2">
                                            <Label className="text-sm flex items-center gap-2">
                                                <Share2 className="h-4 w-4 text-gray-500" />
                                                Share Message (Optional)
                                            </Label>
                                            <Input
                                                type="text"
                                                placeholder="Add a message for recipients..."
                                                value={shareSettings.shareMessage}
                                                onChange={(e) => setShareSettings(prev => ({ ...prev, shareMessage: e.target.value }))}
                                                className="text-sm"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="space-y-4 py-2">
                        <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-3">
                                <Check className="h-6 w-6 text-green-600 dark:text-green-400" />
                            </div>
                            <p className="font-medium text-green-800 dark:text-green-300">Link Created Successfully!</p>
                        </div>

                        <div className="space-y-2">
                            <Label className="text-sm flex items-center gap-2">
                                <Link2 className="h-4 w-4 text-gray-500" />
                                Share Link
                            </Label>
                            <div className="flex gap-2">
                                <Input
                                    value={shareUrl}
                                    readOnly
                                    className="text-sm font-mono bg-gray-50 dark:bg-gray-800"
                                />
                                <Button
                                    onClick={copyToClipboard}
                                    variant={isCopied ? 'default' : 'outline'}
                                    className={`shrink-0 ${isCopied ? 'bg-green-600 hover:bg-green-700' : ''}`}
                                >
                                    {isCopied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                </Button>
                            </div>
                        </div>


                        <div className="flex items-center justify-between gap-3 mt-4 p-3 bg-brand-25 dark:bg-brand-50 rounded-lg border border-transparent hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-300">
                            <Label className="text-sm flex items-center gap-2 shrink-0 text-brand-500 dark:text-brand-300">
                                <Share2 className="h-4 w-4" />
                                <span className="font-medium">Share to Your Socials:</span>
                            </Label>
                            <div className="flex items-center gap-2 flex-wrap">
                                {/* LinkedIn (Disabled) */}
                                {/* <Button
                                    variant="outline"
                                    size="icon"
                                    className="h-9 w-9 text-[#0077b5] border-[#0077b5]/20 hover:bg-[#0077b5]/10 bg-white dark:bg-gray-800 opacity-60 cursor-not-allowed shadow-sm"
                                    disabled
                                    title="LinkedIn sharing coming soon"
                                >
                                    <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
                                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                                    </svg>
                                </Button> */}

                                {/* Telegram */}
                                <a
                                    href={`https://t.me/share/url?url=${encodeURIComponent(shareUrl || '')}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        className="h-9 w-9 text-[#0088cc] border-[#0088cc]/20 hover:bg-[#0088cc]/10 bg-white dark:bg-gray-800 shadow-sm transition-transform hover:scale-105"
                                    >
                                        <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
                                            <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 11.944 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
                                        </svg>
                                    </Button>
                                </a>

                                {/* WhatsApp */}
                                <a
                                    href={`https://wa.me/?text=${encodeURIComponent(shareUrl || '')}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        className="h-9 w-9 text-[#25D366] border-[#25D366]/20 hover:bg-[#25D366]/10 bg-white dark:bg-gray-800 shadow-sm transition-transform hover:scale-105"
                                    >
                                        <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
                                            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413z" />
                                        </svg>
                                    </Button>
                                </a>

                                {/* Twitter / X */}
                                <a
                                    href={`https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl || '')}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        className="h-9 w-9 text-black dark:text-white border-black/20 dark:border-white/20 hover:bg-black/5 dark:hover:bg-white/10 bg-white dark:bg-gray-800 shadow-sm transition-transform hover:scale-105"
                                    >
                                        <svg viewBox="0 0 24 24" fill="currentColor" className="h-3.5 w-3.5">
                                            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                                        </svg>
                                    </Button>
                                </a>
                            </div>
                        </div>

                        {shareDetails && (
                            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-2 text-sm">
                                <div className="flex items-center justify-between">
                                    <span className="text-gray-500 dark:text-gray-400 flex items-center gap-2">
                                        {shareDetails.is_public ? <Globe className="h-4 w-4" /> : <Lock className="h-4 w-4" />}
                                        Access
                                    </span>
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {shareDetails.is_public ? 'Public' : 'Restricted'}
                                    </span>
                                </div>
                                {shareDetails.has_password && (
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-500 dark:text-gray-400 flex items-center gap-2">
                                            <Lock className="h-4 w-4" />
                                            Password
                                        </span>
                                        <span className="font-medium text-amber-600 dark:text-amber-400">Protected</span>
                                    </div>
                                )}
                                <div className="flex items-center justify-between">
                                    <span className="text-gray-500 dark:text-gray-400 flex items-center gap-2">
                                        <Calendar className="h-4 w-4" />
                                        Expires
                                    </span>
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {formatExpiryDate(shareDetails.expires_at)}
                                    </span>
                                </div>
                                {shareDetails.allowed_emails && shareDetails.allowed_emails.length > 0 && (
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-500 dark:text-gray-400 flex items-center gap-2">
                                            <Users className="h-4 w-4" />
                                            Recipients
                                        </span>
                                        <span className="font-medium text-gray-900 dark:text-white">
                                            {shareDetails.allowed_emails.length} email(s)
                                        </span>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                <DialogFooter className="gap-2">
                    <Button variant="outline" onClick={onClose}>
                        {shareUrl ? 'Close' : 'Cancel'}
                    </Button>
                    {!shareUrl && (
                        <Button
                            onClick={generateShareLink}
                            disabled={isGenerating || !sessionId}
                            className="bg-brand-500 hover:bg-brand-600"
                        >
                            {isGenerating ? (
                                <>
                                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                    Generating...
                                </>
                            ) : (
                                <>
                                    <Share2 className="h-4 w-4 mr-2" />
                                    Generate Link
                                </>
                            )}
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
});

ShareReportModal.displayName = 'ShareReportModal';
