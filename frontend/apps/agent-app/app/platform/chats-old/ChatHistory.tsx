"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";

interface Agent {
  id: number;
  name: string;
}

interface Chat {
  id: number;
  title: string;
}

interface Message {
  id: number;
  sender: "user" | "agent";
  content: string;
  timestamp: string;
}

interface ChatHistoryProps {
  onBack: () => void;
}

const ChatHistory = ({ onBack }: ChatHistoryProps) => {
  const { getToken } = useAuth();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const [chats, setChats] = useState<Chat[]>([]);
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null);
  const [selectedChatTitle, setSelectedChatTitle] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch agents
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const token = await getToken();
        const res = await fetch("http://127.0.0.1:8000/api/agents", {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });
        const data = await res.json();
        const agentList = Array.isArray(data) ? data : data.agents || data.data || [];
        setAgents(agentList);
      } catch (err: any) {
        setError(err.message || "Error loading agents");
      }
    };
    fetchAgents();
  }, []);

  // Fetch chats
  useEffect(() => {
    if (selectedAgentId === null) return;

    const fetchChats = async () => {
      setLoading(true);
      try {
        const token = await getToken();
        const res = await fetch(`http://127.0.0.1:8000/api/conversations?agent_id=${selectedAgentId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });
        const data = await res.json();
        const chatList = Array.isArray(data) ? data : data.chats || data.data || [];
        setChats(chatList);
      } catch (err: any) {
        setError(err.message || "Error loading chats");
      } finally {
        setLoading(false);
      }
    };

    fetchChats();
  }, [selectedAgentId]);

  // Fetch messages and set chat title when a chat is selected
  useEffect(() => {
    if (selectedChatId === null) return;

    const fetchMessages = async () => {
      setLoading(true);
      try {
        const token = await getToken();
        const res = await fetch(`http://127.0.0.1:8000/api/conversations/${selectedChatId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });
        const data = await res.json();
        const msgList = Array.isArray(data) ? data : data.messages || data.data || [];
        setMessages(msgList);
        
        // Find and set the chat title
        const selectedChat = chats.find(chat => chat.id === selectedChatId);
        if (selectedChat) {
          setSelectedChatTitle(selectedChat.title);
        }
      } catch (err: any) {
        setError(err.message || "Error loading messages");
      } finally {
        setLoading(false);
      }
    };

    fetchMessages();
  }, [selectedChatId, chats]);

  const goBack = () => {
    if (selectedChatId !== null) {
      setSelectedChatId(null);
      setSelectedChatTitle("");
      setMessages([]);
    } else if (selectedAgentId !== null) {
      setSelectedAgentId(null);
      setChats([]);
    } else {
      onBack();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <button
          onClick={goBack}
          className="text-gray-600 hover:text-gray-800 font-medium"
        >
          Back
        </button>
        
        {selectedChatId !== null ? (
          <div className="text-center">
            <h2 className="font-semibold">{selectedChatTitle}</h2>
          </div>
        ) : selectedAgentId !== null ? (
          <h2 className="font-semibold">Chat History</h2>
        ) : (
          <h2 className="font-semibold">Select an Agent</h2>
        )}
        
        <div className="text-xs text-gray-500">
          {new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {error && <p className="text-red-500 mb-4 text-center">{error}</p>}

        {/* Messages View */}
        {selectedChatId !== null ? (
          loading ? (
            <div className="flex justify-center items-center h-full">
              <p className="text-gray-500">Loading messages...</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      msg.sender === "user"
                        ? "bg-blue-500 text-white"
                        : "bg-gray-200 text-gray-800"
                    }`}
                  >
                    <p className="text-sm">{msg.content}</p>
                    <p className="text-xs text-right mt-1 opacity-70">
                      {new Date(msg.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : selectedAgentId === null ? (
          /* Agents List */
          <div className="grid grid-cols-1 gap-3">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className="p-4 border rounded-md shadow-sm bg-white hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => setSelectedAgentId(agent.id)}
              >
                <h3 className="font-semibold">{agent.name}</h3>
              </div>
            ))}
          </div>
        ) : (
          /* Chats List */
          loading ? (
            <div className="flex justify-center items-center h-full">
              <p className="text-gray-500">Loading chats...</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  className="p-4 border rounded-md shadow-sm bg-white hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => {
                    setSelectedChatId(chat.id);
                    setSelectedChatTitle(chat.title);
                  }}
                >
                  <h3 className="font-semibold">{chat.title}</h3>
                </div>
              ))}
            </div>
          )
        )}
      </div>

      {/* Input area (visible only in chat view) */}
      {selectedChatId !== null && (
        <div className="p-4 border-t">
          <div className="flex items-center">
            <input
              type="text"
              placeholder="Type a message..."
              className="flex-1 border rounded-md px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatHistory;