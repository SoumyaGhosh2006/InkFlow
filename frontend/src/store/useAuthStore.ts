/**
 * InkFlow Authentication & Quota Zustand Store
 * Maintains user profile, subscription tier, and weekly word quota.
 */

import { create } from 'zustand';
import type { UserProfile } from '../types/api';
import { authApi } from '../lib/api';
import {
  signInWithGoogle,
  signOutUser,
  recordUserActivity,
  isSessionExpiredDueToInactivity,
} from '../lib/firebase';

interface AuthState {
  user: UserProfile | null;
  isLoading: boolean;
  error: string | null;
  isAuthModalOpen: boolean;
  authModalReason: string;
  openAuthModal: (reason?: string) => void;
  closeAuthModal: () => void;
  isAuthenticated: () => boolean;
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
  isAuthModalOpen: false,
  authModalReason: 'Sign in to access your Style Genome and start humanizing text.',

  openAuthModal: (reason) => {
    set({
      isAuthModalOpen: true,
      authModalReason: reason || 'Sign in to access your Style Genome and start humanizing text.',
    });
  },

  closeAuthModal: () => set({ isAuthModalOpen: false }),

  isAuthenticated: () => {
    const user = get().user;
    const token = localStorage.getItem('inkflow_token');
    if (!token || !user) return false;
    if (user.id === 'usr_local_dev') return false;
    return true;
  },

  fetchUser: async () => {
    if (isSessionExpiredDueToInactivity()) {
      await get().logout();
      return;
    }
    const token = localStorage.getItem('inkflow_token');
    if (!token) {
      set({ user: null, isLoading: false });
      return;
    }
    set({ isLoading: true, error: null });
    try {
      const user = await authApi.getMe();
      if (!user) {
        set({ user: null, isLoading: false });
        return;
      }
      recordUserActivity();
      set({ user, isLoading: false });
    } catch (err: any) {
      set({ user: null, error: err.message, isLoading: false });
    }
  },

  loginWithGoogle: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await signInWithGoogle();
      if (res && res.user) {
        recordUserActivity();
        // Immediate optimistic update with real Google credentials
        set({
          user: {
            id: res.user.uid,
            email: res.user.email || '',
            displayName: res.user.displayName || (res.user.email ? res.user.email.split('@')[0] : 'Author'),
            photoUrl: res.user.photoURL || undefined,
            tier: 'free',
            wordsUsedThisWeek: 0,
            weeklyWordLimit: 5000,
            lastWeekReset: new Date().toISOString(),
            streakDays: 1,
            is_active: true,
          },
          isAuthModalOpen: false,
        });
        const user = await authApi.sync({
          uid: res.user.uid,
          email: res.user.email,
          displayName: res.user.displayName,
          photoUrl: res.user.photoURL || undefined,
        });
        set({ user, isLoading: false, isAuthModalOpen: false });
      } else {
        set({ isLoading: false });
      }
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  logout: async () => {
    await signOutUser();
    set({ user: null, isAuthModalOpen: false });
  },

  updateWordsUsed: (delta: number) => {
    const current = get().user;
    if (!current) return;
    recordUserActivity();
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
