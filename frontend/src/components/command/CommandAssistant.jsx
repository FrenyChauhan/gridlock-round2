import React, { useState, useRef, useEffect } from 'react';
import { Terminal, X, Send } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import '../../styles/assistant.css';

export default function CommandAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [hasUnassigned, setHasUnassigned] = useState(true); // Default true for notification demo
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  
  const bottomRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

  const starters = [
    "Urgent zones needing patrol",
    "Teams freeing up soon",
    "Volatile zones today",
    "Today's false positive rate"
  ];

  const handleSend = (text) => {
    if (!text.trim()) return;
    
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput('');
    setIsTyping(true);

    // Mock API response delay
    setTimeout(() => {
      let reply = "";
      if (text.toLowerCase().includes('urgent')) {
        reply = "CRITICAL ALERT: There are currently 3 unassigned Red zones in the Shivajinagar and Koramangala sectors. Predicted volume is exceeding 450+ violations within the next 2 hours. It is highly recommended to dispatch Reserve Substitution teams immediately to mitigate severe gridlock risks before the Evening peak.";
      } else if (text.toLowerCase().includes('teams')) {
        reply = "RESOURCE FORECAST: Teams OFF-0842 and OFF-0129 are currently on-site at Madiwala but are predicted to be free in under 12 minutes (based on historical resolution time of 42 mins/incident). They are perfectly positioned to substitute in the Indiranagar corridor where volatility is rising.";
      } else if (text.toLowerCase().includes('volatile')) {
        reply = "VOLATILITY REPORT: Our predictive models detect 14 'Volatile Growing' zones today. The highest risk sector is HSR Layout, showing an unexpected 22% spike in predicted violations compared to the 7-day moving average. Assigning proactive patrols to HSR is highly advised.";
      } else if (text.toLowerCase().includes('false positive')) {
        reply = "SYSTEM HEALTH: Today's False Positive Rate (FPR) across the entire grid is sitting at an excellent 2.4%, which is 0.8% below the weekly average. The prediction engine is currently operating with high confidence (94.2% accuracy in Amber zones).";
      } else {
        reply = "ERROR: LLM API Key is missing or invalid. Please insert a valid API key in the settings to process custom generative queries. However, you can try clicking the predefined quick prompts below to see how the AI system would structure responses!";
      }
      
      setIsTyping(false);
      setMessages(prev => [...prev, { role: 'system', content: reply }]);
      setHasUnassigned(false); // clear notification on first interaction
    }, 1200);
  };

  return (
    <>
      <button 
        className="assistant-trigger" 
        onClick={() => setIsOpen(!isOpen)}
        title="Command Assistant"
      >
        <Terminal size={22} />
        {hasUnassigned && <div className="ast-dot"></div>}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div 
            className="assistant-panel"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 20, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 250 }}
          >
            <div className="ast-header">
              <div className="ast-header-left">
                <Terminal size={14} color="var(--scan-blue)" />
                <span>COMMAND ASSISTANT</span>
              </div>
              <div className="ast-header-right">
                <span className="ast-badge">AI</span>
                <button className="ast-close" onClick={() => setIsOpen(false)}>
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="ast-body">
              {messages.length === 0 && (
                <div className="ast-msg-sys">
                  System initialized. How can I assist Command today?
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={msg.role === 'system' ? 'ast-msg-sys' : 'ast-msg-usr'}>
                  {msg.content}
                </div>
              ))}

              {isTyping && (
                <div className="ast-loading">
                  <span className="ast-dot-anim">.</span>
                  <span className="ast-dot-anim">.</span>
                  <span className="ast-dot-anim">.</span>
                </div>
              )}

              {!isTyping && (
                <div className="ast-chips">
                  {starters.map(s => (
                    <button key={s} className="ast-chip" onClick={() => handleSend(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              )}
              
              <div ref={bottomRef} />
            </div>

            <div className="ast-footer">
              <input 
                type="text" 
                className="ast-input"
                placeholder="Query the intelligence layer..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend(input)}
              />
              <button className="ast-send" onClick={() => handleSend(input)}>
                <Send size={18} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
