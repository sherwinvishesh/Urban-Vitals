import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import './Chatbot.css';

// CO2 calculation function based on your formula
function calculateCO2Savings(numTokens, outputUnit = 'kg') {
  // Commercial provider parameters (using H100 GPUs)
  const commercial_power = 2.8;  // kW (4× H100 at 0.7 kW each)
  const commercial_ci = 0.43;    // kgCO2e/kWh (Azure data centers)
  const commercial_tps = 100;    // tokens/second
  const embodied_co2 = 7000;     // kgCO2e (4× H100 at 1750 kgCO2e each)
  const lifetime_hours = 43800;  // hours (5 years)
  
  // Tandemn parameters (using L40 GPUs)
  const tandemn_power = 1.5;     // kW (3× L40 at 0.5 kW each)
  const tandemn_ci = 0.15;       // kgCO2e/kWh (N. California grid)
  const tandemn_tps = 30;        // tokens/second
  
  // Calculate commercial emissions per token
  const commercial_operational = (commercial_power * commercial_ci) / commercial_tps;
  const commercial_embodied = embodied_co2 / (commercial_tps * lifetime_hours);
  const commercial_total = commercial_operational + commercial_embodied;
  
  // Calculate Tandemn emissions per token (no embodied carbon)
  const tandemn_total = (tandemn_power * tandemn_ci) / tandemn_tps;
  
  // Convert to per token (divide by 3600 to convert seconds to hours)
  const savings_per_token = (commercial_total - tandemn_total) / 3600;
  
  // Calculate total savings
  let total_savings = savings_per_token * numTokens;
  
  // Convert to requested unit
  if (outputUnit.toLowerCase() === 'g') {
    total_savings *= 1000; // Convert kg to grams
  } else if (outputUnit.toLowerCase() === 'mg') {
    total_savings *= 1000000; // Convert kg to milligrams
  }
  
  return total_savings;
}

// Estimate tokens in text (rough approximation: 1 token ≈ 4 characters)
function estimateTokens(text) {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

function Chatbot({ selectedNeighborhood, onClose, isVisible }) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [chatbotAvailable, setChatbotAvailable] = useState(true);
  
  // CO2 tracking state
  const [sessionStats, setSessionStats] = useState({
    totalTokens: 0,
    totalSavingsKg: 0,
    totalMessages: 0,
    sessionStartTime: new Date()
  });
  
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

  // Reset session stats when component mounts
  useEffect(() => {
    if (isVisible) {
      setSessionStats({
        totalTokens: 0,
        totalSavingsKg: 0,
        totalMessages: 0,
        sessionStartTime: new Date()
      });
    }
  }, [isVisible]);

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
        timestamp: new Date(),
        tokens: estimateTokens(welcomeMessage)
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

  // Update session stats
  const updateSessionStats = (userTokens, botTokens) => {
    const totalNewTokens = userTokens + botTokens;
    const newSavings = calculateCO2Savings(totalNewTokens, 'kg');
    
    setSessionStats(prev => ({
      ...prev,
      totalTokens: prev.totalTokens + totalNewTokens,
      totalSavingsKg: prev.totalSavingsKg + newSavings,
      totalMessages: prev.totalMessages + 1
    }));
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

    const userTokens = estimateTokens(inputMessage.trim());
    const userMessage = {
      id: Date.now(),
      text: inputMessage.trim(),
      isBot: false,
      timestamp: new Date(),
      tokens: userTokens
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
        const botTokens = estimateTokens(response.data.response);
        const botMessage = {
          id: Date.now() + 1,
          text: response.data.response,
          isBot: true,
          timestamp: new Date(),
          tokens: botTokens
        };
        
        setMessages(prev => [...prev, botMessage]);
        
        // Update CO2 stats
        updateSessionStats(userTokens, botTokens);
        
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
    const errorTokens = estimateTokens(errorText);
    const errorMessage = {
      id: Date.now(),
      text: errorText,
      isBot: true,
      isError: true,
      timestamp: new Date(),
      tokens: errorTokens
    };
    setMessages(prev => [...prev, errorMessage]);
  };

  const resetChat = async () => {
    try {
      await axios.post(`${API_BASE_URL}/api/chatbot/reset`);
      setMessages([]);
      
      // Reset CO2 stats
      setSessionStats({
        totalTokens: 0,
        totalSavingsKg: 0,
        totalMessages: 0,
        sessionStartTime: new Date()
      });
      
      // Re-add welcome message
      setTimeout(() => {
        const welcomeText = "Chat reset! How can I help you with Urban Vitals data?";
        const welcomeTokens = estimateTokens(welcomeText);
        const welcomeMessage = {
          id: Date.now(),
          text: welcomeText,
          isBot: true,
          timestamp: new Date(),
          tokens: welcomeTokens
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

  const formatCO2Savings = (savingsKg) => {
    if (savingsKg < 0.001) {
      return `${(savingsKg * 1000000).toFixed(2)} mg`; // milligrams
    } else if (savingsKg < 1) {
      return `${(savingsKg * 1000).toFixed(2)} g`; // grams
    } else {
      return `${savingsKg.toFixed(3)} kg`; // kilograms
    }
  };

  const getSessionDuration = () => {
    const now = new Date();
    const diffMs = now - sessionStats.sessionStartTime;
    const diffMins = Math.floor(diffMs / 60000);
    const diffSecs = Math.floor((diffMs % 60000) / 1000);
    return `${diffMins}m ${diffSecs}s`;
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

        {/* CO2 Savings Display */}
        <div className="co2-tracker">
          <div className="co2-stats">
            <div className="co2-stat">
              <span className="co2-label">🌱 CO₂ Saved</span>
              <span className="co2-value">{formatCO2Savings(sessionStats.totalSavingsKg)}</span>
            </div>
            <div className="co2-stat">
              <span className="co2-label">📝 Messages</span>
              <span className="co2-value">{sessionStats.totalMessages}</span>
            </div>
            <div className="co2-stat">
              <span className="co2-label">🎯 Tokens</span>
              <span className="co2-value">{sessionStats.totalTokens.toLocaleString()}</span>
            </div>
            <div className="co2-stat">
              <span className="co2-label">⏱️ Session</span>
              <span className="co2-value">{getSessionDuration()}</span>
            </div>
          </div>
          <div className="co2-explanation">
            <small>💡 By using Tandemn's eco-friendly AI instead of commercial providers, you're saving CO₂ through refurbished hardware and green energy!</small>
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
                <span className="message-time">
                  {formatTime(message.timestamp)}
                  {message.tokens && (
                    <span className="message-tokens"> • {message.tokens} tokens</span>
                  )}
                </span>
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