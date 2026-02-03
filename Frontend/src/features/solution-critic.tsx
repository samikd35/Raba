/**
 * Solution Critic Feature
 * 
 * This file re-exports the modular Solution Critic component.
 * The component has been split into smaller, reusable pieces for better maintainability.
 * 
 * Structure:
 * - solution-critic/types.ts - TypeScript interfaces
 * - solution-critic/cache.ts - Caching utilities
 * - solution-critic/hooks/useSolutionCritic.ts - Custom hook for data management
 * - solution-critic/components/ - UI components
 *   - states/ - Loading, Error, Empty, Generating states
 *   - CitationText.tsx - Citation rendering
 *   - badges.tsx - Badge components
 *   - Header.tsx - Header with actions
 *   - CritiqueCard.tsx - Individual critique display
 *   - ResearchSources.tsx - Sources list
 * - solution-critic/SolutionCritic.tsx - Main component
 */

export { default } from './solution-critic/SolutionCritic';
export { default as SolutionCritic } from './solution-critic/SolutionCritic';
export * from './solution-critic/types';
