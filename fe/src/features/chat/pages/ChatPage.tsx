import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient, getInMemoryToken } from '@/services/apiClient';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  MessageSquare,
  Send,
  ThumbsUp,
  ThumbsDown,
  ShieldAlert,
  Loader2,
  BookMarked
} from 'lucide-react';
import toast from 'react-hot-toast';

interface Citation {
  source_id: string;
  source_name: string;
  chunk_text: string;
  score?: number;
}

interface Message {
  message_id: string;
  conversation_id: string;
  sender_type: 'USER' | 'ASSISTANT';
  content: string;
  citations: Citation[];
  feedback_score: number;
  created_at: string;
}

interface Conversation {
  conversation_id: string;
  company_id: string;
  user_identifier: string;
  status: 'OPEN' | 'ESCALATED' | 'RESOLVED';
  created_at: string;
}

export const ChatPage: React.FC = () => {
  const { activeCompanyId } = useAuth();
  
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  
  // Streaming states
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  // 1. Fetch Conversations
  const { data: conversations = [], isLoading: isConvsLoading, refetch: refetchConvs } = useQuery({
    queryKey: ['conversations', activeCompanyId],
    queryFn: async () => {
      if (!activeCompanyId) return [];
      const response = await apiClient.get(`/companies/${activeCompanyId}/conversations`);
      return response.data.data || [];
    },
    enabled: !!activeCompanyId,
  });

  // 2. Fetch Message History when selected conversation changes
  const fetchMessages = async (convId: string) => {
    try {
      const response = await apiClient.get(`/companies/${activeCompanyId}/conversations/${convId}/messages`);
      // Backend returns messages sorted by created_at DESC (due to pagination)
      // Reverse them to chronological order for chat list rendering
      const list = response.data.data || [];
      const chronological = [...list].reverse();
      setMessages(chronological);
      
      // Load citations from last message if assistant
      const lastMsg = chronological[chronological.length - 1];
      if (lastMsg && lastMsg.sender_type === 'ASSISTANT') {
        setActiveCitations(lastMsg.citations || []);
      } else {
        setActiveCitations([]);
      }
    } catch (err) {
      console.error(err);
      toast.error('Failed to load message history.');
    }
  };

  useEffect(() => {
    if (selectedConversationId) {
      fetchMessages(selectedConversationId);
      // Close previous ws if open
      if (wsRef.current) {
        wsRef.current.close();
      }
      connectWebSocket(selectedConversationId);
    } else {
      setMessages([]);
      setActiveCitations([]);
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [selectedConversationId]);

  // Scroll to bottom helper
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  // 3. Connect live WebSocket streaming route
  const connectWebSocket = (convId: string) => {
    const token = getInMemoryToken() || 'DummyTokenForTesting';
    const wsBaseUrl = 'ws://localhost:8001/api/v1/chat/ws';
    const wsUrl = `${wsBaseUrl}?token=${token}&company_id=${activeCompanyId}&conversation_id=${convId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected successfully.');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const { event: wsEvent, payload } = data;

        if (wsEvent === 'message.token') {
          setIsStreaming(true);
          setStreamingMessage((prev) => prev + payload.token);
        } else if (wsEvent === 'message.override') {
          setStreamingMessage(payload.content);
        } else if (wsEvent === 'message.completed') {
          setIsStreaming(false);
          setStreamingMessage('');
          
          // Refresh message history to render final database records (includes citations)
          fetchMessages(convId);
          refetchConvs();
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket closed.');
      setIsStreaming(false);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setIsStreaming(false);
    };
  };

  // 4. Action: Start New Conversation Session
  const handleStartConversation = async () => {
    if (!activeCompanyId) return;
    try {
      const userIdentifier = `Customer_${Math.random().toString(36).substring(2, 7)}`;
      const response = await apiClient.post(`/companies/${activeCompanyId}/conversations`, {
        user_identifier: userIdentifier,
      });
      toast.success('Started a new conversation playground session!');
      await refetchConvs();
      const newConvId = response.data.data.conversation_id;
      setSelectedConversationId(newConvId);
    } catch (err) {
      console.error(err);
      toast.error('Failed to start conversation.');
    }
  };

  // 5. Action: Send Message via WebSocket
  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || !selectedConversationId || !wsRef.current) return;

    if (wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error('WebSocket is disconnected. Reconnecting...');
      connectWebSocket(selectedConversationId);
      return;
    }

    // Append user message locally in UI for immediate feedback
    const tempUserMsg: Message = {
      message_id: Math.random().toString(),
      conversation_id: selectedConversationId,
      sender_type: 'USER',
      content: inputText,
      citations: [],
      feedback_score: 0,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    // Send payload
    wsRef.current.send(
      JSON.stringify({
        payload: {
          content: inputText,
        },
      })
    );

    setInputText('');
    setIsStreaming(true);
    setStreamingMessage('');
  };

  // 6. Action: Submit Feedback Rating
  const handleFeedback = async (messageId: string, score: number) => {
    if (!selectedConversationId) return;
    try {
      await apiClient.post(
        `/companies/${activeCompanyId}/conversations/${selectedConversationId}/messages/${messageId}/feedback`,
        {
          score,
        }
      );
      toast.success(score > 0 ? 'Marked as helpful!' : 'Feedback logged.');
      fetchMessages(selectedConversationId);
    } catch (err) {
      console.error(err);
      toast.error('Failed to submit feedback.');
    }
  };

  // 7. Action: Escalate Conversation Status
  const handleEscalate = async () => {
    if (!selectedConversationId) return;
    try {
      await apiClient.patch(
        `/companies/${activeCompanyId}/conversations/${selectedConversationId}/status`,
        {
          status: 'ESCALATED',
        }
      );
      toast.success('Conversation escalated to human agent.');
      refetchConvs();
    } catch (err) {
      console.error(err);
      toast.error('Failed to escalate conversation.');
    }
  };

  if (!activeCompanyId) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="No Company Selected"
        description="Select or create a company workspace to start chat conversations."
      />
    );
  }

  const activeConv = conversations.find((c: Conversation) => c.conversation_id === selectedConversationId);

  return (
    <div className="flex-1 flex gap-6 h-[calc(100vh-12rem)] min-h-[500px]">
      
      {/* Left Pane: Conversation List */}
      <div className="w-72 bg-card border border-border/80 rounded-xl flex flex-col overflow-hidden shrink-0">
        <div className="p-4 border-b border-border/40 flex flex-col gap-3">
          <Button onClick={handleStartConversation} className="w-full text-xs">
            + New Playground Session
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isConvsLoading ? (
            <div className="p-4 space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : conversations.length === 0 ? (
            <p className="text-center text-xs text-muted-foreground py-8">
              No playground sessions.
            </p>
          ) : (
            conversations.map((conv: Conversation) => (
              <button
                key={conv.conversation_id}
                onClick={() => setSelectedConversationId(conv.conversation_id)}
                className={`w-full text-left p-3 rounded-lg text-xs transition-all flex flex-col gap-1.5 ${
                  conv.conversation_id === selectedConversationId
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'hover:bg-accent border border-transparent'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold truncate">{conv.user_identifier}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border ${
                      conv.status === 'ESCALATED'
                        ? 'bg-amber-500/10 text-amber-500 border-amber-500/25'
                        : conv.status === 'RESOLVED'
                        ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/25'
                        : 'bg-primary/10 text-primary border-primary/25'
                    }`}
                  >
                    {conv.status}
                  </span>
                </div>
                <span className="text-[10px] text-muted-foreground">
                  Session: {new Date(conv.created_at).toLocaleTimeString()}
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Middle Pane: Chat Dialog Window */}
      <div className="flex-1 bg-card border border-border/80 rounded-xl flex flex-col overflow-hidden relative">
        {selectedConversationId ? (
          <>
            {/* Header info */}
            <div className="px-6 py-4 border-b border-border/40 flex items-center justify-between bg-muted/10 shrink-0">
              <div>
                <h4 className="text-sm font-semibold">
                  Active Session: {activeConv?.user_identifier}
                </h4>
                <p className="text-[10px] text-muted-foreground">
                  Live WebSocket hot-path streaming activated.
                </p>
              </div>
              <div className="flex gap-2">
                {activeConv?.status !== 'ESCALATED' && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-xs flex items-center gap-1 text-amber-500 border-amber-500/20 hover:bg-amber-500/10"
                    onClick={handleEscalate}
                  >
                    <ShieldAlert className="h-3.5 w-3.5" /> Escalate to Agent
                  </Button>
                )}
              </div>
            </div>

            {/* Scrollable messages container */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((msg: Message) => {
                const isUser = msg.sender_type === 'USER';
                return (
                  <div
                    key={msg.message_id}
                    className={`flex flex-col max-w-[75%] gap-1.5 ${
                      isUser ? 'ml-auto items-end' : 'mr-auto items-start'
                    }`}
                  >
                    <div
                      className={`px-4 py-3 rounded-xl text-sm leading-relaxed ${
                        isUser
                          ? 'bg-primary text-primary-foreground rounded-tr-none'
                          : 'bg-muted/40 border border-border/40 text-foreground rounded-tl-none'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>

                    {/* Meta info / ratings for Assistant */}
                    {!isUser && (
                      <div className="flex items-center gap-3 px-1">
                        <span className="text-[10px] text-muted-foreground">
                          {new Date(msg.created_at).toLocaleTimeString()}
                        </span>
                        
                        {/* Rating Buttons */}
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => handleFeedback(msg.message_id, 1)}
                            className={`p-1 rounded hover:bg-accent text-muted-foreground transition-all ${
                              msg.feedback_score > 0 ? 'text-emerald-500 bg-emerald-500/10' : ''
                            }`}
                          >
                            <ThumbsUp className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => handleFeedback(msg.message_id, -1)}
                            className={`p-1 rounded hover:bg-accent text-muted-foreground transition-all ${
                              msg.feedback_score < 0 ? 'text-destructive bg-destructive/10' : ''
                            }`}
                          >
                            <ThumbsDown className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Streaming placeholder message */}
              {isStreaming && streamingMessage && (
                <div className="flex flex-col max-w-[75%] gap-1.5 mr-auto items-start animate-in fade-in-50 duration-150">
                  <div className="px-4 py-3 bg-muted/40 border border-border/40 text-foreground rounded-xl rounded-tl-none text-sm leading-relaxed">
                    <p className="whitespace-pre-wrap">{streamingMessage}</p>
                  </div>
                  <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" /> Streaming response...
                  </span>
                </div>
              )}

              {/* Typing state spinner */}
              {isStreaming && !streamingMessage && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground p-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span>AI Assistant is compiling context facts...</span>
                </div>
              )}

              <div ref={messageEndRef} />
            </div>

            {/* Input area */}
            <form
              onSubmit={handleSendMessage}
              className="p-4 border-t border-border/40 flex items-center gap-2.5 bg-muted/5 shrink-0"
            >
              <input
                type="text"
                placeholder={
                  activeConv?.status === 'RESOLVED'
                    ? 'This session is resolved. Start a new session.'
                    : 'Ask about specifications, troubleshooting guidelines...'
                }
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                disabled={isStreaming || activeConv?.status === 'RESOLVED'}
                className="flex-1 bg-background border border-border/80 rounded-lg px-4 py-2.5 text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring transition-all"
              />
              <Button
                type="submit"
                disabled={isStreaming || !inputText.trim() || activeConv?.status === 'RESOLVED'}
                size="icon"
                className="h-10 w-10 shrink-0"
              >
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </>
        ) : (
          <EmptyState
            icon={MessageSquare}
            title="No Active Playground Session"
            description="Start a new widget session or choose an existing customer thread from the sidebar list."
            actionText="Start Playground Session"
            onAction={handleStartConversation}
          />
        )}
      </div>

      {/* Right Pane: Citation Cards */}
      <div className="w-80 bg-card border border-border/80 rounded-xl flex flex-col overflow-hidden shrink-0">
        <div className="p-4 border-b border-border/40 flex items-center gap-2 bg-muted/10">
          <BookMarked className="h-4.5 w-4.5 text-primary" />
          <h4 className="text-sm font-semibold">Matched Citations</h4>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeCitations.length === 0 ? (
            <p className="text-center text-xs text-muted-foreground py-12">
              No matching facts cited for the last message.
            </p>
          ) : (
            activeCitations.map((cit, idx) => (
              <Card key={cit.source_id + idx} className="hover:border-primary/20 transition-all">
                <CardContent className="p-4 space-y-2 text-xs">
                  <div className="flex items-center justify-between border-b border-border/40 pb-1.5">
                    <span className="font-semibold text-foreground truncate max-w-[150px]">
                      {cit.source_name}
                    </span>
                    {cit.score && (
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-500 border border-emerald-500/25 px-1.5 py-0.5 rounded font-mono">
                        {(cit.score * 100).toFixed(0)}% Match
                      </span>
                    )}
                  </div>
                  <p className="text-muted-foreground leading-relaxed italic">
                    &quot;{cit.chunk_text}&quot;
                  </p>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
export default ChatPage;
