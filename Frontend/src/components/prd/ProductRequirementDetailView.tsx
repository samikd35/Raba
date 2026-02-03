"use client";

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import CreditCostBadge from "@/components/common/CreditCostBadge";
import { usePRD } from "@/hooks/usePRD";
import { useAuthStore } from "@/stores/authStore";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
    ArrowLeft,
    ArrowRight,
} from "lucide-react";
import { PRDHeader } from "./PRDHeader";
import { PRDLoadingState } from "./PRDLoadingState";
import { PRDErrorState } from "./PRDErrorState";
import { GeneratePRDModal } from "./GeneratePRDModal";

// Helper function to clean text artifacts (specifically \u0011, \u0012 and other control chars)
const cleanText = (data: any): any => {
    if (typeof data === 'string') {
        // Replace control characters (0000-001F range, excluding \t, \n, \r) with hyphen
        // \u0009 is tab, \u000A is newline, \u000D is CR
        return data.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '-');
    }
    if (Array.isArray(data)) {
        return data.map(item => cleanText(item));
    }
    if (typeof data === 'object' && data !== null) {
        const cleaned: any = {};
        for (const key in data) {
            cleaned[key] = cleanText(data[key]);
        }
        return cleaned;
    }
    return data;
};

interface ProductRequirementDetailViewProps {
    projectId: string;
    backPath: string;
    continuePath: string;
}

export function ProductRequirementDetailView({
    projectId,
    backPath,
    continuePath
}: ProductRequirementDetailViewProps) {
    const router = useRouter();
    const { token } = useAuthStore();
    const hasFetchedRef = useRef(false);

    const [isBackLoading, setIsBackLoading] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [isContinueLoading, setIsContinueLoading] = useState(false);
    const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);

    const {
        isLoading,
        prdData,
        error,
        isRegenerating,
        isSaving,
        fetchPRDData,
        regeneratePRD,
        savePRDChanges,
    } = usePRD({
        projectId,
        onAuthError: () => router.push("/signin"),
    });

    // Calculate cleaned PRD JSON unconditionally
    // If prdData changes, re-calculate. If prdData is null, result is null.
    const cleanedPrdJson = useMemo(() => {
        if (!prdData?.prd_json) return null;
        return cleanText(prdData.prd_json);
    }, [prdData]);

    // Fetch data only once when token is available
    useEffect(() => {
        if (token && projectId && !hasFetchedRef.current) {
            hasFetchedRef.current = true;
            fetchPRDData();
        }
    }, [token, projectId, fetchPRDData]);

    const handleBackToProject = useCallback(() => {
        setIsBackLoading(true);
        router.push(backPath);
    }, [backPath, router]);

    const handleEditToggle = useCallback(() => {
        setIsEditing(!isEditing);
    }, [isEditing]);

    const handleSaveChanges = useCallback(async () => {
        const success = await savePRDChanges({});
        if (success) {
            setIsEditing(false);
        }
    }, [savePRDChanges]);

    const handleRegenerate = useCallback(async () => {
        await regeneratePRD();
    }, [regeneratePRD]);

    const handleContinueToBMC = useCallback(() => {
        setIsContinueLoading(true);
        router.push(continuePath);
    }, [continuePath, router]);

    // Modal handlers
    const handleOpenGenerateModal = useCallback(() => {
        setIsGenerateModalOpen(true);
    }, []);

    const handleCloseGenerateModal = useCallback(() => {
        setIsGenerateModalOpen(false);
    }, []);

    const handlePRDGenerated = useCallback(() => {
        // Refresh the page data after PRD is generated
        hasFetchedRef.current = false;
        fetchPRDData();
    }, [fetchPRDData]);

    // Auto-open modal when there's a 404 error (no PRD found)
    useEffect(() => {
        if (error && error.toLowerCase().includes('no product requirements found')) {
            if (process.env.NODE_ENV === 'development') {
                console.log('🚀 No PRD found, automatically opening generation modal...');
            }
            // Small delay to ensure component is mounted
            const timer = setTimeout(() => {
                handleOpenGenerateModal();
            }, 500);

            return () => clearTimeout(timer);
        }
    }, [error, handleOpenGenerateModal]);

    // Loading State
    if (isLoading) {
        return <PRDLoadingState />;
    }

    // Error State
    if (error || !prdData) {
        return (
            <>
                <PRDErrorState
                    error={error || "Failed to load PRD"}
                    onRetry={fetchPRDData}
                    onGenerateClick={handleOpenGenerateModal}
                />
                <GeneratePRDModal
                    isOpen={isGenerateModalOpen}
                    onClose={handleCloseGenerateModal}
                    projectId={projectId}
                    onPRDGenerated={handlePRDGenerated}
                />
            </>
        );
    }

    const { prd_metadata, validation_status, version } = prdData;
    const prd_json = cleanedPrdJson || prdData.prd_json; // Fallback just in case, though loading state should prevent null here

    return (
        <>
            <div className="container mx-auto space-y-2 mb-2">
                <PageBreadcrumb pageTitle="Your Product Requirement Detail" titleSuffix={<CreditCostBadge cost={35} />}  />

                <PRDHeader
                    validationStatus={validation_status}
                    version={version}
                    isEditing={isEditing}
                    isSaving={isSaving}
                    isRegenerating={isRegenerating}
                    isBackLoading={isBackLoading}
                    isContinueLoading={isContinueLoading}
                    onBack={handleBackToProject}
                    onEditToggle={handleEditToggle}
                    onSave={handleSaveChanges}
                    onRegenerate={handleRegenerate}
                    onGeneratePRD={handleOpenGenerateModal}
                    onContinue={handleContinueToBMC}
                    backLabel="Back to projects"
                    continueLabel="Continue to next step"
                    showGenerateOption={true}
                />
            </div>

            <div className="bg-white dark:bg-[#101828]">
                {/* Main Report Content */}
                <div className="mx-auto bg-white dark:bg-gray-900 min-h-screen">
                    <Card className="p-8 shadow-sm">
                        {/* Document Title */}
                        <h1 className="text-4xl font-bold text-brand-500 dark:text-brand-200 pb-2 leading-tight border-b">
                            Product Requirement Document
                        </h1>

                        {/* 1. Purpose & Problem Statement */}
                        <section>
                            <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                1. Purpose
                            <span className="text-xs block text-gray-500 dark:text-gray-400"> {prd_json.purpose?.section_description}</span>
                            </h2>
                            <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                <p className="mb-3">{prd_json.purpose?.statement || prd_json.purpose?.purpose_statement}</p>
                                {/* <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Target Persona:</strong> {prd_json.purpose?.target_persona}</p> */}
                                <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Validated Problem:</strong> {prd_json.purpose?.validated_problem}</p>
                            </div>
                        </section>

                        {/* 2. Primary Persona */}
                        <section>
                            <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                2. Primary Persona
                            <span className="text-xs block text-gray-500 dark:text-gray-400"> {prd_json.primary_persona?.section_description}</span>
                            </h2>
                            <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Name:</strong> {prd_json.primary_persona?.name || prd_json.primary_persona?.persona_name}</p>
                                {prd_json.primary_persona?.description && (
                                    <p className="mb-3">{prd_json.primary_persona.description}</p>
                                )}
                                {prd_json.primary_persona?.segment && (
                                    <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Segment:</strong> {prd_json.primary_persona.segment}</p>
                                )}
                                {prd_json.primary_persona?.primary_job && (
                                    <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Primary Job:</strong> {prd_json.primary_persona.primary_job.job_statement}</p>
                                )}
                                {prd_json.primary_persona?.primary_jtbd && (
                                    <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Primary Job-to-be-Done:</strong> {prd_json.primary_persona.primary_jtbd}</p>
                                )}

                                {(prd_json.primary_persona?.key_pains || []).length > 0 && (
                                    <>
                                        <p className="mb-2 mt-4"><strong className="text-brand-500 dark:text-brand-400">Key Pains:</strong></p>
                                        <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                            {prd_json.primary_persona.key_pains.map((pain: string, idx: number) => (
                                                <li key={idx}>{pain}</li>
                                            ))}
                                        </ul>
                                    </>
                                )}

                                {(prd_json.primary_persona?.desired_gains || []).length > 0 && (
                                    <>
                                        <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Desired Gains:</strong></p>
                                        <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                            {prd_json.primary_persona.desired_gains.map((gain: string, idx: number) => (
                                                <li key={idx}>{gain}</li>
                                            ))}
                                        </ul>
                                    </>
                                )}
                            </div>
                        </section>

                        {/* 3. Scope */}
                        <section>
                            <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                3. Scope
                                <span className="text-xs block text-gray-500 dark:text-gray-400"> {prd_json.scope?.section_description}</span>
                            </h2>
                            <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                <div className=" rounded-lg p-5 border border-gray-200 dark:border-gray-700 mb-4 ">
                                    <div className="flex items-center mb-4">

                                        <h3 className="text-lg font-semibold text-brand-500 dark:text-white">In Scope</h3>
                                    </div>

                                    {prd_json.scope?.in_scope?.geography && (
                                        <div className="mb-4 p-3 bg-brand-25 dark:bg-brand-800 rounded-md border border-brand-100 dark:border-gray-700">
                                            <p className="text-sm font-medium text-brand-500 dark:text-brand-400 mb-1">Geography</p>
                                            <p className="text-gray-700 dark:text-gray-300">{prd_json.scope.in_scope.geography}</p>
                                        </div>
                                    )}

                                    {(prd_json.scope?.in_scope?.user_segments || []).length > 0 && (
                                        <div className="mb-4">
                                            <p className="mb-3 font-medium text-brand-500 dark:text-brand-400">User Segments</p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                {prd_json.scope.in_scope.user_segments.map((seg: string, idx: number) => (
                                                    <div key={idx} className="flex items-start space-x-3 p-3 bg-brand-25 dark:bg-brand-800 rounded-md border border-brand-100 dark:border-gray-700 hover:shadow-sm transition-shadow">
                                                        <div className="w-2 h-2 bg-brand-500 rounded-full shrink-0 mt-1.5"></div>
                                                        <span className="text-sm">{seg}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {(prd_json.scope?.in_scope?.core_flows || []).length > 0 && (
                                        <div className="mb-4">
                                            <p className="mb-3 font-medium text-brand-500 dark:text-brand-400">Core Flows</p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                {prd_json.scope.in_scope.core_flows.map((flow: string, idx: number) => (
                                                    <div key={idx} className="flex items-start space-x-3 p-3 bg-brand-25 dark:bg-brand-800 rounded-md border border-brand-100 dark:border-gray-700 hover:shadow-sm transition-shadow">
                                                        <div className="w-2 h-2 bg-brand-500 rounded-full shrink-0 mt-1.5"></div>
                                                        <span className="text-sm">{flow}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {(prd_json.scope?.in_scope?.additional || []).length > 0 && (
                                        <div className="mb-4">
                                            <p className="mb-3 font-medium text-brand-500 dark:text-brand-400">Additional</p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                {prd_json.scope.in_scope.additional.map((item: string, idx: number) => (
                                                    <div key={idx} className="flex items-start space-x-3 p-3 bg-brand-25 dark:bg-brand-800 rounded-md border border-brand-100 dark:border-gray-700 hover:shadow-sm transition-shadow">
                                                        <div className="w-2 h-2 bg-brand-500 rounded-full shrink-0 mt-1.5"></div>
                                                        <span className="text-sm">{item}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {(prd_json.scope?.out_of_scope || []).length > 0 && (
                                    <div className=" rounded-lg p-5 border border-gray-200 dark:border-gray-700 mb-4">
                                        <div className="flex items-center mb-4">

                                            <h3 className="text-lg font-semibold text-brand-500 dark:text-white">Out of Scope</h3>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            {prd_json.scope.out_of_scope.map((item: string, idx: number) => (
                                                <div key={idx} className="flex items-start space-x-3 p-3 bg-brand-25 dark:bg-brand-800 rounded-md border border-brand-100 dark:border-gray-700 hover:shadow-sm transition-shadow">
                                                    <div className="w-2 h-2 bg-brand-500 rounded-full shrink-0 mt-1.5"></div>
                                                    <span className="text-sm">{item}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </section>

                        {/* 4. Objectives */}
                        <section>
                            <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                4. Objectives
                                <span className="text-xs block text-gray-500 dark:text-gray-400"> {prd_json.objective?.section_description}</span>
                            </h2>
                            <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                {prd_json.objective?.primary_objective && (
                                    <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Primary Objective:</strong> {prd_json.objective.primary_objective}</p>
                                )}

                                {(prd_json.objective?.key_results || []).length > 0 && (
                                    <>
                                        <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Key Results:</strong></p>
                                        <ul className="list-decimal list-outside pl-6 mb-3 space-y-1">
                                            {prd_json.objective.key_results.map((kr: any, idx: number) => (
                                                <li key={idx}>
                                                    <strong className="text-brand-500 dark:text-brand-400">{kr.result}</strong> — Target: {kr.target}
                                                </li>
                                            ))}
                                        </ul>
                                    </>
                                )}

                                {(prd_json.objective?.learning_goals || []).length > 0 && (
                                    <>
                                        {/* <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Learning Goals:</strong></p> */}
                                        <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                            {prd_json.objective.learning_goals.map((goal: string, idx: number) => (
                                                <li className="pb-3" key={idx}>{goal}</li>
                                            ))}
                                        </ul>
                                    </>
                                )}

                                {/* {(prd_json.objective?.success_criteria || []).length > 0 && (
                                    <>
                                        <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Success Criteria:</strong></p>
                                        <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                            {prd_json.objective.success_criteria.map((criteria: string, idx: number) => (
                                                <li key={idx}>{criteria}</li>
                                            ))}
                                        </ul>
                                    </>
                                )} */}
                            </div>
                        </section>

                        {/* 5. Must-Have Features  */}
                        {((prd_json.must_have_features?.features || prd_json.mvp_features?.must_haves) || []).length > 0 && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    5. Must-Have Features
                                    <span className="text-xs block text-gray-500 dark:text-gray-400"> {prd_json.must_have_features?.section_description}</span>
                                </h2>
                                <div className="overflow-x-auto">
                                    <table className="w-full border-collapse">
                                        <thead>
                                            <tr className="bg-brand-50 dark:bg-brand-900/30">
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700">#</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 min-w-[200px]">Feature Name</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 w-1/4 min-w-[280px]">Description</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700">Job Supported</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700">Job Type</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 min-w-[200px]">Advantage</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 min-w-[200px]">Benefit</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {(prd_json.must_have_features?.features || prd_json.mvp_features?.must_haves || []).map((feature: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 font-medium align-top">{idx + 1}</td>
                                                    <td className="p-3 text-sm border border-gray-200 dark:border-gray-700 align-top min-w-[200px]">
                                                        <div className="space-y-2">
                                                            <span className="text-brand-600 dark:text-brand-400 font-semibold block">{feature.feature_name || '-'}</span>
                                                            {(feature.vpc_reference || feature.bmc_reference) && (
                                                                <div className="flex flex-wrap gap-1.5 mt-2">
                                                                    {feature.vpc_reference && (
                                                                        <span className="flex flex-col items-start py-0.5 px-2 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs border border-blue-200 dark:border-blue-700">
                                                                            <span className="font-medium">VPC Reference :</span> <span>{feature.vpc_reference}</span>
                                                                        </span>
                                                                    )}
                                                                    {feature.bmc_reference && (
                                                                        <span className="flex flex-col items-start py-0.5 px-2 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded text-xs border border-emerald-200 dark:border-emerald-700">
                                                                            <span className="font-medium">BMC Reference :</span> <span>{feature.bmc_reference}</span>
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 w-1/4 min-w-[280px] align-top">{feature.description || '-'}</td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 align-top">{feature.job_supported || '-'}</td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 align-top">
                                                        <span className="inline-block py-0.5 px-2 bg-gray-100 dark:bg-gray-700 rounded text-xs capitalize">{feature.job_type || '-'}</span>
                                                    </td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 align-top min-w-[200px]">
                                                        {feature.advantage || '-'}
                                                    </td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 align-top min-w-[200px]">
                                                        {feature.benefit || '-'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </section>
                        )}

                        {/* 6. Nice-to-Have Features */}
                        {((prd_json.nice_to_have_features?.features || prd_json.mvp_features?.nice_to_haves) || []).length > 0 && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    6. Nice-to-Have Features
                                    <span className="text-xs block text-gray-500 dark:text-gray-400"> {prd_json.nice_to_have_features?.section_description}</span>
                                </h2>
                                <div className="overflow-x-auto">
                                    <table className="w-full border-collapse">
                                        <thead>
                                            <tr className="bg-brand-50 dark:bg-brand-900/30">
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700">#</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 min-w-[180px]">Feature Name</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 w-1/4 min-w-[250px]">Description</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700">Job Supported</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 min-w-[180px]">Advantage</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 min-w-[180px]">Benefit</th>
                                                <th className="text-left p-3 text-sm font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 min-w-[200px]">Deferral Rationale</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {(prd_json.nice_to_have_features?.features || prd_json.mvp_features?.nice_to_haves || []).map((feature: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 font-medium align-top">{idx + 1}</td>
                                                    <td className="p-3 text-sm text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700 font-semibold align-top min-w-[180px]">{feature.feature_name || '-'}</td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 w-1/4 min-w-[250px] align-top">{feature.description || '-'}</td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 align-top">{feature.job_supported || '-'}</td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 align-top min-w-[180px]">
                                                        {feature.advantage || '-'}
                                                    </td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 align-top min-w-[180px]">
                                                        {feature.benefit || '-'}
                                                    </td>
                                                    <td className="p-3 text-sm text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 align-top min-w-[200px]">
                                                        {feature.rationale_for_deferral || '-'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </section>
                        )}

                        {/* 7. Critical Workflows */}
                        {((prd_json.critical_workflows?.workflows || prd_json.critical_workflows) || []).length > 0 && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    7. Critical Workflows (User Journey) 
                                    <span className="text-xs block text-gray-500 dark:text-gray-400"> {prd_json.critical_workflows?.section_description}</span>
                                </h2>
                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                    {(prd_json.critical_workflows?.workflows || prd_json.critical_workflows || []).map((workflow: any, idx: number) => (
                                        <div key={idx} className="mb-5 pb-4 border-b border-gray-100 dark:border-gray-800 last:border-0">
                                            <h3 className="text-lg font-semibold text-brand-500 dark:text-brand-400 mb-2">
                                                {workflow.workflow_name}
                                            </h3>
                                            {workflow.description && <p className="mb-2 text-sm italic">{workflow.description}</p>}
                                            {workflow.value_delivered && <p className="mb-2 text-sm"><strong className="text-brand-500 dark:text-brand-400">Value Delivered:</strong> {workflow.value_delivered}</p>}
                                            <ol className="list-outside pl-8 space-y-2">
                                                {(workflow.steps || []).map((step: string, stepIdx: number) => (
                                                    <li key={stepIdx} className="font-normal"><span className="font-bold">{stepIdx + 1}.</span> {step}</li>
                                                ))}
                                            </ol>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* 8. Success Signals */}
                        {prd_json.success_signals && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    8. Success Signals
                                    <span className="text-xs block text-gray-500 dark:text-gray-400"> {prd_json.success_signals.section_description}</span>
                                </h2>
                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                    {(prd_json.success_signals.quantitative || []).length > 0 && (
                                        <>
                                            <h3 className="text-lg font-semibold mt-2 mb-2 text-brand-500 dark:text-brand-400">Quantitative Metrics</h3>
                                            {prd_json.success_signals.quantitative.map((signal: any, idx: number) => (
                                                <div key={idx} className="mb-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700">
                                                    <div className="flex items-start justify-between mb-2">
                                                        <h4 className="text-base font-semibold text-brand-500 dark:text-brand-400">
                                                            {signal.metric_name}
                                                        </h4>
                                                        <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-md">
                                                            Target: {signal.target}
                                                        </span>
                                                    </div>
                                                    {signal.description && (
                                                        <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">{signal.description}</p>
                                                    )}
                                                    {signal.measurement_method && (
                                                        <div className="text-sm text-gray-600 dark:text-gray-400">
                                                            <em>Measurement: {signal.measurement_method}</em>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </>
                                    )}

                                    {(prd_json.success_signals.qualitative || []).length > 0 && (
                                        <>
                                            <h3 className="text-lg font-semibold mt-4 mb-2 text-brand-500 dark:text-brand-400">Qualitative Signals</h3>
                                            {prd_json.success_signals.qualitative.map((signal: any, idx: number) => (
                                                <div key={idx} className="mb-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700">
                                                    <div className="flex items-start justify-between mb-2">
                                                        <h4 className="text-base font-semibold text-brand-500 dark:text-brand-400">
                                                            {signal.signal_name}
                                                        </h4>
                                                        <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-md">
                                                            Target: {signal.target}
                                                        </span>
                                                    </div>
                                                    {signal.description && (
                                                        <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">{signal.description}</p>
                                                    )}
                                                    {signal.measurement_method && (
                                                        <div className="text-sm text-gray-600 dark:text-gray-400">
                                                            <em>Measurement: {signal.measurement_method}</em>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </>
                                    )}
                                </div>
                            </section>
                        )}

                        {/* 9. FAB Analysis */}
                        {/* {(prd_json.mvp_features?.must_haves_fab_analysis || []).length > 0 && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    9. Feature-Advantage-Benefit Analysis
                                </h2>
                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                    {prd_json.mvp_features.must_haves_fab_analysis.map((fab: any, idx: number) => (
                                        <div key={idx} className="mb-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700">
                                            <h3 className="text-base font-semibold text-brand-500 dark:text-brand-400 mb-2">
                                                {fab.feature}
                                            </h3>
                                            <div className="space-y-2">
                                                <div className="flex items-start">
                                                    <span className="inline-block w-20 text-sm font-medium text-gray-500 dark:text-gray-400 shrink-0">
                                                        Advantage:
                                                    </span>
                                                    <p className="text-sm text-gray-700 dark:text-gray-300">
                                                        {fab.advantage}
                                                    </p>
                                                </div>
                                                <div className="flex items-start">
                                                    <span className="inline-block w-20 text-sm font-medium text-gray-500 dark:text-gray-400 shrink-0">
                                                        Benefit:
                                                    </span>
                                                    <p className="text-sm text-gray-700 dark:text-gray-300">
                                                        {fab.benefit}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )} */}
                        {/* 10. Production & Quality Control */}
                        {prd_json.production_qc && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    9. Production & Quality Control
                                    <span className="text-xs block text-gray-500 dark:text-gray-400"> {prd_json.production_qc.section_description}</span>
                                </h2>
                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                    {prd_json.production_qc.manufacturing_approach && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Manufacturing Approach:</strong> {prd_json.production_qc.manufacturing_approach}</p>
                                    )}
                                    {prd_json.production_qc.production_partner && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Production Partner:</strong> {prd_json.production_qc.production_partner}</p>
                                    )}
                                    {prd_json.production_qc.batch_size_initial && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Initial Batch Size:</strong> {prd_json.production_qc.batch_size_initial}</p>
                                    )}
                                    {prd_json.production_qc.lead_time && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Lead Time:</strong> {prd_json.production_qc.lead_time}</p>
                                    )}
                                    {prd_json.production_qc.production_method && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Production Method:</strong> {prd_json.production_qc.production_method}</p>
                                    )}

                                    {(prd_json.production_qc.quality_controls || prd_json.production_qc.quality_standards || []).length > 0 && (
                                        <>
                                            <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Quality Controls:</strong></p>
                                            <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                                {(prd_json.production_qc.quality_controls || prd_json.production_qc.quality_standards || []).map((item: string, idx: number) => (
                                                    <li key={idx}>{item}</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}
                                </div>
                            </section>
                        )}

                        {/* 11. Consumer Use Case */}
                        {prd_json.consumer_use_case && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    11. Consumer Use Case
                                </h2>
                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                    {prd_json.consumer_use_case.product_category && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Product Category:</strong> {prd_json.consumer_use_case.product_category}</p>
                                    )}
                                    {prd_json.consumer_use_case.consumption_context && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Consumption Context:</strong> {prd_json.consumer_use_case.consumption_context}</p>
                                    )}
                                    {prd_json.consumer_use_case.purchase_occasion && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Purchase Occasion:</strong> {prd_json.consumer_use_case.purchase_occasion}</p>
                                    )}
                                    {prd_json.consumer_use_case.usage_frequency && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Usage Frequency:</strong> {prd_json.consumer_use_case.usage_frequency}</p>
                                    )}
                                    {prd_json.consumer_use_case.usage_scenario && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Usage Scenario:</strong> {prd_json.consumer_use_case.usage_scenario}</p>
                                    )}

                                    {(prd_json.consumer_use_case.competing_alternatives || []).length > 0 && (
                                        <>
                                            <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Competing Alternatives:</strong></p>
                                            <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                                {prd_json.consumer_use_case.competing_alternatives.map((alt: string, idx: number) => (
                                                    <li key={idx}>{alt}</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}
                                </div>
                            </section>
                        )}

                        {/* 12. Packaging Formats */}
                        {prd_json.packaging_formats && (
                            <section className="mb-4">
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    12. Packaging Formats
                                </h2>
                                <div className="space-y-4">
                                    {prd_json.packaging_formats.primary_packaging && (
                                        <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700">
                                            <h3 className="text-base font-semibold text-brand-500 dark:text-brand-400 mb-2">Primary Packaging</h3>
                                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                                                <div>
                                                    <p className="text-gray-500 dark:text-gray-400">Format</p>
                                                    <p className="text-gray-700 dark:text-gray-300">{prd_json.packaging_formats.primary_packaging.format}</p>
                                                </div>
                                                <div>
                                                    <p className="text-gray-500 dark:text-gray-400">Size</p>
                                                    <p className="text-gray-700 dark:text-gray-300">{prd_json.packaging_formats.primary_packaging.size}</p>
                                                </div>
                                                <div>
                                                    <p className="text-gray-500 dark:text-gray-400">Material</p>
                                                    <p className="text-gray-700 dark:text-gray-300">{prd_json.packaging_formats.primary_packaging.material}</p>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {(prd_json.packaging_formats.sku_variants || []).length > 0 && (
                                        <div className="space-y-3">
                                            <h3 className="text-base font-semibold text-brand-500 dark:text-brand-400">SKU Variants</h3>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                {prd_json.packaging_formats.sku_variants.map((sku: any, idx: number) => (
                                                    <div key={idx} className="p-3 bg-white dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700">
                                                        <div className="flex items-start justify-between mb-1">
                                                            <h4 className="font-medium text-brand-500 dark:text-brand-400">{sku.variant_name}</h4>
                                                            <span className="text-sm px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                                                                {sku.target_price}
                                                            </span>
                                                        </div>
                                                        <div className="text-sm text-gray-600 dark:text-gray-400">
                                                            Size: {sku.size}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {(prd_json.packaging_formats.labeling_requirements || []).length > 0 && (
                                        <div className="space-y-3">
                                            <h3 className="text-base font-semibold text-brand-500 dark:text-brand-400">Labeling Requirements</h3>
                                            <ul className="space-y-2">
                                                {prd_json.packaging_formats.labeling_requirements.map((req: string, idx: number) => (
                                                    <li key={idx} className="flex items-start space-x-2 text-sm">
                                                        <span className="text-brand-500 dark:text-brand-400">•</span>
                                                        <span className="text-gray-700 dark:text-gray-300">{req}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {(prd_json.packaging_formats.formats || []).length > 0 && (
                                        <div className="space-y-3">
                                            <h3 className="text-base font-semibold text-brand-500 dark:text-brand-400">Additional Formats</h3>
                                            <ul className="space-y-2">
                                                {prd_json.packaging_formats.formats.map((format: string, idx: number) => (
                                                    <li key={idx} className="flex items-start space-x-2 text-sm">
                                                        <span className="text-brand-500 dark:text-brand-400">•</span>
                                                        <span className="text-gray-700 dark:text-gray-300">{format}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </section>
                        )}

                        {/* 13. Regulatory & Safety */}
                        {prd_json.regulatory_safety && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    13. Regulatory & Safety
                                </h2>
                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                    {prd_json.regulatory_safety.compliance_timeline && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Compliance Timeline:</strong> {prd_json.regulatory_safety.compliance_timeline}</p>
                                    )}

                                    {(prd_json.regulatory_safety.certifications_required || prd_json.regulatory_safety.certifications || []).length > 0 && (
                                        <>
                                            <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Certifications Required:</strong></p>
                                            <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                                {(prd_json.regulatory_safety.certifications_required || prd_json.regulatory_safety.certifications || []).map((cert: string, idx: number) => (
                                                    <li key={idx}>{cert}</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}

                                    {(prd_json.regulatory_safety.regulatory_bodies || []).length > 0 && (
                                        <>
                                            <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Regulatory Bodies:</strong></p>
                                            <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                                {prd_json.regulatory_safety.regulatory_bodies.map((body: string, idx: number) => (
                                                    <li key={idx}>{body}</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}

                                    {(prd_json.regulatory_safety.safety_testing || prd_json.regulatory_safety.safety_requirements || []).length > 0 && (
                                        <>
                                            <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Safety Testing:</strong></p>
                                            <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                                {(prd_json.regulatory_safety.safety_testing || prd_json.regulatory_safety.safety_requirements || []).map((req: string, idx: number) => (
                                                    <li key={idx}>{req}</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}
                                </div>
                            </section>
                        )}

                        {/* 14. Product Composition */}
                        {prd_json.product_composition && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    14. Product Composition
                                </h2>
                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                    {prd_json.product_composition.formulation_approach && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Formulation Approach:</strong> {prd_json.product_composition.formulation_approach}</p>
                                    )}
                                    {prd_json.product_composition.shelf_life && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Shelf Life:</strong> {prd_json.product_composition.shelf_life}</p>
                                    )}

                                    {(prd_json.product_composition.key_ingredients || prd_json.product_composition.ingredients || []).length > 0 && (
                                        <>
                                            <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Key Ingredients:</strong></p>
                                            <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                                {(prd_json.product_composition.key_ingredients || prd_json.product_composition.ingredients || []).map((ing: string, idx: number) => (
                                                    <li key={idx}>{ing}</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}

                                    {(prd_json.product_composition.quality_attributes || []).length > 0 && (
                                        <>
                                            <p className="mb-2"><strong className="text-brand-500 dark:text-brand-400">Quality Attributes:</strong></p>
                                            <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                                {prd_json.product_composition.quality_attributes.map((attr: string, idx: number) => (
                                                    <li key={idx}>{attr}</li>
                                                ))}
                                            </ul>
                                        </>
                                    )}
                                </div>
                            </section>
                        )}

                        {/* 15. Distribution Channels */}
                        {prd_json.distribution_channels && (
                            <section>
                                <h2 className="text-2xl font-bold text-brand-500 dark:text-brand-400 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                                    15. Distribution Channels
                                </h2>
                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                    {prd_json.distribution_channels.route_to_market && (
                                        <p className="mb-3"><strong className="text-brand-500 dark:text-brand-400">Route to Market:</strong> {prd_json.distribution_channels.route_to_market}</p>
                                    )}

                                    {(prd_json.distribution_channels.primary_channels || []).length > 0 && (
                                        <>
                                            <p className="mb-3 font-semibold text-gray-900 dark:text-white">Primary Channels:</p>
                                            <div className="space-y-3">
                                                {prd_json.distribution_channels.primary_channels.map((channel: any, idx: number) => (
                                                    <div key={idx} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                                                        <div className="flex items-start justify-between mb-2">
                                                            <h4 className="font-semibold text-brand-500 dark:text-brand-400">{channel.channel_name}</h4>
                                                            <span className="text-sm px-2 py-1 bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 rounded-md">
                                                                {channel.channel_type}
                                                            </span>
                                                        </div>
                                                        <div className="text-sm text-gray-600 dark:text-gray-400">
                                                            <span className="font-medium">Coverage:</span> {channel.geographic_coverage}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </>
                                    )}

                                    {(prd_json.distribution_channels.distribution_partners || []).length > 0 && (
                                        <>
                                            <p className="mb-3 mt-6 font-semibold text-gray-900 dark:text-white">Distribution Partners:</p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                {prd_json.distribution_channels.distribution_partners.map((partner: string, idx: number) => (
                                                    <div key={idx} className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                                                        <div className="w-2 h-2 bg-brand-500 rounded-full shrink-0"></div>
                                                        <span className="text-sm text-gray-700 dark:text-gray-300">{partner}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </>
                                    )}

                                    {(prd_json.distribution_channels.channels || []).length > 0 && (
                                        <ul className="list-disc list-outside pl-6 mb-3 space-y-1">
                                            {prd_json.distribution_channels.channels.map((channel: string, idx: number) => (
                                                <li key={idx}>{channel}</li>
                                            ))}
                                        </ul>
                                    )}
                                </div>
                            </section>
                        )}
                    </Card>

                    {/* Footer Navigation */}
                    <div className="flex items-center justify-center py-6 px-4 gap-4">
                        <Button
                            variant="outline"
                            onClick={handleBackToProject}
                            disabled={isBackLoading}
                            className="bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-900"
                        >
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Project
                        </Button>
                        <Button
                            onClick={handleContinueToBMC}
                            disabled={isContinueLoading}
                            className="bg-green-600 hover:bg-green-700"
                        >
                            Advance to next module
                            <ArrowRight className="h-4 w-4 ml-2" />
                        </Button>
                    </div>
                </div>

                <GeneratePRDModal
                    isOpen={isGenerateModalOpen}
                    onClose={handleCloseGenerateModal}
                    projectId={projectId}
                    onPRDGenerated={handlePRDGenerated}
                />
            </div>
        </>
    );
}
