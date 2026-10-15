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
googleProvider.setCustomParameters({
  prompt: 'select_account',
});

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
    alert('Firebase is not initialized. Please ensure your frontend/.env has valid Firebase keys.');
    return null;
  }

  try {
    const result = await signInWithPopup(auth, googleProvider);
    const token = await result.user.getIdToken();
    localStorage.setItem('inkflow_token', token);
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
