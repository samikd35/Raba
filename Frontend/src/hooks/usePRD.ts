"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/authStore";

// TypeScript Interfaces
export interface PRDMetadata {
  template_code: string;
  template_name: string;
  template_version: string;
  schema_version: string;
  generated_at: string;
  research_used: boolean;
  research_sources_count: number | null;
}

export interface Scope {
  in_scope: {
    geography: string;
    additional: string[];
    core_flows: string[];
    user_segments: string[];
  };
  out_of_scope: string[];
}

export interface Purpose {
  statement: string;
  target_persona: string;
  validated_problem: string;
}

export interface Objective {
  learning_goals: string[];
  success_criteria: string[];
}

export interface Feature {
  feature_name: string;
  job_type: string;
  description: string;
  job_supported: string;
  vpc_reference: string;
  bmc_reference: string;
}

// New format for must-have features (A4 template)
export interface MustHaveFeature {
  feature_name: string;
  job_type: string;
  description: string;
  job_supported: string;
  vpc_reference: string;
  bmc_reference: string;
  benefit?: string;
  advantage?: string;
}

export interface NiceToHave {
  feature_name: string;
  job_type?: string;
  description: string;
  job_supported: string;
  rationale_for_deferral: string;
}

// New format for nice-to-have features (A4 template)
export interface NiceToHaveFeature {
  feature_name: string;
  description: string;
  job_supported: string;
  rationale_for_deferral: string;
  benefit?: string;
  advantage?: string;
}

export interface FABAnalysis {
  feature: string;
  advantage: string;
  benefit: string;
}

// Legacy MVPFeatures structure
export interface MVPFeatures {
  must_haves: Feature[];
  nice_to_haves: NiceToHave[];
  must_haves_fab_analysis: FABAnalysis[];
  nice_to_haves_fab_analysis: FABAnalysis[];
}

// New format for must-have features wrapper (A4 template)
export interface MustHaveFeatures {
  features: MustHaveFeature[];
  section_description?: string;
}

// New format for nice-to-have features wrapper (A4 template)
export interface NiceToHaveFeatures {
  features: NiceToHaveFeature[];
  section_description?: string;
}

export interface PrimaryPersona {
  name: string;
  description: string;
  segment?: string;
  primary_job: {
    job_type: string;
    job_statement: string;
  };
  primary_jtbd?: string;
  key_pains?: string[];
  desired_gains?: string[];
}

export interface QualitativeSignal {
  signal_name: string;
  description: string;
  collection_method: string;
}

export interface QuantitativeSignal {
  metric_name: string;
  description: string;
  measurement_method: string;
  target: string;
}

export interface SuccessSignals {
  qualitative: QualitativeSignal[];
  quantitative: QuantitativeSignal[];
}

export interface AutomationLevel {
  ai_features: Array<{
    feature_name: string;
    description: string;
    confidence: string;
  }>;
  manual_processes: Array<{
    process_name: string;
    reason_for_manual: string;
  }>;
  automated_processes: Array<{
    process_name: string;
    automation_type: string;
    fallback_if_fails: string;
  }>;
}

export interface PlatformChoices {
  primary_platform: string;
  access_method: string;
  platform_rationale: string;
  mobile_considerations: string;
}

export interface UserInput {
  field_name: string;
  field_type: string;
  is_required: boolean;
  purpose: string;
}

export interface SystemOutput {
  output_name: string;
  output_type: string;
  description: string;
}

export interface DataRequirements {
  user_inputs: UserInput[];
  system_outputs: SystemOutput[];
}

export interface Workflow {
  workflow_name: string;
  description: string;
  is_must_have: boolean;
  value_delivered: string;
  steps: string[];
}

// New format for critical workflows wrapper (A4 template)
export interface CriticalWorkflows {
  workflows: Workflow[];
  section_description?: string;
}

export interface SourceArtifacts {
  bmc_version: string;
  vpc_version: string;
  vps_version: string;
  critique_used: boolean;
}

// Production QC Interface
export interface ProductionQC {
  lead_time: string;
  quality_controls: string[];
  batch_size_initial: string;
  production_partner: string;
  manufacturing_approach: string;
}

// Consumer Use Case Interface
export interface ConsumerUseCase {
  usage_frequency: string;
  product_category: string;
  purchase_occasion: string;
  consumption_context: string;
  competing_alternatives: string[];
}

// Packaging Formats Interface
export interface SKUVariant {
  size: string;
  target_price: string;
  variant_name: string;
}

export interface PrimaryPackaging {
  size: string;
  format: string;
  material: string;
}

export interface PackagingFormats {
  sku_variants: SKUVariant[];
  primary_packaging: PrimaryPackaging;
  labeling_requirements: string[];
}

// Regulatory Safety Interface
export interface RegulatorySafety {
  safety_testing: string[];
  regulatory_bodies: string[];
  compliance_timeline: string;
  certifications_required: string[];
}

// Product Composition Interface
export interface ProductComposition {
  shelf_life: string;
  key_ingredients: string[];
  quality_attributes: string[];
  formulation_approach: string;
}

// Distribution Channels Interface
export interface DistributionChannel {
  channel_name: string;
  channel_type: string;
  geographic_coverage: string;
}

export interface DistributionChannels {
  route_to_market: string;
  primary_channels: DistributionChannel[];
  distribution_partners: string[];
}

export interface PRDJson {
  scope: Scope;
  purpose: Purpose;
  objective: Objective;
  // Legacy format
  mvp_features?: MVPFeatures;
  // New format (A4 template)
  must_have_features?: MustHaveFeatures;
  nice_to_have_features?: NiceToHaveFeatures;
  primary_persona: PrimaryPersona;
  success_signals?: SuccessSignals;
  automation_level?: AutomationLevel;
  platform_choices?: PlatformChoices;
  data_requirements?: DataRequirements;
  // Legacy format (array)
  critical_workflows?: Workflow[] | CriticalWorkflows;
  source_artifacts_used?: SourceArtifacts;
  // New fields for C1 template
  production_qc?: ProductionQC;
  consumer_use_case?: ConsumerUseCase;
  packaging_formats?: PackagingFormats;
  regulatory_safety?: RegulatorySafety;
  product_composition?: ProductComposition;
  distribution_channels?: DistributionChannels;
  template_code: string;
  template_version: string;
  schema_version: string;
  generated_at: string;
}

export interface PRDResponse {
  success: boolean;
  run_id: string;
  project_id: string;
  status: string;
  prd_json: PRDJson;
  prd_metadata: PRDMetadata;
  validation_status: string;
  validation_warnings: string[];
  version: number;
  completed_at: string;
}

interface UsePRDOptions {
  projectId: string;
  onAuthError?: () => void;
}

export function usePRD({ projectId, onAuthError }: UsePRDOptions) {
  const router = useRouter();
  const { token } = useAuthStore();

  // Use ref to track token to avoid infinite loops
  const tokenRef = useRef(token);
  const hasFetchedRef = useRef(false);

  // Update token ref when token changes
  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  const [isLoading, setIsLoading] = useState(true);
  const [prdData, setPrdData] = useState<PRDResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Fetch PRD data
  const fetchPRDData = useCallback(async () => {
    if (!projectId) {
      setError("Project ID is missing");
      setIsLoading(false);
      return;
    }

    // Get current token from ref
    const currentToken = tokenRef.current;

    try {
      setIsLoading(true);
      setError(null);

      if (!currentToken) {
        toast.error("Authentication required");
        if (onAuthError) {
          onAuthError();
        } else {
          router.push("/signin");
        }
        setIsLoading(false);
        return;
      }

      const API_URL = process.env.NEXT_PUBLIC_API_URL;

      if (process.env.NODE_ENV === "development") {
        console.log("🔄 Fetching PRD for project:", projectId);
      }

      const response = await fetch(`${API_URL}/mvp/projects/${projectId}/amrg/results`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("No Product Requirements Found for this project");
        } else if (response.status === 401) {
          toast.error("Session expired. Please login again.");
          if (onAuthError) {
            onAuthError();
          } else {
            router.push("/signin");
          }
          return;
        }
        throw new Error(`Failed to fetch PRD: ${response.statusText}`);
      }

      const data: PRDResponse = await response.json();

      if (process.env.NODE_ENV === "development") {
        console.log("✅ PRD data received:", data.success);
        console.log("📦 Full PRD Response:", data);
        console.log("📋 PRD JSON keys:", data.prd_json ? Object.keys(data.prd_json) : 'No prd_json');
        console.log("🏭 C1 Template Fields:", {
          production_qc: data.prd_json?.production_qc ? 'Present' : 'Missing',
          consumer_use_case: data.prd_json?.consumer_use_case ? 'Present' : 'Missing',
          packaging_formats: data.prd_json?.packaging_formats ? 'Present' : 'Missing',
          regulatory_safety: data.prd_json?.regulatory_safety ? 'Present' : 'Missing',
          product_composition: data.prd_json?.product_composition ? 'Present' : 'Missing',
          distribution_channels: data.prd_json?.distribution_channels ? 'Present' : 'Missing',
        });
      }

      if (data.success) {
        setPrdData(data);
        hasFetchedRef.current = true;
      } else {
        throw new Error("Failed to load PRD data");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load PRD";
      setError(errorMessage);
      toast.error(errorMessage);

      if (process.env.NODE_ENV === "development") {
        console.error("❌ Error fetching PRD:", err);
      }
    } finally {
      setIsLoading(false);
    }
  }, [projectId, router, onAuthError]);

  // ReGenerate PR
  const regeneratePRD = useCallback(async () => {
    setIsRegenerating(true);
    try {
      // TODO: Implement actual regenerate API call
      await fetchPRDData();
      toast.success("PRD regenerated successfully");
    } catch (err) {
      toast.error("Failed to reGenerate PR");
    } finally {
      setIsRegenerating(false);
    }
  }, [fetchPRDData]);

  // Save PRD changes
  const savePRDChanges = useCallback(async (updatedData: Partial<PRDJson>) => {
    const currentToken = tokenRef.current;

    setIsSaving(true);
    try {
      if (!currentToken) {
        toast.error("Authentication required");
        return false;
      }

      const API_URL = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${API_URL}/mvp/projects/${projectId}/amrg/results`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify(updatedData),
      });

      if (!response.ok) {
        throw new Error(`Failed to save PRD: ${response.statusText}`);
      }

      toast.success("Changes saved successfully");
      await fetchPRDData();
      return true;
    } catch (err) {
      toast.error("Failed to save changes");
      if (process.env.NODE_ENV === "development") {
        console.error("❌ Error saving PRD:", err);
      }
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [projectId, fetchPRDData]);

  return {
    // State
    isLoading,
    prdData,
    error,
    isRegenerating,
    isSaving,
    // Actions
    fetchPRDData,
    regeneratePRD,
    savePRDChanges,
    setPrdData,
  };
}
