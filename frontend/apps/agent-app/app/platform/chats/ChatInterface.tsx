import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';

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
  onBack: () => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onBack }) => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState<string>('');
  const [isAgentTyping, setIsAgentTyping] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { getToken } = useAuth();

  // Fetch agents from API
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const token = await getToken();
        const response = await fetch('http://127.0.0.1:8000/api/agents', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        const result = await response.json();
        console.log('Fetched Agents:', result);

        if (!result.success || !Array.isArray(result.data)) {
          throw new Error('Invalid API response');
        }

        setAgents(result.data);
      } catch (err) {
        console.error('Error fetching agents:', err);
        setError('Error loading agents');
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();
  }, [getToken]);

  // Scroll to bottom when messages update
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Send message to chat API (with query parameters)
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || !selectedAgent) return;
  
    // Add user message to chat
    const userMessage: Message = {
      id: Math.random().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date(),
    };
  
    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setIsAgentTyping(true);
  
    try {
      const token = await getToken();
  
      // Construct API URL with agent_id and prompt as query params
      const apiUrl = `http://127.0.0.1:8000/api/agents/${selectedAgent.id}/chat?prompt=${encodeURIComponent(inputText)}`;
  
      const response = await fetch(apiUrl, {
        method: 'POST', // ✅ API requires GET
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
  
      const data = await response.json();
      console.log('Chat API Response:', data);
  
      if (!response.ok || !data.success) {
        throw new Error(data.message || 'Chat API error');
      }
  
      // Add agent response to chat
      const agentMessage: Message = {
        id: Math.random().toString(),
        text: data.response, // ✅ Ensure API returns `{ response: "Agent's reply" }`
        sender: 'agent',
        timestamp: new Date(),
      };
  
      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      console.error('Chat API error:', error);
      setMessages((prev) => [
        ...prev,
        { id: Math.random().toString(), text: 'Error getting response.', sender: 'agent', timestamp: new Date() },
      ]);
    } finally {
      setIsAgentTyping(false);
    }
  };
  

  return (
    <div className="flex flex-col h-[500px] border border-gray-300 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center p-4 border-b border-gray-300 dark:bg-gray-900 bg-gray-50">
        <button
          onClick={onBack}
          className="px-4 py-2 text-white bg-gray-600 rounded-lg hover:bg-gray-700"
        >
          &larr; Back
        </button>
        <h3 className="text-lg block font-medium">
          {selectedAgent ? `Chat with ${selectedAgent.name}` : 'Select an Agent'}
        </h3>
      </div>

      {/* Agent Selection */}
      {!selectedAgent ? (
        <div className="p-4 space-y-3 bg-gray-50 dark:bg-gray-900">
          {loading ? (
            <p>Loading agents...</p>
          ) : error ? (
            <p className="text-red-500">{error}</p>
          ) : (
            <>
              <h4 className="text-lg font-medium">Choose an agent:</h4>
              {agents.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent)}
                  className="block w-full p-3 text-left bg-gray-200 rounded-lg hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600"
                >
                  {agent.name}
                </button>
              ))}
            </>
          )}
        </div>
      ) : (
        <>
          {/* Chat Messages */}
          <div className="flex-1 p-4 overflow-y-auto bg-gray-50 dark:bg-gray-900">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`mb-4 ${message.sender === 'user' ? 'text-right' : 'text-left'}`}
              >
                <div
                  className={`inline-block p-3 rounded-lg max-w-[70%] ${
                    message.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'
                  }`}
                >
                  <p>{message.text}</p>
                  <span className="text-xs text-gray-500 block mt-1">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
            {isAgentTyping && (
              <div className="text-left">
                <div className="inline-block p-3 rounded-lg bg-gray-200 text-gray-800">
                  <p>{selectedAgent.name} is typing...</p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Message Input Form */}
          <form onSubmit={handleSendMessage} className="p-4 border-t border-gray-300 dark:bg-gray-900">
            <div className="flex">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="flex-1 p-2 border border-gray-300 rounded-l-md focus:outline-none dark:bg-gray-900"
                placeholder="Type a message..."
                disabled={!selectedAgent}
              />
              <button
                type="submit"
                className="px-4 py-2 bg-green-500 text-white rounded-r-md hover:bg-green-600 dark:bg-green-800"
                disabled={!selectedAgent}
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
