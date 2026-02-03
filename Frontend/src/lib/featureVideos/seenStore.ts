/**
 * Seen Feature Videos Store (Zustand)
 * Global cache for tracking which feature help videos have been seen
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { getSeenFeatureVideos, postSeenFeatureVideo, SeenSource } from './api';

const STORAGE_KEY = 'yuba.seenFeatureVideos.v1';

interface SeenFeatureVideosState {
  seenFeatureIds: Set<string>;
  isLoaded: boolean;
  isFetching: boolean;
  hasFetched: boolean;
}

interface SeenFeatureVideosActions {
  markSeenLocal: (featureId: string) => void;
  hydrateSeen: (featureIds: string[]) => void;
  fetchSeenOnce: () => Promise<void>;
  isSeen: (featureId: string) => boolean;
  markSeenAndPost: (featureId: string, source: SeenSource) => void;
}

type SeenFeatureVideosStore = SeenFeatureVideosState & SeenFeatureVideosActions;

export const useSeenFeatureVideosStore = create<SeenFeatureVideosStore>()(
  persist(
    (set, get) => ({
      seenFeatureIds: new Set<string>(),
      isLoaded: false,
      isFetching: false,
      hasFetched: false,

      markSeenLocal: (featureId: string) => {
        set((state) => {
          const newSet = new Set(state.seenFeatureIds);
          newSet.add(featureId);
          return { seenFeatureIds: newSet };
        });
      },

      hydrateSeen: (featureIds: string[]) => {
        set({
          seenFeatureIds: new Set(featureIds),
          isLoaded: true,
        });
      },

      fetchSeenOnce: async () => {
        const { hasFetched, isFetching } = get();
        
        if (hasFetched || isFetching) {
          if (process.env.NODE_ENV === 'development') {
            console.log('[SeenStore] Skipping fetch - already fetched or fetching');
          }
          return;
        }

        set({ isFetching: true });

        try {
          const seenList = await getSeenFeatureVideos();
          
          set((state) => {
            const mergedSet = new Set([...state.seenFeatureIds, ...seenList]);
            return {
              seenFeatureIds: mergedSet,
              isLoaded: true,
              isFetching: false,
              hasFetched: true,
            };
          });

          if (process.env.NODE_ENV === 'development') {
            console.log('[SeenStore] Fetched and merged seen features:', seenList);
          }
        } catch (error) {
          if (process.env.NODE_ENV === 'development') {
            console.error('[SeenStore] Error fetching seen features:', error);
          }
          set({
            isFetching: false,
            hasFetched: true,
            isLoaded: true,
          });
        }
      },

      isSeen: (featureId: string) => {
        return get().seenFeatureIds.has(featureId);
      },

      markSeenAndPost: (featureId: string, source: SeenSource) => {
        const { seenFeatureIds, markSeenLocal } = get();
        
        if (seenFeatureIds.has(featureId)) {
          if (process.env.NODE_ENV === 'development') {
            console.log('[SeenStore] Feature already seen, skipping POST:', featureId);
          }
          return;
        }

        markSeenLocal(featureId);
        
        postSeenFeatureVideo(featureId, source).catch((error) => {
          if (process.env.NODE_ENV === 'development') {
            console.error('[SeenStore] Failed to POST seen feature:', error);
          }
        });
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        seenFeatureIds: Array.from(state.seenFeatureIds),
      }),
      merge: (persistedState: any, currentState) => {
        const persisted = persistedState as { seenFeatureIds?: string[] } | undefined;
        return {
          ...currentState,
          seenFeatureIds: new Set(persisted?.seenFeatureIds || []),
          isLoaded: true,
        };
      },
      onRehydrateStorage: () => (state) => {
        if (process.env.NODE_ENV === 'development') {
          console.log('[SeenStore] Rehydrated from localStorage:', state?.seenFeatureIds);
        }
      },
    }
  )
);

export const useIsSeen = (featureId: string) => 
  useSeenFeatureVideosStore((state) => state.seenFeatureIds.has(featureId));

export const useIsSeenLoaded = () => 
  useSeenFeatureVideosStore((state) => state.isLoaded);
