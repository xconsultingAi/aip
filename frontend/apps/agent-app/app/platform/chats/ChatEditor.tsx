"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";

interface Message {
  id: number;
  sender: string;
  content: string;
  timestamp: string;
}

interface ChatEditorProps {
  agent: {
    id: number;
    name: string;
  } | null;
  chatHistory?: Message[];
  onMessageUpdate?: (updatedMessages: Message[]) => void;
}

const ChatEditor: React.FC<ChatEditorProps> = ({ 
  agent, 
  chatHistory = [],
  onMessageUpdate
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [editingMessageId, setEditingMessageId] = useState<number | null>(null);
  const [editedContent, setEditedContent] = useState<string>("");
  const { getToken } = useAuth();
  const searchParams = useSearchParams();
  const chatId = searchParams.get("chatId");
  const agentId = searchParams.get("agentId");

  useEffect(() => {
    if (chatHistory && chatHistory.length > 0) {
      setMessages(chatHistory);
      return;
    }

    const fetchHistory = async () => {
      if (!chatId || !agentId) return;

      try {
        const token = await getToken();
        const response = await fetch(
          `http://127.0.0.1:8000/api/conversations/${chatId}?agent_id=${agentId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error("Failed to fetch chat history");
        }

        const data = await response.json();
        const loadedMessages = Array.isArray(data) ? data : data.messages || [];
        setMessages(loadedMessages);
        
        // Notify parent of loaded messages if callback exists
        if (onMessageUpdate) {
          onMessageUpdate(loadedMessages);
        }
      } catch (error) {
        console.error("Error fetching history:", error);
      }
    };

    fetchHistory();
  }, [getToken, chatId, agentId, chatHistory, onMessageUpdate]);

  const handleDeleteMessage = async (messageId: number) => {
    if (!chatId || !agentId) return;

    try {
      const token = await getToken();
      const response = await fetch(
        `http://127.0.0.1:8000/api/messages/${messageId}?chat_id=${chatId}&agent_id=${agentId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to delete message");
      }

      // Update local state
      const updatedMessages = messages.filter(msg => msg.id !== messageId);
      setMessages(updatedMessages);
      
      // Notify parent if callback exists
      if (onMessageUpdate) {
        onMessageUpdate(updatedMessages);
      }
    } catch (error) {
      console.error("Error deleting message:", error);
    }
  };

  const handleEditMessage = async (messageId: number) => {
    if (!editedContent.trim() || !chatId || !agentId) return;

    try {
      const token = await getToken();
      const response = await fetch(
        `http://127.0.0.1:8000/api/messages/${messageId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ 
            content: editedContent,
            chat_id: chatId,
            agent_id: agentId
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to update message");
      }

      // Update local state
      const updatedMessages = messages.map(msg => 
        msg.id === messageId ? { ...msg, content: editedContent } : msg
      );
      setMessages(updatedMessages);
      setEditingMessageId(null);
      
      // Notify parent if callback exists
      if (onMessageUpdate) {
        onMessageUpdate(updatedMessages);
      }
    } catch (error) {
      console.error("Error updating message:", error);
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-gray-200 dark:bg-gray-800 p-4 rounded-lg">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
        {agent?.name || "Chat"} History
      </h2>

      {messages.length === 0 ? (
        <div className="text-center text-gray-500 dark:text-gray-400 py-8">
          No messages yet. Start a conversation!
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-4 pr-2">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`p-4 rounded-lg relative ${
                message.sender === "user"
                  ? "bg-green-100 dark:bg-green-900 ml-auto max-w-[80%]"
                  : "bg-gray-100 dark:bg-gray-700 mr-auto max-w-[80%]"
              }`}
            >
              {editingMessageId === message.id ? (
                <div className="space-y-2">
                  <textarea
                    value={editedContent}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                    rows={3}
                    autoFocus
                  />
                  <div className="flex space-x-2 justify-end">
                    <button
                      onClick={() => setEditingMessageId(null)}
                      className="px-3 py-1 bg-gray-500 text-white rounded hover:bg-gray-600"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleEditMessage(message.id)}
                      className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex justify-between items-start">
                    <div className="text-sm font-medium text-gray-800 dark:text-gray-100">
                      {message.sender === "user" ? "You" : agent?.name || "Agent"}
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => {
                          setEditingMessageId(message.id);
                          setEditedContent(message.content);
                        }}
                        className="text-xs text-blue-500 hover:text-blue-700 dark:hover:text-blue-400"
                        title="Edit message"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => {
                          if (confirm("Are you sure you want to delete this message?")) {
                            handleDeleteMessage(message.id);
                          }
                        }}
                        className="text-xs text-red-500 hover:text-red-700 dark:hover:text-red-400"
                        title="Delete message"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="text-gray-700 dark:text-gray-200 mt-1 whitespace-pre-wrap">
                    {message.content}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {new Date(message.timestamp).toLocaleString()}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatEditor;