"use client";

import React from 'react';
import { Card } from '@/components/ui/card';
import {
  FileText,
  AlertCircle,
  Users,
  Target,
  CheckCircle2,
  Layers,
  Workflow,
} from 'lucide-react';
import { PRDData, PRDJson } from '@/types/organization';

interface ProductRequirementSectionProps {
  prdData: PRDData | null;
  readOnly?: boolean;
  embedded?: boolean;
}

/**
 * Product Requirement Section Component
 * Displays the Product Requirement Document in an embedded format
 * for the member project detail page.
 */
export const ProductRequirementSection: React.FC<ProductRequirementSectionProps> = ({
  prdData,
  readOnly = true,
  embedded = true,
}) => {
  // Handle empty/null state
  if (!prdData || !prdData.prd_json) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
        <p className="text-lg font-medium">No PRD Data Available</p>
        <p className="text-sm">Product Requirement Document will appear here once generated.</p>
      </div>
    );
  }

  const prd_json = prdData.prd_json;

  return (
    <div className="space-y-6">
      {/* Document Title */}
      <h2 className="text-3xl font-bold text-brand-500 dark:text-brand-200 pb-2 leading-tight border-b border-gray-200 dark:border-gray-700">
        Product Requirement Document
      </h2>

      {/* 1. Purpose & Problem Statement */}
      <section className="space-y-3">
        <h3 className="text-xl font-bold text-brand-500 dark:text-brand-400 flex items-center gap-2">
          <Target className="w-5 h-5" />
          1. Purpose & Problem Statement
        </h3>
        <Card className="p-4 bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700">
          <div className="text-gray-700 dark:text-gray-300 leading-relaxed space-y-3">
            {(prd_json.purpose?.statement || prd_json.purpose?.purpose_statement) && (
              <p>
                <strong className="text-brand-500 dark:text-brand-400">Purpose Statement:</strong>{' '}
                {prd_json.purpose.statement || prd_json.purpose.purpose_statement}
              </p>
            )}
            {prd_json.purpose?.target_persona && (
              <p>
                <strong className="text-brand-500 dark:text-brand-400">Target Persona:</strong>{' '}
                {prd_json.purpose.target_persona}
              </p>
            )}
            {prd_json.purpose?.validated_problem && (
              <p>
                <strong className="text-brand-500 dark:text-brand-400">Validated Problem:</strong>{' '}
                {prd_json.purpose.validated_problem}
              </p>
            )}
          </div>
        </Card>
      </section>

      {/* 2. Primary Persona */}
      {prd_json.primary_persona && (
        <section className="space-y-3">
          <h3 className="text-xl font-bold text-brand-500 dark:text-brand-400 flex items-center gap-2">
            <Users className="w-5 h-5" />
            2. Primary Persona
          </h3>
          <Card className="p-4 bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700">
            <div className="text-gray-700 dark:text-gray-300 leading-relaxed space-y-3">
              <p>
                <strong className="text-brand-500 dark:text-brand-400">Persona:</strong>{' '}
                {prd_json.primary_persona.name || prd_json.primary_persona.persona_name}
              </p>
              {prd_json.primary_persona.description && (
                <p>
                  <strong className="text-brand-500 dark:text-brand-400">Description:</strong>{' '}
                  {prd_json.primary_persona.description}
                </p>
              )}
              {prd_json.primary_persona.segment && (
                <p>
                  <strong className="text-brand-500 dark:text-brand-400">Segment:</strong>{' '}
                  {prd_json.primary_persona.segment}
                </p>
              )}
              {prd_json.primary_persona.primary_job?.job_statement && (
                <p>
                  <strong className="text-brand-500 dark:text-brand-400">Primary Job:</strong>{' '}
                  {prd_json.primary_persona.primary_job.job_statement}
                </p>
              )}
              {prd_json.primary_persona.primary_jtbd && (
                <p>
                  <strong className="text-brand-500 dark:text-brand-400">Primary Job-to-be-Done:</strong>{' '}
                  {prd_json.primary_persona.primary_jtbd}
                </p>
              )}

              {(prd_json.primary_persona.key_pains || []).length > 0 && (
                <div>
                  <p className="font-medium text-brand-500 dark:text-brand-400 mb-2">Key Pains:</p>
                  <ul className="list-disc list-outside pl-6 space-y-1">
                    {prd_json.primary_persona.key_pains?.map((pain: string, idx: number) => (
                      <li key={idx}>{pain}</li>
                    ))}
                  </ul>
                </div>
              )}

              {(prd_json.primary_persona.desired_gains || []).length > 0 && (
                <div>
                  <p className="font-medium text-brand-500 dark:text-brand-400 mb-2">Desired Gains:</p>
                  <ul className="list-disc list-outside pl-6 space-y-1">
                    {prd_json.primary_persona.desired_gains?.map((gain: string, idx: number) => (
                      <li key={idx}>{gain}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Card>
        </section>
      )}

      {/* 3. Scope */}
      {prd_json.scope && (
        <section className="space-y-3">
          <h3 className="text-xl font-bold text-brand-500 dark:text-brand-400 flex items-center gap-2">
            <Layers className="w-5 h-5" />
            3. Scope
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* In Scope */}
            <Card className="p-4 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
              <h4 className="font-semibold text-green-700 dark:text-green-400 mb-3">In Scope</h4>
              <div className="text-gray-700 dark:text-gray-300 space-y-2">
                {prd_json.scope.in_scope?.geography && (
                  <p><strong>Geography:</strong> {prd_json.scope.in_scope.geography}</p>
                )}
                {(prd_json.scope.in_scope?.user_segments || []).length > 0 && (
                  <div>
                    <p className="font-medium mb-1">User Segments:</p>
                    <ul className="list-disc list-outside pl-5 text-sm space-y-1">
                      {prd_json.scope.in_scope?.user_segments?.map((seg: string, idx: number) => (
                        <li key={idx}>{seg}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {(prd_json.scope.in_scope?.core_flows || []).length > 0 && (
                  <div>
                    <p className="font-medium mb-1">Core Flows:</p>
                    <ul className="list-disc list-outside pl-5 text-sm space-y-1">
                      {prd_json.scope.in_scope?.core_flows?.map((flow: string, idx: number) => (
                        <li key={idx}>{flow}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Card>

            {/* Out of Scope */}
            {(prd_json.scope.out_of_scope || []).length > 0 && (
              <Card className="p-4 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
                <h4 className="font-semibold text-red-700 dark:text-red-400 mb-3">Out of Scope</h4>
                <ul className="list-disc list-outside pl-5 text-gray-700 dark:text-gray-300 text-sm space-y-1">
                  {prd_json.scope.out_of_scope?.map((item: string, idx: number) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </Card>
            )}
          </div>
        </section>
      )}

      {/* 4. Objectives */}
      {prd_json.objective && (
        <section className="space-y-3">
          <h3 className="text-xl font-bold text-brand-500 dark:text-brand-400 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5" />
            4. Objectives
          </h3>
          <Card className="p-4 bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700">
            <div className="text-gray-700 dark:text-gray-300 leading-relaxed space-y-3">
              {prd_json.objective.primary_objective && (
                <p>
                  <strong className="text-brand-500 dark:text-brand-400">Primary Objective:</strong>{' '}
                  {prd_json.objective.primary_objective}
                </p>
              )}

              {(prd_json.objective.key_results || []).length > 0 && (
                <div>
                  <p className="font-medium text-brand-500 dark:text-brand-400 mb-2">Key Results:</p>
                  <ul className="list-decimal list-outside pl-6 space-y-1">
                    {prd_json.objective.key_results?.map((kr, idx: number) => (
                      <li key={idx}>
                        <strong>{kr.result}</strong> — Target: {kr.target}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(prd_json.objective.learning_goals || []).length > 0 && (
                <div>
                  <p className="font-medium text-brand-500 dark:text-brand-400 mb-2">Learning Goals:</p>
                  <ul className="list-disc list-outside pl-6 space-y-1">
                    {prd_json.objective.learning_goals?.map((goal: string, idx: number) => (
                      <li key={idx}>{goal}</li>
                    ))}
                  </ul>
                </div>
              )}

              {(prd_json.objective.success_criteria || []).length > 0 && (
                <div>
                  <p className="font-medium text-brand-500 dark:text-brand-400 mb-2">Success Criteria:</p>
                  <ul className="list-disc list-outside pl-6 space-y-1">
                    {prd_json.objective.success_criteria?.map((criteria: string, idx: number) => (
                      <li key={idx}>{criteria}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Card>
        </section>
      )}

      {/* 5. Must-Have Features */}
      {(prd_json.mvp_features?.must_haves || []).length > 0 && (
        <section className="space-y-3">
          <h3 className="text-xl font-bold text-brand-500 dark:text-brand-400 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5" />
            5. Must-Have Features
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-brand-50 dark:bg-brand-900/30">
                  <th className="text-left p-3 font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700">#</th>
                  <th className="text-left p-3 font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700">Feature Name</th>
                  <th className="text-left p-3 font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700">Description</th>
                  <th className="text-left p-3 font-semibold text-brand-600 dark:text-brand-400 border border-gray-200 dark:border-gray-700">Job Supported</th>
                </tr>
              </thead>
              <tbody>
                {prd_json.mvp_features?.must_haves?.map((feature, idx: number) => (
                  <tr key={idx} className="bg-white dark:bg-gray-800">
                    <td className="p-3 border border-gray-200 dark:border-gray-700">{idx + 1}</td>
                    <td className="p-3 border border-gray-200 dark:border-gray-700 font-medium">{feature.feature_name}</td>
                    <td className="p-3 border border-gray-200 dark:border-gray-700">{feature.description}</td>
                    <td className="p-3 border border-gray-200 dark:border-gray-700">{feature.job_supported}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 6. Nice-to-Have Features */}
      {(prd_json.mvp_features?.nice_to_haves || []).length > 0 && (
        <section className="space-y-3">
          <h3 className="text-xl font-bold text-brand-500 dark:text-brand-400">
            6. Nice-to-Have Features
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-gray-100 dark:bg-gray-800">
                  <th className="text-left p-3 font-semibold text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">#</th>
                  <th className="text-left p-3 font-semibold text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">Feature Name</th>
                  <th className="text-left p-3 font-semibold text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">Description</th>
                  <th className="text-left p-3 font-semibold text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">Rationale for Deferral</th>
                </tr>
              </thead>
              <tbody>
                {prd_json.mvp_features?.nice_to_haves?.map((feature, idx: number) => (
                  <tr key={idx} className="bg-white dark:bg-gray-800">
                    <td className="p-3 border border-gray-200 dark:border-gray-700">{idx + 1}</td>
                    <td className="p-3 border border-gray-200 dark:border-gray-700 font-medium">{feature.feature_name}</td>
                    <td className="p-3 border border-gray-200 dark:border-gray-700">{feature.description}</td>
                    <td className="p-3 border border-gray-200 dark:border-gray-700">{feature.rationale_for_deferral}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 7. Critical Workflows */}
      {(prd_json.critical_workflows || []).length > 0 && (
        <section className="space-y-3">
          <h3 className="text-xl font-bold text-brand-500 dark:text-brand-400 flex items-center gap-2">
            <Workflow className="w-5 h-5" />
            7. Critical Workflows
          </h3>
          <div className="space-y-4">
            {prd_json.critical_workflows?.map((workflow, idx: number) => (
              <Card key={idx} className="p-4 bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700">
                <h4 className="font-semibold text-brand-500 dark:text-brand-400 mb-2">
                  {workflow.workflow_name}
                  {workflow.is_must_have && (
                    <span className="ml-2 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded-full">
                      Must Have
                    </span>
                  )}
                </h4>
                {workflow.description && (
                  <p className="text-gray-700 dark:text-gray-300 mb-2">{workflow.description}</p>
                )}
                {workflow.value_delivered && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    <strong>Value Delivered:</strong> {workflow.value_delivered}
                  </p>
                )}
                {(workflow.steps || []).length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Steps:</p>
                    <ol className="list-decimal list-outside pl-5 text-sm text-gray-700 dark:text-gray-300 space-y-1">
                      {workflow.steps?.map((step: string, stepIdx: number) => (
                        <li key={stepIdx}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Metadata */}
      {prdData.prd_metadata?.generated_at && (
        <div className="flex items-center justify-center gap-4 text-xs text-gray-500 dark:text-gray-400 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-1">
            <FileText className="w-3 h-3" />
            Generated on {new Date(prdData.prd_metadata.generated_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </div>
          {prdData.version && (
            <div>Version: {prdData.version}</div>
          )}
        </div>
      )}
    </div>
  );
};

export default ProductRequirementSection;
