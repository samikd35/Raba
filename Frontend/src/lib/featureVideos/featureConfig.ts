/**
 * Feature Video Configuration
 * Maps feature IDs to their video config (youtubeId, resourcesHref, title)
 * 
 * TEMPORARY: All features use the same youtubeId "7kcUoAPEEUw"
 * Replace individual youtubeId values when unique videos are available
 */

import { FEATURE_IDS, FeatureId } from './featureIds';

export interface FeatureVideoConfig {
  youtubeId: string;
  resourcesHref: string;
  title: string;
}

const DEFAULT_YOUTUBE_ID = '7kcUoAPEEUw';
const PROFILE_YOUTUBE_ID = '1Jrr48Y6ft0';
const HYPOTHESIS_YOUTUBE_ID = 'jUvki-uR1Ck';
const QUESTIONNAIRES_YOUTUBE_ID = 'XyAd_GZK5u4';

export const FEATURE_VIDEO_CONFIG: Record<FeatureId, FeatureVideoConfig> = {
  [FEATURE_IDS.PROBLEM_EXPLORER]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#problem-explorer',
    title: 'Explainer: Problem Explorer',
  },
  [FEATURE_IDS.IDEA_REFINER]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#idea-refiner',
    title: 'Explainer: Idea Refiner',
  },
  [FEATURE_IDS.PROBLEM_VALIDATOR]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#problem-validator',
    title: 'Explainer: Problem Validator',
  },
  [FEATURE_IDS.PERSONAS]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#personas',
    title: 'Explainer: Personas',
  },
  [FEATURE_IDS.CUSTOMER_PROFILE]: {
    youtubeId: PROFILE_YOUTUBE_ID,
    resourcesHref: '/resources#customer-profile',
    title: 'Explainer: Customer Profile',
  },
  [FEATURE_IDS.VPC]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#vpc',
    title: 'Explainer: Value Proposition Canvas',
  },
  [FEATURE_IDS.HYPOTHESIS]: {
    youtubeId: HYPOTHESIS_YOUTUBE_ID,
    resourcesHref: '/resources#hypothesis',
    title: 'Explainer: Hypothesis & Assumptions',
  },
  [FEATURE_IDS.ASSUMPTIONS]: {
    youtubeId: HYPOTHESIS_YOUTUBE_ID,
    resourcesHref: '/resources#assumptions',
    title: 'Explainer: Hypothesis & Assumptions',
  },
  [FEATURE_IDS.QUESTIONNAIRES]: {
    youtubeId: QUESTIONNAIRES_YOUTUBE_ID,
    resourcesHref: '/resources#questionnaires',
    title: 'Explainer: Questionnaires',
  },
  [FEATURE_IDS.MARKET_RESEARCH_ANALYSIS]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#market-research-analysis',
    title: 'Explainer: Market Research Analysis',
  },
  [FEATURE_IDS.CUSTOMER_PROFILE_V2]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#customer-profile-v2',
    title: 'Explainer: Customer Profile V2',
  },
  [FEATURE_IDS.VALUE_MAP]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#value-map',
    title: 'Explainer: Value Map',
  },
  [FEATURE_IDS.VPC_V2]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#vpc-v2',
    title: 'Explainer: Value Proposition Canvas V2',
  },
  [FEATURE_IDS.MVP_BOOTSTRAP]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#mvp-bootstrap',
    title: 'Explainer: MVP Bootstrap',
  },
  [FEATURE_IDS.VPS]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#vps',
    title: 'Explainer: Value Proposition Statement',
  },
  [FEATURE_IDS.BMC]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#bmc',
    title: 'Explainer: Business Model Canvas',
  },
  [FEATURE_IDS.SOLUTION_CRITIC]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#solution-critic',
    title: 'Solution Critic',
  },
  [FEATURE_IDS.VPS_V2]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#vps-v2',
    title: 'Explainer: Value Proposition Statement V2',
  },
  [FEATURE_IDS.BMC_V2]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#bmc-v2',
    title: 'Explainer: Business Model Canvas V2',
  },
  [FEATURE_IDS.PRODUCT_REQUIREMENT]: {
    youtubeId: DEFAULT_YOUTUBE_ID,
    resourcesHref: '/resources#product-requirement',
    title: 'Explainer: Product Requirement',
  },
};

export function getFeatureVideoConfig(featureId: FeatureId): FeatureVideoConfig {
  return FEATURE_VIDEO_CONFIG[featureId];
}
