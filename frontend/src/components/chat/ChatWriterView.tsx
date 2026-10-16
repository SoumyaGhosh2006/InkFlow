/**
 * ChatWriterView Component
 * Standalone direct AI writing chatbox.
 *
 * Rationale:
 * Allows authors to directly compose emails, lecture notes, formal letters,
 * SMS messages, or paragraphs without needing external ChatGPT roundtrips.
 * Features 1-click "Send to Humanize" bridge to transfer drafts directly
 * into the Humanize Studio for stylistic refinement.
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Copy,
  Check,
  ArrowRight,
  Bot,
  User,
  Trash2,
  Mail,
  BookOpen,
  MessageSquare,
  FileText,
  Loader2,
  CornerDownLeft,
} from 'lucide-react';
import { chatApi } from '../../lib/api';
import { useStudioStore } from '../../store/useStudioStore';
import { useAuthStore } from '../../store/useAuthStore';
import type { ChatMessage } from '../../types/api';

interface QuickPrompt {
  label: string;
  icon: React.ElementType;
  context: string;
  template: string;
}

const QUICK_PROMPTS: QuickPrompt[] = [
  {
    label: 'Email',
    icon: Mail,
    context: 'email',
    template:
      'Write an email to: professor.smith@university.edu\nSubject: Request for extension on research paper\nKey details: Need 48 extra hours due to lab equipment delay; draft is 80% complete.\nTone: Respectful, clear, professional',
  },
  {
    label: 'Lecture Notes',
    icon: BookOpen,
    context: 'lecture_notes',
    template:
      'Create lecture notes on: Distributed Systems Consensus (Raft vs. Paxos)\nTarget audience: 3rd year CS undergrads\nFormat: Key principles, leader election, log replication, summary comparison',
  },
  {
    label: 'Direct Message / SMS',
    icon: MessageSquare,
    context: 'sms',
    template:
      'Write a concise Slack message to the team:\nUpdate on the backend release: database migration succeeded with zero downtime, testing checkout flow now.',
  },
  {
    label: 'Formal Letter',
    icon: FileText,
    context: 'letter',
    template:
      'Write a formal cover letter paragraph explaining why my background in full-stack engineering and distributed systems matches the Senior Engineer role.',
  },
];

export const ChatWriterView: React.FC = () => {
  const { transferToHumanize } = useStudioStore();
  const { updateWordsUsed } = useAuthStore();

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        '👋 Welcome to the **InkFlow AI Writer**!\n\nTell me what you need to write — whether it’s an **email** with specific recipient and sender details, **lecture notes**, a **formal letter**, an **SMS**, or a **full paragraph**.\n\nI’ll generate it cleanly without generic AI slop. When you’re satisfied, click **"Send to Humanize"** to fine-tune it in your personal voice.',
    },
  ]);

  const [input, setInput] = useState('');
  const [selectedContext, setSelectedContext] = useState<string>('email');
  const [selectedTone, setSelectedTone] = useState<string>('natural');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMessage: ChatMessage = { role: 'user', content: trimmed };
    const updatedMessages = [...messages, userMessage];

    setMessages(updatedMessages);
    setInput('');
    setIsLoading(true);

    try {
      const response = await chatApi.compose({
        prompt: trimmed,
        messages: updatedMessages,
        context: selectedContext,
        tone: selectedTone,
      });

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.reply,
      };
      setMessages([...updatedMessages, assistantMessage]);

      if (response.words_consumed) {
        updateWordsUsed(response.words_consumed);
      }
    } catch (err: any) {
      setMessages([
        ...updatedMessages,
        {
          role: 'assistant',
          content: `⚠️ Generation failed: ${err.message || 'Please check your connection and try again.'}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch {
      // clipboard failover
    }
  };

  const handleClear = () => {
    setMessages([
      {
        role: 'assistant',
        content:
          'Chat cleared. What would you like to draft next? Pick a starter template or describe your message below.',
      },
    ]);
  };

  const inputWordCount = input.trim().split(/\s+/).filter(Boolean).length;

  return (
    <div className="flex-1 flex flex-col h-full bg-surface select-text overflow-hidden">
      {/* Top Bar with Context Starters */}
      <div className="p-4 bg-surface border-b border-surface-border flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
            Quick Starters:
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            {QUICK_PROMPTS.map((qp) => {
              const Icon = qp.icon;
              return (
                <button
                  key={qp.label}
                  onClick={() => {
                    setInput(qp.template);
                    setSelectedContext(qp.context);
                    textareaRef.current?.focus();
                  }}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-surface-subtle hover:bg-stone-200/70 border border-surface-border text-xs text-ink-primary font-medium transition-all"
                >
                  <Icon className="w-3.5 h-3.5 text-accent-primary" />
                  <span>{qp.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleClear}
            title="Clear Chat History"
            className="flex items-center space-x-1 px-2.5 py-1.5 text-xs text-stone-500 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Clear Chat</span>
          </button>
        </div>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.map((msg, idx) => {
            const isUser = msg.role === 'user';
            const wordCount = msg.content.trim().split(/\s+/).filter(Boolean).length;

            return (
              <div
                key={idx}
                className={`flex items-start space-x-3 ${
                  isUser ? 'flex-row-reverse space-x-reverse' : 'flex-row'
                }`}
              >
                {/* Avatar Icon */}
                <div
                  className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    isUser
                      ? 'bg-ink-primary text-stone-100 shadow-xs'
                      : 'bg-amber-100 text-amber-900 border border-amber-300 shadow-xs'
                  }`}
                >
                  {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                {/* Bubble Container */}
                <div
                  className={`max-w-[85%] rounded-2xl p-4 transition-all ${
                    isUser
                      ? 'bg-stone-900 text-stone-100 shadow-xs rounded-tr-none'
                      : 'bg-canvas border border-surface-border shadow-subtle text-ink-primary rounded-tl-none'
                  }`}
                >
                  {/* Message Content */}
                  <div className="whitespace-pre-wrap leading-relaxed text-sm font-sans">
                    {msg.content}
                  </div>

                  {/* Actions for Assistant messages (exclude the initial greeting) */}
                  {!isUser && idx > 0 && (
                    <div className="mt-4 pt-3 border-t border-surface-border flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center space-x-2 text-[11px] text-ink-secondary font-mono">
                        <span>{wordCount} words</span>
                        <span>•</span>
                        <span className="text-emerald-700">Groq 120B</span>
                      </div>

                      <div className="flex items-center space-x-2">
                        {/* Copy button */}
                        <button
                          onClick={() => handleCopy(msg.content, idx)}
                          className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-surface border border-surface-border hover:bg-surface-subtle text-xs text-ink-secondary hover:text-ink-primary transition-all"
                          title="Copy to clipboard"
                        >
                          {copiedIndex === idx ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-600" />
                              <span className="text-emerald-600 font-medium">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>

                        {/* Direct Bridge to Humanize Studio */}
                        <button
                          onClick={() => transferToHumanize(msg.content)}
                          className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-accent-primary hover:bg-accent-hover text-stone-900 text-xs font-semibold shadow-xs transition-all cursor-pointer"
                          title="Transfer this draft into Humanize Studio to fine-tune with your voice genome"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Send to Humanize</span>
                          <ArrowRight className="w-3 h-3 ml-0.5" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Typing Indicator */}
          {isLoading && (
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-900 border border-amber-300 flex items-center justify-center flex-shrink-0 shadow-xs">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl rounded-tl-none bg-canvas border border-surface-border shadow-subtle flex items-center space-x-2 text-xs text-ink-secondary">
                <Loader2 className="w-4 h-4 animate-spin text-accent-primary" />
                <span>InkFlow is drafting your response (Groq 120B)...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Composer Dock */}
      <div className="p-4 bg-surface border-t border-surface-border">
        <div className="max-w-3xl mx-auto space-y-2">
          {/* Format & Tone controls */}
          <div className="flex flex-wrap items-center justify-between text-xs gap-2">
            <div className="flex items-center space-x-2">
              <span className="text-ink-secondary text-[11px] uppercase font-semibold">Format:</span>
              <select
                value={selectedContext}
                onChange={(e) => setSelectedContext(e.target.value)}
                className="px-2.5 py-1 bg-surface-subtle border border-surface-border rounded-lg text-ink-primary font-medium text-xs focus:outline-none focus:border-accent-primary"
              >
                <option value="email">Email (Sender, Subject, Body)</option>
                <option value="letter">Formal Letter</option>
                <option value="lecture_notes">Lecture Notes / Study Guide</option>
                <option value="sms">SMS / Direct Message</option>
                <option value="article">Paragraph / Article</option>
                <option value="general">General Text</option>
              </select>

              <span className="text-ink-secondary text-[11px] uppercase font-semibold ml-2">Tone:</span>
              <select
                value={selectedTone}
                onChange={(e) => setSelectedTone(e.target.value)}
                className="px-2.5 py-1 bg-surface-subtle border border-surface-border rounded-lg text-ink-primary font-medium text-xs focus:outline-none focus:border-accent-primary"
              >
                <option value="natural">Natural & Authentic</option>
                <option value="professional">Professional Formal</option>
                <option value="academic">Academic & Precise</option>
                <option value="concise">Punchy & Direct</option>
                <option value="friendly">Warm & Cordial</option>
              </select>
            </div>

            <div className="text-[11px] font-mono text-ink-secondary">
              {inputWordCount} / 1,000 words
            </div>
          </div>

          {/* Textarea + Action Button */}
          <div className="relative flex items-end bg-canvas rounded-2xl border border-surface-border focus-within:ring-2 focus-within:ring-accent-primary/20 focus-within:border-accent-primary transition-all p-2 shadow-xs">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe what you want to write (e.g. sender email, recipient, main message, key points)..."
              rows={3}
              className="w-full p-2 bg-transparent text-sm text-ink-primary placeholder:text-stone-400 focus:outline-none resize-none leading-relaxed"
            />

            <div className="flex items-center space-x-2 pl-2 pb-1">
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim() || inputWordCount > 1000}
                className="px-4 py-2 bg-accent-primary hover:bg-accent-hover disabled:bg-stone-200 disabled:text-stone-400 disabled:cursor-not-allowed text-stone-900 rounded-xl font-semibold text-xs flex items-center space-x-1.5 shadow-xs transition-all cursor-pointer"
              >
                {isLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <>
                    <span>Generate</span>
                    <CornerDownLeft className="w-3 h-3" />
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-stone-400 px-1">
            <span>Press <kbd className="px-1 py-0.5 bg-stone-100 border border-stone-300 rounded font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1 py-0.5 bg-stone-100 border border-stone-300 rounded font-mono text-[10px]">Shift+Enter</kbd> for new line</span>
            <span>Resets Daily (00:00 UTC)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
