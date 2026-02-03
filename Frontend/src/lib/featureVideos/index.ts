/**
 * Feature Videos Module - Public Exports
 */

export { FEATURE_IDS, ALL_FEATURE_IDS, isValidFeatureId } from './featureIds';
export type { FeatureId } from './featureIds';

export { FEATURE_VIDEO_CONFIG, getFeatureVideoConfig } from './featureConfig';
export type { FeatureVideoConfig } from './featureConfig';

export { getSeenFeatureVideos, postSeenFeatureVideo } from './api';
export type { SeenSource, SeenFeaturesResponse, MarkSeenRequest } from './api';

export { 
  useSeenFeatureVideosStore, 
  useIsSeen, 
  useIsSeenLoaded 
} from './seenStore';
