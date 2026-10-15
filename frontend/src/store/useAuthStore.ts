/**
 * InkFlow Authentication & Quota Zustand Store
 * Maintains user profile, subscription tier, and weekly word quota.
 */

import { create } from 'zustand';
import type { UserProfile } from '../types/api';
import { authApi } from '../lib/api';
import { signInWithGoogle, signOutUser } from '../lib/firebase';

interface AuthState {
  user: UserProfile | null;
  isLoading: boolean;
  error: string | null;
  fetchUser: () => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  updateWordsUsed: (delta: number) => void;
  setUserTier: (tier: 'free' | 'pro') => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isLoading: false,
  error: null,

  fetchUser: async () => {
    set({ isLoading: true, error: null });
    try {
      const user = await authApi.getMe();
      set({ user, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  loginWithGoogle: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await signInWithGoogle();
      if (res) {
        const user = await authApi.sync();
        set({ user, isLoading: false });
      } else {
        set({ isLoading: false });
      }
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  logout: async () => {
    await signOutUser();
    set({ user: null });
  },

  updateWordsUsed: (delta: number) => {
    const current = get().user;
    if (!current) return;
    set({
      user: {
        ...current,
        wordsUsedThisWeek: current.wordsUsedThisWeek + delta,
      },
    });
  },

  setUserTier: (tier: 'free' | 'pro') => {
    const current = get().user;
    if (!current) return;
    set({
      user: {
        ...current,
        tier,
      },
    });
  },
}));
