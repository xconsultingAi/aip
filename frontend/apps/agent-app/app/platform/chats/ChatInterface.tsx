import { useState, useEffect, useRef } from 'react';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
}

interface ChatInterfaceProps {
  onBack: () => void; // Callback for the Back button
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onBack }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState<string>('');
  const [isAgentTyping, setIsAgentTyping] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Simulate agent response
  useEffect(() => {
    if (isAgentTyping) {
      const timer = setTimeout(() => {
        const newMessage: Message = {
          id: Math.random().toString(),
          text: 'This is a response from the agent.',
          sender: 'agent',
          timestamp: new Date(),
        };
        setMessages((prevMessages) => [...prevMessages, newMessage]);
        setIsAgentTyping(false);
      }, 2000); // Simulate a 2-second delay for agent response
      return () => clearTimeout(timer);
    }
  }, [isAgentTyping]);

  // Scroll to the bottom of the chat when new messages are added
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputText.trim()) return;

    const newMessage: Message = {
      id: Math.random().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prevMessages) => [...prevMessages, newMessage]);
    setInputText('');
    setIsAgentTyping(true); // Simulate agent typing
  };

  return (
    <div className="flex flex-col h-[500px] border border-gray-300 rounded-lg overflow-hidden">
      {/* Header with Back Button */}
      <div className="flex justify-between items-center p-4 border-b border-gray-300 bg-gray-50">
        <button
          onClick={onBack}
          className="px-4 py-2 text-white bg-gray-600 rounded-lg hover:bg-gray-900"
        >
          &larr; Back
        </button>
        <h3 className="text-lg text-black font-medium">Chat Interface</h3>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 p-4 overflow-y-auto bg-gray-50 ">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`mb-4 ${
              message.sender === 'user' ? 'text-right' : 'text-left'
            }`}
          >
            <div
              className={`inline-block p-3 rounded-lg max-w-[70%] ${
                message.sender === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 text-gray-800'
              }`}
            >
              <p>{message.text}</p>
              <span className="text-xs text-white-500 block mt-1">
                {message.timestamp.toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
        {isAgentTyping && (
          <div className="text-left">
            <div className="inline-block p-3 rounded-lg bg-gray-200 text-gray-800">
              <p>Agent is typing...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input Form */}
      <form onSubmit={handleSendMessage} className="p-4 border-t border-gray-300">
        <div className="flex">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            className="flex-1 p-2 border border-gray-300 rounded-l-md focus:outline-none"
            placeholder="Type a message..."
          />
          <button
            type="submit"
            className="px-4 py-2 bg-green-500 text-white rounded-r-md hover:bg-green-600"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;