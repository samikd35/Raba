/**
 * Feature IDs for the Help Video Overlay system
 * Single source of truth for all feature identifiers
 */

export const FEATURE_IDS = {
  PROBLEM_EXPLORER: 'problem-explorer',
  IDEA_REFINER: 'idea-refiner',
  PROBLEM_VALIDATOR: 'problem-validator',
  PERSONAS: 'personas',
  CUSTOMER_PROFILE: 'customer-profile',
  VPC: 'vpc',
  HYPOTHESIS: 'hypothesis',
  ASSUMPTIONS: 'assumptions',
  QUESTIONNAIRES: 'questionnaires',
  MARKET_RESEARCH_ANALYSIS: 'market-research-analysis',
  CUSTOMER_PROFILE_V2: 'customer-profile-v2',
  VALUE_MAP: 'value-map',
  VPC_V2: 'vpc-v2',
  MVP_BOOTSTRAP: 'mvp-bootstrap',
  VPS: 'vps',
  BMC: 'bmc',
  SOLUTION_CRITIC: 'solution-critic',
  VPS_V2: 'vps-v2',
  BMC_V2: 'bmc-v2',
  PRODUCT_REQUIREMENT: 'product-requirement',
} as const;

export type FeatureId = typeof FEATURE_IDS[keyof typeof FEATURE_IDS];

export const ALL_FEATURE_IDS: readonly FeatureId[] = Object.values(FEATURE_IDS);

export function isValidFeatureId(value: string): value is FeatureId {
  return ALL_FEATURE_IDS.includes(value as FeatureId);
}
