import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/api';
import './ChatInterface.css';

const ChatInterface = ({ onQueryResponse }) => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your SAP Order-to-Cash data assistant. Ask me questions about sales orders, deliveries, invoices, payments, customers, or products.',
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Get conversation history
      const history = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
      }));

      const response = await apiService.query(userMessage.content, history);

      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        query_type: response.query_type,
        data: response.data,
        highlighted_nodes: response.highlighted_nodes,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Notify parent component about highlighted nodes
      if (onQueryResponse) {
        onQueryResponse(response);
      }

    } catch (error) {
      console.error('Query error:', error);
      
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your query. Please try again or rephrase your question.',
        isError: true,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleExampleClick = (example) => {
    setInput(example);
    inputRef.current?.focus();
  };

  const exampleQueries = [
    "Which products are associated with the highest number of billing documents?",
    "Trace the flow of billing document 90504248",
    "Show me sales orders that have broken or incomplete flows",
    "Find deliveries that haven't been billed",
    "What customers have the most sales orders?",
  ];

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h2>💬 Query Assistant</h2>
        <div className="chat-status">
          {isLoading ? '🔄 Processing...' : '✓ Ready'}
        </div>
      </div>

      {messages.length <= 1 && (
        <div className="example-queries">
          <p className="examples-title">Try these example queries:</p>
          {exampleQueries.map((example, idx) => (
            <button
              key={idx}
              className="example-query"
              onClick={() => handleExampleClick(example)}
            >
              {example}
            </button>
          ))}
        </div>
      )}

      <div className="messages-container">
        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`message ${message.role} ${message.isError ? 'error' : ''}`}
          >
            <div className="message-header">
              <span className="message-role">
                {message.role === 'user' ? '🧑 You' : '🤖 Assistant'}
              </span>
              <span className="message-time">
                {message.timestamp.toLocaleTimeString()}
              </span>
            </div>
            
            <div className="message-content">
              {message.content}
            </div>

            {message.query_type && (
              <div className="message-metadata">
                <span className="query-type-badge">{message.query_type}</span>
              </div>
            )}

            {message.data && (
              <div className="message-data">
                <pre>{message.data}</pre>
              </div>
            )}

            {message.highlighted_nodes && message.highlighted_nodes.length > 0 && (
              <div className="highlighted-nodes-info">
                <span className="nodes-badge">
                  🔍 {message.highlighted_nodes.length} nodes highlighted
                </span>
              </div>
            )}
          </div>
        ))}
        
        {isLoading && (
          <div className="message assistant loading">
            <div className="message-header">
              <span className="message-role">🤖 Assistant</span>
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about the SAP O2C data..."
          className="chat-input"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="send-button"
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? '⏳' : '📤'}
        </button>
      </form>
    </div>
  );
};

export default ChatInterface;
