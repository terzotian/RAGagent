import React, { useState, useEffect, useRef } from 'react';
import { Container, Form, Button, Spinner, Image, ListGroup } from 'react-bootstrap';
import { streamAnswer, getAvatarUrl, api, type Reference, type User } from '../services/api';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  references?: Reference[];
}

interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
  last_activity: string;
}

interface ChatPageProps {
  user?: User | null;
  base: string;
  language: 'en' | 'zh-cn' | 'zh-tw';
}

const ChatPage: React.FC<ChatPageProps> = ({ user, base, language }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => 'session_' + Math.random().toString(36).substr(2, 9));
  const [showSidebar, setShowSidebar] = useState(false);
  const [historySessions, setHistorySessions] = useState<ChatSession[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (user) {
      api.getUserSessions(user.user_id).then(setHistorySessions).catch(console.error);
    } else {
      setHistorySessions([]);
    }
  }, [user]);

  const handleNewChat = () => {
    setSessionId('session_' + Math.random().toString(36).substr(2, 9));
    setMessages([]);
    setInput('');
    if (user) {
      api.getUserSessions(user.user_id).then(setHistorySessions).catch(console.error);
    }
  };

  const loadSession = async (sid: string) => {
    if (sid === sessionId) return;
    try {
      setLoading(true);
      const msgs = await api.getSessionMessages(sid);
      setMessages(msgs);
      setSessionId(sid);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 自动调整输入框高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    const newMessages: Message[] = [...messages, { role: 'user', content: userMsg }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);
    
    // 重置输入框高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    // 添加一个空的 assistant 消息占位
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    const questionId = 'q_' + Date.now();
    const previousQuestions = messages.filter(m => m.role === 'user').map(m => m.content);

    // 累积 Token 的临时变量
    let currentAnswer = '';

    // Close previous stream if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = await streamAnswer({
      session_id: sessionId,
      question_id: questionId,
      previous_questions: previousQuestions,
      current_question: userMsg,
      language: language,
      base: base,
      user_id: user?.user_id,
      onToken: (token) => {
        currentAnswer += token;
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last.role === 'assistant') {
            return [...prev.slice(0, -1), { ...last, content: currentAnswer }];
          }
          return prev;
        });
      },
      onReferences: (refs) => {
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last.role === 'assistant') {
            return [...prev.slice(0, -1), { ...last, references: refs }];
          }
          return prev;
        });
      },
      onDone: () => {
        setLoading(false);
        abortControllerRef.current = null;
        // Refresh history after chat
        if (user) {
           // Small delay to ensure DB is updated
           setTimeout(() => {
               api.getUserSessions(user.user_id).then(setHistorySessions).catch(console.error);
           }, 1000);
        }
      },
      onError: () => {
        setLoading(false);
        abortControllerRef.current = null;
        setMessages(prev => [...prev, { role: 'assistant', content: '\n[Error: Connection interrupted. Please try again.]' }]);
      }
    });
    
    if (controller) {
      abortControllerRef.current = controller;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="d-flex h-100 w-100 overflow-hidden">
      {/* Sidebar */}
      <div 
        className="bg-light border-end d-flex flex-column" 
        style={{ 
            width: showSidebar ? '280px' : '0px', 
            overflow: 'hidden', 
            transition: 'width 0.3s ease',
            flexShrink: 0 
        }}
      >
        <div className="p-3 border-bottom d-flex justify-content-between align-items-center bg-white">
           <span className="fw-bold text-primary">History</span>
           <Button variant="link" size="sm" className="p-0 text-secondary text-decoration-none" onClick={() => setShowSidebar(false)}>
             <span style={{ fontSize: '1.2rem' }}>&times;</span>
           </Button>
        </div>
        <div className="p-3 flex-grow-1 overflow-auto">
           <Button variant="primary" className="w-100 mb-3 shadow-sm" onClick={handleNewChat}>
             <span className="me-2">+</span> New Chat
           </Button>
           
           {user ? (
               <div className="mt-2">
                   <div className="text-muted small mb-2 text-uppercase fw-bold" style={{ fontSize: '0.75rem' }}>Recent</div>
                   <ListGroup variant="flush">
                       {historySessions.map(s => (
                           <ListGroup.Item 
                               key={s.session_id} 
                               action 
                               active={s.session_id === sessionId}
                               onClick={() => loadSession(s.session_id)}
                               className="border-0 rounded mb-1 text-truncate px-2 py-2"
                               style={{ fontSize: '0.9rem', backgroundColor: s.session_id === sessionId ? '#e9ecef' : 'transparent', color: '#333', fontWeight: s.session_id === sessionId ? 600 : 400 }}
                           >
                               {s.title || 'Untitled Chat'}
                           </ListGroup.Item>
                       ))}
                       {historySessions.length === 0 && (
                         <div className="text-center text-muted small mt-4">No history yet</div>
                       )}
                   </ListGroup>
               </div>
           ) : (
               <div className="text-center text-muted small mt-5 p-3 bg-white rounded border border-dashed">
                 Log in to view and save your chat history.
               </div>
           )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-grow-1 d-flex flex-column position-relative h-100" style={{ minWidth: 0 }}>
        {/* Toggle Button */}
        {!showSidebar && (
          <Button 
            variant="light" 
            className="position-absolute top-0 start-0 m-3 shadow-sm z-3 border d-flex align-items-center justify-content-center"
            onClick={() => setShowSidebar(true)}
            style={{ width: '40px', height: '40px', borderRadius: '50%', backgroundColor: 'rgba(255,255,255,0.9)' }}
            title="Show History"
          >
            <span style={{ fontSize: '1.2rem' }}>☰</span>
          </Button>
        )}

        {/* 聊天内容区域 */}
        <div className="flex-grow-1 overflow-auto w-100" style={{ paddingBottom: '140px' }}>
          <Container className="chat-container py-5">
          {messages.length === 0 && (
            <div className="text-center mt-5 pt-5">
              <div className="mb-4">
                <div style={{ fontSize: '4rem' }}>🤖</div>
              </div>
              <h2 className="fw-bold mb-3 text-dark">How can I assist you today?</h2>
              <p className="text-muted">Select a knowledge base to get started</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`d-flex mb-4 ${msg.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}>
              
              {msg.role === 'assistant' && (
                <div className="avatar ai me-3 shadow-sm">AI</div>
              )}
              
              <div className={`message-bubble ${msg.role} shadow-sm`} style={{ maxWidth: '85%' }}>
                {msg.role === 'assistant' ? (
                   <div className="markdown-body">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                   </div>
                ) : (
                  msg.content
                )}
                
                {msg.references && msg.references.length > 0 && (
                  <div className="mt-3 pt-2 border-top small" style={{ borderColor: 'rgba(0,0,0,0.1)' }}>
                    <div className="fw-bold mb-1 text-muted" style={{ fontSize: '0.8rem' }}>📚 Reference source:</div>
                    <ul className="mb-0 ps-3 text-muted">
                      {msg.references.map((ref, rIdx) => (
                        <li key={rIdx}>
                          {ref.file_name} <span className="badge bg-light text-dark border ms-1">{typeof ref.similarity === 'number' ? ref.similarity.toFixed(2) : ref.similarity}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="avatar user ms-3 shadow-sm p-0 overflow-hidden d-flex align-items-center justify-content-center">
                  {user && user.avatar_path ? (
                     <Image 
                       src={getAvatarUrl(user.avatar_path)} 
                       style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                     />
                  ) : (
                    user ? user.nickname.charAt(0).toUpperCase() : 'Me'
                  )}
                </div>
              )}

            </div>
          ))}
          
          {loading && messages[messages.length - 1]?.role === 'user' && (
            <div className="d-flex mb-4 justify-content-start">
               <div className="avatar ai me-3 shadow-sm">AI</div>
               <div className="message-bubble assistant bg-white">
                  <div className="d-flex align-items-center gap-2 text-muted">
                    <Spinner animation="grow" size="sm" />
                    <span>Thinking...</span>
                  </div>
               </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </Container>
      </div>

      {/* 底部输入区域 (固定) */}
      <div className="position-absolute bottom-0 start-0 end-0 input-area-wrapper">
        <Container className="chat-container">
          <div className="modern-input-group d-flex flex-column">
            <Form.Control
              as="textarea"
              ref={textareaRef}
              rows={1}
              placeholder="Enter your question..."
              className="modern-textarea"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              style={{ maxHeight: '200px', overflowY: 'auto' }}
            />
            <div className="d-flex justify-content-between align-items-center px-2 pb-1 mt-1">
               <div className="small text-muted ps-2">
                 <small>Shift + Enter Newline</small>
               </div>
               <Button 
                variant={input.trim() ? "primary" : "secondary"} 
                size="sm" 
                onClick={handleSend} 
                disabled={loading || !input.trim()} 
                className="rounded-pill px-4"
                style={{ opacity: input.trim() ? 1 : 0.6 }}
               >
                {loading ? <Spinner animation="border" size="sm" /> : 'Send'}
              </Button>
            </div>
          </div>
          <div className="text-center mt-2">
             <small className="text-muted" style={{ fontSize: '0.75rem' }}>AI-generated content may not be accurate, please verify important information.</small>
          </div>
        </Container>
      </div>
    </div>
    </div>
  );
};

export default ChatPage;
