"use client";

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';

interface Agent {
  id: string;
  name: string;
}

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
}

interface ChatInterfaceProps {
  onBack?: () => void; // Made optional with ?
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onBack }) => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isAgentTyping, setIsAgentTyping] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { getToken } = useAuth();
  const router = useRouter();

  // Enhanced back handler
  const handleBackClick = () => {
    console.log('Back button clicked'); // Debug log
    try {
      if (typeof onBack === 'function') {
        console.log('Using provided onBack handler');
        onBack();
      } else {
        console.log('Falling back to router.back()');
        router.back();
      }
    } catch (err) {
      console.error('Back navigation failed:', err);
      router.push('/'); // Ultimate fallback
    }
  };

  // Fetch agents
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const token = await getToken();
        const response = await fetch('http://127.0.0.1:8000/api/agents', {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch agents');
        }

        const result = await response.json();
        if (!Array.isArray(result.data)) {
          throw new Error('Invalid agents data format');
        }

        setAgents(result.data);
      } catch (err) {
        console.error('Error fetching agents:', err);
        setError(err instanceof Error ? err.message : 'Error loading agents');
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();
  }, [getToken]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Setup WebSocket when agent is selected
  useEffect(() => {
    if (!selectedAgent) return;

    const connectWebSocket = async () => {
      try {
        const token = await getToken();
        const ws = new WebSocket(
          `ws://127.0.0.1:8000/api/ws/chat/${selectedAgent.id}?token=${token}`
        );

        ws.onopen = () => {
          console.log('WebSocket connected');
          socketRef.current = ws;
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const agentMessage: Message = {
              id: Date.now().toString(),
              text: data.content || data.text || 'No message',
              sender: 'agent',
              timestamp: new Date(),
            };
            setMessages((prev) => [...prev, agentMessage]);
            setIsAgentTyping(false);
          } catch (err) {
            console.error('Error processing message:', err);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setError('Connection error');
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
        };

        return () => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.close();
          }
        };
      } catch (err) {
        console.error('WebSocket connection error:', err);
        setError('Failed to connect');
      }
    };

    connectWebSocket();

    return () => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.close();
      }
    };
  }, [selectedAgent, getToken]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsAgentTyping(true);
    socketRef.current.send(JSON.stringify({ content: text }));
    setInputText('');
  };

  return (
    <div className="flex flex-col h-[500px] border border-gray-300 rounded-lg overflow-hidden bg-white dark:bg-gray-800">
      <div className="flex justify-between items-center p-4 border-b border-gray-300 bg-gray-50 dark:bg-gray-900">
        <button
          onClick={(e) => {
            e.preventDefault();
            handleBackClick();
          }}
          className="px-4 py-2 text-white bg-gray-600 rounded-lg hover:bg-gray-700 transition-colors"
          aria-label="Go back"
        >
          &larr; Back
        </button>
        <h3 className="text-lg font-medium text-gray-800 dark:text-white">
          {selectedAgent ? `Chat with ${selectedAgent.name}` : 'Select an Agent'}
        </h3>
      </div>

      {!selectedAgent ? (
        <div className="p-4 space-y-3 bg-gray-50 dark:bg-gray-900">
          {loading ? (
            <div className="flex justify-center items-center h-20">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            </div>
          ) : error ? (
            <p className="text-red-500 p-2 rounded bg-red-50 dark:bg-red-900/20">{error}</p>
          ) : (
            <>
              <h4 className="text-lg font-medium text-gray-800 dark:text-white">Choose an agent:</h4>
              <div className="space-y-2">
                {agents.map((agent) => (
                  <button
                    key={agent.id}
                    onClick={() => setSelectedAgent(agent)}
                    className="w-full p-3 text-left bg-gray-200 rounded-lg hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-white transition-colors"
                  >
                    {agent.name}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      ) : (
        <>
          <div className="flex-1 p-4 overflow-y-auto bg-white dark:bg-gray-800">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`mb-4 ${message.sender === 'user' ? 'text-right' : 'text-left'}`}
              >
                <div
                  className={`inline-block p-3 rounded-lg max-w-[70%] ${
                    message.sender === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-white'
                  }`}
                >
                  <p>{message.text}</p>
                  <span className="text-xs opacity-70 block mt-1">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
            {isAgentTyping && (
              <div className="text-left">
                <div className="inline-block p-3 rounded-lg bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-white">
                  <p>{selectedAgent.name} is typing...</p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSendMessage} className="p-4 border-t border-gray-300 bg-gray-50 dark:bg-gray-900">
            <div className="flex">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="flex-1 p-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                placeholder="Type a message..."
                disabled={!selectedAgent}
              />
              <button
                type="submit"
                className="px-4 py-2 bg-green-500 text-white rounded-r-md hover:bg-green-600 disabled:opacity-50 dark:bg-green-600 dark:hover:bg-green-700 transition-colors"
                disabled={!selectedAgent || !inputText.trim()}
              >
                Send
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
};

export default ChatInterface;