/**
 * UpgradeModal Component
 * Plan comparison table and Razorpay checkout launcher.
 *
 * Rationale:
 * Adheres to docs/frontend.md Section 3 View 4 and docs/backend.md Section 5:
 * Integrates with Razorpay Checkout JS SDK for UPI, card, and netbanking,
 * calling POST /api/v1/payments/create-order and /verify.
 */

import React, { useState, useEffect } from 'react';
import confetti from 'canvas-confetti';
import { Crown, Check, X, Shield, Sparkles, Loader2, CreditCard } from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';
import { useStudioStore } from '../../store/useStudioStore';
import { paymentsApi } from '../../lib/api';

declare global {
  interface Window {
    Razorpay?: any;
  }
}

export const UpgradeModal: React.FC = () => {
  const { isPricingModalOpen, setPricingModalOpen, activeView, setActiveView } = useStudioStore();
  const { user, setUserTier, loginWithGoogle } = useAuthStore();
  const [isProcessing, setIsProcessing] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleClose = React.useCallback(() => {
    setPricingModalOpen(false);
    if (activeView === 'pricing') {
      setActiveView('studio');
    }
  }, [activeView, setPricingModalOpen, setActiveView]);

  useEffect(() => {
    if (!isPricingModalOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isPricingModalOpen, handleClose]);

  if (!isPricingModalOpen) return null;

  const isAlreadyPro = user?.tier === 'pro';
  const isAnonymous =
    !user ||
    (user.id === 'usr_local_dev' && (!user.email || user.email === 'author@inkflow.tech'));

  const handleLaunchCheckout = async () => {
    setIsProcessing(true);
    setSuccessMessage(null);

    // If user is not logged in, trigger Google Sign-In first
    if (isAnonymous) {
      try {
        await loginWithGoogle();
        const activeUser = useAuthStore.getState().user;
        if (
          !activeUser ||
          (activeUser.id === 'usr_local_dev' &&
            (!activeUser.email || activeUser.email === 'author@inkflow.tech'))
        ) {
          setIsProcessing(false);
          return;
        }
      } catch (err) {
        setIsProcessing(false);
        return;
      }
    }

    try {
      // 1. Create order on backend
      const order = await paymentsApi.createOrder('pro_monthly');

      // 2. If Razorpay JS SDK is loaded in window
      if (typeof window.Razorpay === 'function') {
        const activeUser = useAuthStore.getState().user;
        const options: any = {
          key: order.key_id || 'rzp_test_inkflow',
          amount: order.amount,
          currency: order.currency || 'INR',
          name: 'InkFlow Pro',
          description: 'Unlimited Adaptive Rewrites & Multi-Context Genomes',
          handler: async (response: any) => {
            try {
              await paymentsApi.verify({
                razorpay_order_id: response.razorpay_order_id || order.order_id,
                razorpay_payment_id: response.razorpay_payment_id || `pay_${Date.now()}`,
                razorpay_signature: response.razorpay_signature || 'demo_signature',
              });

              setUserTier('pro');
              setSuccessMessage('Welcome to InkFlow Pro! Your account has been upgraded.');
              confetti({ particleCount: 90, spread: 70, origin: { y: 0.6 } });
            } catch (err: any) {
              console.error('Payment verification failed:', err);
              alert('Payment verification failed on server.');
            } finally {
              setIsProcessing(false);
            }
          },
          prefill: {
            name: activeUser?.displayName || 'InkFlow Author',
            email: activeUser?.email || 'author@inkflow.tech',
          },
          theme: {
            color: '#F59E0B',
          },
          modal: {
            ondismiss: () => {
              setIsProcessing(false);
            },
          },
        };

        if (order.order_id && !order.order_id.includes('_usr_') && !order.order_id.includes('demo')) {
          options.order_id = order.order_id;
        }

        const rzpInstance = new window.Razorpay(options);
        rzpInstance.on('payment.failed', (response: any) => {
          console.error('Razorpay payment failed:', response.error);
          setIsProcessing(false);
        });
        rzpInstance.open();
      } else {
        // Fallback for sandboxed preview if external checkout.js is blocked
        console.info('Simulating sandbox verification...');
        await paymentsApi.verify({
          razorpay_order_id: order.order_id,
          razorpay_payment_id: `pay_mock_${Date.now()}`,
          razorpay_signature: 'mock_signature',
        });
        setUserTier('pro');
        setSuccessMessage('Upgraded to Pro in test sandbox mode!');
        confetti({ particleCount: 90, spread: 70, origin: { y: 0.6 } });
        setIsProcessing(false);
      }
    } catch (err: any) {
      console.error('Checkout error:', err);
      alert(`Checkout failed: ${err.message || 'Check backend connection'}`);
      setIsProcessing(false);
    }
  };

  return (
    <div
      onClick={handleClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl bg-surface rounded-3xl border border-surface-border shadow-panel p-8 space-y-6 animate-in zoom-in-95 duration-200 relative"
      >
        {/* Close Button */}
        <button
          onClick={handleClose}
          aria-label="Close modal"
          className="absolute top-6 right-6 p-2 rounded-full text-stone-400 hover:text-ink-primary hover:bg-surface-subtle transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-amber-50 text-accent-primary flex items-center justify-center border border-amber-200/80 shadow-xs">
            <Crown className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-serif font-medium text-ink-primary">
            Upgrade to InkFlow Pro
          </h2>
          <p className="text-xs text-ink-secondary max-w-sm mx-auto">
            Unlimited writing passes, multi-context genome profiles, and dedicated Groq 120B reasoning.
          </p>
        </div>

        {/* Success Alert */}
        {successMessage && (
          <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs font-medium flex items-center space-x-2">
            <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Comparison Table */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Free Tier Card */}
          <div className="p-5 rounded-2xl bg-canvas border border-surface-border space-y-4 flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-ink-primary">Free Tier</h3>
                <span className="text-xs font-mono font-bold text-stone-500">$0 / mo</span>
              </div>
              <p className="text-xs text-ink-secondary">
                For occasional drafting and trying out your Style Genome twin.
              </p>

              <ul className="space-y-2 pt-2 text-xs text-ink-primary">
                <li className="flex items-center space-x-2">
                  <Check className="w-3.5 h-3.5 text-stone-500" />
                  <span>2,500 words per week</span>
                </li>
                <li className="flex items-center space-x-2">
                  <Check className="w-3.5 h-3.5 text-stone-500" />
                  <span>Resets Monday 00:00 UTC</span>
                </li>
                <li className="flex items-center space-x-2">
                  <Check className="w-3.5 h-3.5 text-stone-500" />
                  <span>1 Style Genome profile</span>
                </li>
                <li className="flex items-center space-x-2">
                  <Check className="w-3.5 h-3.5 text-stone-500" />
                  <span>Character-level punctuation diffs</span>
                </li>
              </ul>
            </div>

            <div className="pt-4 border-t border-stone-200">
              <span className="text-xs font-semibold text-stone-500 block text-center">
                Current Plan
              </span>
            </div>
          </div>

          {/* Pro Tier Card */}
          <div className="p-5 rounded-2xl bg-gradient-to-b from-amber-50/60 to-white border-2 border-accent-primary/60 space-y-4 flex flex-col justify-between shadow-subtle relative">
            <span className="absolute -top-2.5 right-6 px-2.5 py-0.5 rounded-full bg-accent-primary text-stone-900 text-[10px] font-bold uppercase tracking-wider shadow-xs">
              Recommended
            </span>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-amber-950 flex items-center space-x-1.5">
                  <Sparkles className="w-4 h-4 text-accent-primary" />
                  <span>InkFlow Pro</span>
                </h3>
                <span className="text-sm font-mono font-bold text-amber-950">₹499 / mo</span>
              </div>
              <p className="text-xs text-amber-900/80">
                For researchers, academics, and professionals who write daily.
              </p>

              <ul className="space-y-2 pt-2 text-xs text-ink-primary">
                <li className="flex items-center space-x-2 font-medium">
                  <Check className="w-3.5 h-3.5 text-accent-primary" />
                  <span>Unlimited words (no weekly limits)</span>
                </li>
                <li className="flex items-center space-x-2">
                  <Check className="w-3.5 h-3.5 text-accent-primary" />
                  <span>Multi-context profiles (Work, Academic, Chat)</span>
                </li>
                <li className="flex items-center space-x-2">
                  <Check className="w-3.5 h-3.5 text-accent-primary" />
                  <span>Dedicated Groq 120B reasoning tier</span>
                </li>
                <li className="flex items-center space-x-2">
                  <Check className="w-3.5 h-3.5 text-accent-primary" />
                  <span>Complete zero-training data sovereignty</span>
                </li>
              </ul>
            </div>

            <div className="pt-4 border-t border-amber-200/60">
              <button
                onClick={handleLaunchCheckout}
                disabled={isProcessing || isAlreadyPro}
                className="w-full py-2.5 px-3 rounded-xl bg-accent-primary hover:bg-accent-hover disabled:bg-stone-300 text-stone-900 font-semibold text-xs flex items-center justify-center space-x-1.5 shadow-sm transition-all cursor-pointer"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>{isAnonymous ? 'Signing in with Google...' : 'Opening Razorpay Checkout...'}</span>
                  </>
                ) : isAlreadyPro ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Already Subscribed</span>
                  </>
                ) : isAnonymous ? (
                  <>
                    <CreditCard className="w-3.5 h-3.5" />
                    <span>Sign In with Google to Upgrade (₹499)</span>
                  </>
                ) : (
                  <>
                    <CreditCard className="w-3.5 h-3.5" />
                    <span>Upgrade with Razorpay (₹499)</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Security & Refund Guarantee */}
        <div className="flex items-center justify-center space-x-2 text-[11px] text-ink-secondary pt-2">
          <Shield className="w-3.5 h-3.5 text-stone-400" />
          <span>Supports UPI, Cards, Netbanking via Razorpay. Cancel anytime.</span>
        </div>
      </div>
    </div>
  );
};
