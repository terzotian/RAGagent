import React, { useState, useEffect, useRef } from 'react';
import { Container, Form, Button, Spinner } from 'react-bootstrap';
import { streamAnswer, type Reference } from '../services/api';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  references?: Reference[];
}

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [base, setBase] = useState('lingnan'); // 默认知识库
  const [language, setLanguage] = useState<'en' | 'zh-cn' | 'zh-tw'>('zh-cn');
  const [sessionId] = useState(() => 'session_' + Math.random().toString(36).substr(2, 9));
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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

  const handleSend = () => {
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

    streamAnswer({
      session_id: sessionId,
      question_id: questionId,
      previous_questions: previousQuestions,
      current_question: userMsg,
      language: language,
      base: base,
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
      },
      onError: () => {
        setLoading(false);
        setMessages(prev => [...prev, { role: 'assistant', content: '\n[Error: Connection interrupted]' }]);
      }
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="d-flex flex-column h-100 position-relative">
      {/* 顶部设置栏 (悬浮) */}
      <div className="position-absolute top-0 end-0 p-3 z-3">
         <div className="d-flex gap-2 bg-white p-2 rounded shadow-sm border">
            <Form.Select size="sm" value={base} onChange={(e) => setBase(e.target.value)} style={{ width: '130px', border: 'none', background: '#f8f9fa' }}>
              <option value="lingnan">📚 Lingnan</option>
              <option value="base_DS">📊 Data Science</option>
            </Form.Select>
            <Form.Select size="sm" value={language} onChange={(e) => setLanguage(e.target.value as 'en' | 'zh-cn' | 'zh-tw')} style={{ width: '110px', border: 'none', background: '#f8f9fa' }}>
              <option value="zh-cn">🇨🇳 简体中文</option>
              <option value="en">🇺🇸 English</option>
              <option value="zh-tw">🇭🇰 繁体中文</option>
            </Form.Select>
         </div>
      </div>

      {/* 聊天内容区域 */}
      <div className="flex-grow-1 overflow-auto w-100" style={{ paddingBottom: '140px' }}>
        <Container className="chat-container py-5">
          {messages.length === 0 && (
            <div className="text-center mt-5 pt-5">
              <div className="mb-4">
                <div style={{ fontSize: '4rem' }}>🤖</div>
              </div>
              <h2 className="fw-bold mb-3 text-dark">有什么可以帮你的吗？</h2>
              <p className="text-muted">选择一个知识库，开始提问吧</p>
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
                    <div className="fw-bold mb-1 text-muted" style={{ fontSize: '0.8rem' }}>📚 参考来源:</div>
                    <ul className="mb-0 ps-3 text-muted">
                      {msg.references.map((ref, rIdx) => (
                        <li key={rIdx}>
                          {ref.file_name} <span className="badge bg-light text-dark border ms-1">{ref.similarity?.toFixed(2)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="avatar user ms-3 shadow-sm">Me</div>
              )}

            </div>
          ))}
          
          {loading && messages[messages.length - 1]?.role === 'user' && (
            <div className="d-flex mb-4 justify-content-start">
               <div className="avatar ai me-3 shadow-sm">AI</div>
               <div className="message-bubble assistant bg-white">
                  <div className="d-flex align-items-center gap-2 text-muted">
                    <Spinner animation="grow" size="sm" />
                    <span>思考中...</span>
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
              placeholder="输入你的问题..."
              className="modern-textarea"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              style={{ maxHeight: '200px', overflowY: 'auto' }}
            />
            <div className="d-flex justify-content-between align-items-center px-2 pb-1 mt-1">
               <div className="small text-muted ps-2">
                 <small>Shift + Enter 换行</small>
               </div>
               <Button 
                variant={input.trim() ? "primary" : "secondary"} 
                size="sm" 
                onClick={handleSend} 
                disabled={loading || !input.trim()} 
                className="rounded-pill px-4"
                style={{ opacity: input.trim() ? 1 : 0.6 }}
               >
                {loading ? <Spinner animation="border" size="sm" /> : '发送'}
              </Button>
            </div>
          </div>
          <div className="text-center mt-2">
             <small className="text-muted" style={{ fontSize: '0.75rem' }}>AI 生成的内容可能不准确，请核实重要信息。</small>
          </div>
        </Container>
      </div>
    </div>
  );
};

export default ChatPage;
