import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import './Chatbot.css';

function Chatbot({ selectedNeighborhood, onClose, isVisible }) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [chatbotAvailable, setChatbotAvailable] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when new messages are added
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Check chatbot status on mount
  useEffect(() => {
    checkChatbotStatus();
  }, []);

  // Add welcome message when chatbot opens
  useEffect(() => {
    if (isVisible && messages.length === 0) {
      const welcomeMessage = selectedNeighborhood
        ? `Hi! I'm your Urban Vitals assistant. I can help you understand the data for ${selectedNeighborhood.name}. What would you like to know?`
        : "Hi! I'm your Urban Vitals assistant. I can help you understand neighborhood data, green scores, and sustainability metrics. What would you like to know?";
      
      setMessages([{
        id: Date.now(),
        text: welcomeMessage,
        isBot: true,
        timestamp: new Date()
      }]);
    }
  }, [isVisible, selectedNeighborhood]);

  // Focus input when chatbot becomes visible
  useEffect(() => {
    if (isVisible) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isVisible]);

  const checkChatbotStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/chatbot/status`);
      setChatbotAvailable(response.data.available);
    } catch (error) {
      console.error('Failed to check chatbot status:', error);
      setChatbotAvailable(false);
    }
  };

  // Function to convert markdown-style formatting to HTML
  const formatMessage = (text) => {
    if (!text) return '';
    
    // Convert markdown formatting to HTML
    let formatted = text
      // Bold: **text** or __text__
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.*?)__/g, '<strong>$1</strong>')
      
      // Italic: *text* or _text_
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/(?<!_)_([^_]+?)_(?!_)/g, '<em>$1</em>')
      
      // Code: `code`
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      
      // Line breaks
      .replace(/\n/g, '<br>');

    return formatted;
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputMessage.trim() || isLoading) return;
    if (!chatbotAvailable) {
      addErrorMessage("Chatbot is currently unavailable. Please try again later.");
      return;
    }

    const userMessage = {
      id: Date.now(),
      text: inputMessage.trim(),
      isBot: false,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/chatbot/message`, {
        message: userMessage.text,
        neighborhood_context: selectedNeighborhood
      });

      setIsTyping(false);
      
      if (response.data.success) {
        const botMessage = {
          id: Date.now() + 1,
          text: response.data.response,
          isBot: true,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        addErrorMessage(response.data.error || "Sorry, I couldn't process your request.");
      }
    } catch (error) {
      console.error('Chat error:', error);
      setIsTyping(false);
      addErrorMessage("I'm having trouble connecting right now. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const addErrorMessage = (errorText) => {
    const errorMessage = {
      id: Date.now(),
      text: errorText,
      isBot: true,
      isError: true,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, errorMessage]);
  };

  const resetChat = async () => {
    try {
      await axios.post(`${API_BASE_URL}/api/chatbot/reset`);
      setMessages([]);
      // Re-add welcome message
      setTimeout(() => {
        const welcomeMessage = {
          id: Date.now(),
          text: "Chat reset! How can I help you with Urban Vitals data?",
          isBot: true,
          timestamp: new Date()
        };
        setMessages([welcomeMessage]);
      }, 100);
    } catch (error) {
      console.error('Failed to reset chat:', error);
    }
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const suggestedQuestions = [
    "What does the green score mean?",
    "How is air quality measured?",
    "What factors affect walkability?",
    "Compare this neighborhood to others",
    "What can improve sustainability here?"
  ];

  const handleSuggestionClick = (question) => {
    setInputMessage(question);
    inputRef.current?.focus();
  };

  if (!isVisible) return null;

  return (
    <div className="chatbot-overlay">
      <div className="chatbot-container">
        <div className="chatbot-header">
          <div className="chatbot-title">
            <div className="chatbot-avatar">🌱</div>
            <div>
              <h3>Urban Vitals Assistant</h3>
              <span className={`status ${chatbotAvailable ? 'online' : 'offline'}`}>
                {chatbotAvailable ? 'Online' : 'Offline'}
              </span>
            </div>
          </div>
          <div className="chatbot-controls">
            <button className="reset-button" onClick={resetChat} title="Reset conversation">
              🔄
            </button>
            <button className="close-button" onClick={onClose}>
              ✕
            </button>
          </div>
        </div>

        <div className="chatbot-messages">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.isBot ? 'bot-message' : 'user-message'} ${message.isError ? 'error-message' : ''}`}
            >
              <div className="message-content">
                {message.isBot ? (
                  <div 
                    className="message-text"
                    dangerouslySetInnerHTML={{ 
                      __html: formatMessage(message.text) 
                    }}
                  />
                ) : (
                  <p className="message-text">{message.text}</p>
                )}
                <span className="message-time">{formatTime(message.timestamp)}</span>
              </div>
            </div>
          ))}
          
          {isTyping && (
            <div className="message bot-message">
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

        {messages.length === 1 && (
          <div className="suggested-questions">
            <p>Try asking:</p>
            <div className="suggestions">
              {suggestedQuestions.map((question, index) => (
                <button
                  key={index}
                  className="suggestion-button"
                  onClick={() => handleSuggestionClick(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        <form className="chatbot-input-form" onSubmit={sendMessage}>
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={chatbotAvailable ? "Ask about neighborhoods, scores, or sustainability..." : "Chatbot unavailable"}
            disabled={!chatbotAvailable || isLoading}
            className="chatbot-input"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || !chatbotAvailable || isLoading}
            className="send-button"
          >
            {isLoading ? '⏳' : '📤'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Chatbot;