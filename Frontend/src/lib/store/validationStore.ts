import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ValidationStore, MarketValidationData } from '@/types/validation';

export const useValidationStore = create<ValidationStore>()(
  persist(
    (set, get) => ({
      userId: '',
      sessionId: null,
      validationData: null,
      currentAnswers: {},

      setUserId: (id: string) => set({ userId: id }),

      setSessionId: (id: string) => set({ sessionId: id }),

      setValidationData: (data: MarketValidationData) => 
        set({ validationData: data }),

      setAnswer: (questionId: string, answer: string) => 
        set((state) => ({
          currentAnswers: {
            ...state.currentAnswers,
            [questionId]: answer,
          },
        })),

      clearAnswers: () => set({ currentAnswers: {} }),

      reset: () => set({
        userId: get().userId, // Keep userId but reset everything else
        sessionId: null,
        validationData: null,
        currentAnswers: {},
      }),
    }),
    {
      name: 'validation-store',
      partialize: (state) => ({
        userId: state.userId,
        sessionId: state.sessionId,
        validationData: state.validationData,
      }),
    }
  )
);
