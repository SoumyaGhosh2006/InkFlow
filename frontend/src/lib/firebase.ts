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

// Initialize Firebase only if API key is configured
let app: FirebaseApp | null = null;
let auth: Auth | null = null;
const googleProvider = new GoogleAuthProvider();

if (firebaseConfig.apiKey && firebaseConfig.projectId) {
  try {
    app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
    auth = getAuth(app);
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
    console.warn('Firebase Auth is not initialized. Check frontend/.env');
    return null;
  }

  const result = await signInWithPopup(auth, googleProvider);
  const token = await result.user.getIdToken();
  localStorage.setItem('inkflow_token', token);
  return { user: result.user, token };
}

/**
 * Sign out of Firebase and clear local token
 */
export async function signOutUser(): Promise<void> {
  if (auth) {
    await firebaseSignOut(auth);
  }
  localStorage.removeItem('inkflow_token');
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
