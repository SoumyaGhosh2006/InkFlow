/**
 * Firebase Client Initialization & Authentication Helper
 */

import { initializeApp, getApps, type FirebaseApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  setPersistence,
  browserLocalPersistence,
  type Auth,
  type User,
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

// 1-Week Inactivity Timeout Constant (7 days in milliseconds)
export const INACTIVITY_TIMEOUT_MS = 7 * 24 * 60 * 60 * 1000;
export const LAST_ACTIVITY_KEY = 'inkflow_last_activity';

/**
 * Record user activity timestamp to localStorage, throttled.
 */
let lastLoggedActivity = 0;
export function recordUserActivity(): void {
  const now = Date.now();
  if (now - lastLoggedActivity > 30000) {
    lastLoggedActivity = now;
    if (localStorage.getItem('inkflow_token')) {
      localStorage.setItem(LAST_ACTIVITY_KEY, now.toString());
    }
  }
}

/**
 * Check if the active session has exceeded 1 week of complete inactivity.
 */
export function isSessionExpiredDueToInactivity(): boolean {
  const token = localStorage.getItem('inkflow_token');
  if (!token) return false;

  const lastActiveStr = localStorage.getItem(LAST_ACTIVITY_KEY);
  if (!lastActiveStr) {
    // If token exists but no timestamp was recorded yet, seed it now
    localStorage.setItem(LAST_ACTIVITY_KEY, Date.now().toString());
    return false;
  }

  const lastActive = parseInt(lastActiveStr, 10);
  if (isNaN(lastActive)) return false;

  return Date.now() - lastActive > INACTIVITY_TIMEOUT_MS;
}

// Initialize Firebase only if API key is configured
let app: FirebaseApp | null = null;
let auth: Auth | null = null;
const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: 'select_account',
});

if (firebaseConfig.apiKey && firebaseConfig.projectId) {
  try {
    app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
    auth = getAuth(app);
    // Explicitly configure permanent local persistence (persists across browser restarts and tab sessions)
    setPersistence(auth, browserLocalPersistence).catch((err) => {
      console.warn('Failed to configure browserLocalPersistence:', err);
    });
  } catch (err) {
    console.warn('Firebase initialization skipped or failed:', err);
  }
}

export { auth, googleProvider };

/**
 * Trigger Google Sign-In Popup, save ID token to localStorage, and return auth details
 */
export async function signInWithGoogle(): Promise<{ user: User; token: string } | null> {
  if (!auth) {
    alert('Firebase is not initialized. Please ensure your frontend/.env has valid Firebase keys.');
    return null;
  }

  try {
    const result = await signInWithPopup(auth, googleProvider);
    const token = await result.user.getIdToken();
    localStorage.setItem('inkflow_token', token);
    localStorage.setItem(LAST_ACTIVITY_KEY, Date.now().toString());
    return { user: result.user, token };
  } catch (err: any) {
    console.error('Google Sign-In error:', err);
    if (err.code === 'auth/popup-closed-by-user' || err.code === 'auth/cancelled-popup-request') {
      alert("Google Sign-In window closed.\n\nNOTE FOR BRAVE BROWSER: If you are using Brave, click the orange lion icon in the URL bar and toggle 'Shields DOWN' for localhost:3000, then try again.");
    } else if (err.code === 'auth/unauthorized-domain') {
      alert(`Domain unauthorized (${window.location.hostname}). Please add this domain to Firebase Console -> Authentication -> Settings -> Authorized Domains.`);
    } else if (err.code === 'auth/configuration-not-found') {
      alert('Google Sign-In is not enabled in Firebase Console. Go to Authentication -> Sign-in method -> Enable Google.');
    } else {
      alert(`Google Sign-In error (${err.code}): ${err.message}`);
    }
    throw err;
  }
}

/**
 * Sign out of Firebase and clear local token and activity tracking
 */
export async function signOutUser(): Promise<void> {
  if (auth) {
    await firebaseSignOut(auth);
  }
  localStorage.removeItem('inkflow_token');
  localStorage.removeItem(LAST_ACTIVITY_KEY);
}

/**
 * Subscribe to auth state transitions
 */
export function onAuthChange(callback: (user: User | null) => void) {
  if (!auth) {
    callback(null);
    return () => {};
  }
  return onAuthStateChanged(auth, callback);
}
