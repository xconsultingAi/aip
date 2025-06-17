"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { Agent } from "../../types/agent";

interface Chat {
  id: number;
  title: string;
  created_at: string;
}

interface ChatListProps {
  agents: Agent[];
  onSelectAgent: (agent: Agent) => void;
  onChatHistoryChange: (history: any[]) => void;
}

const ChatList: React.FC<ChatListProps> = ({ 
  agents, 
  onSelectAgent,
  onChatHistoryChange 
}) => {
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const [chatList, setChatList] = useState<Chat[]>([]);
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null);
  const [editingChatId, setEditingChatId] = useState<number | null>(null);
  const [editedTitle, setEditedTitle] = useState<string>("");
  const router = useRouter();
  const { getToken } = useAuth();

  const fetchChatsForAgent = async (agentId: number) => {
    try {
      const token = await getToken();
      const res = await fetch(`http://127.0.0.1:8000/api/conversations?agent_id=${agentId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
      if (!res.ok) throw new Error(`Failed to fetch chats. Status: ${res.status}`);
      const data = await res.json();
      setChatList(data);
      onChatHistoryChange([]);
      setSelectedChatId(null);
      setEditingChatId(null);
    } catch (error) {
      console.error("Error fetching chats:", error);
      setChatList([]);
    }
  };

  const fetchChatHistory = async (chatId: number, agentId: number) => {
    try {
      const token = await getToken();
      const res = await fetch(
        `http://127.0.0.1:8000/api/conversations/${chatId}?agent_id=${agentId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );
      if (!res.ok) throw new Error(`Failed to fetch messages. Status: ${res.status}`);
      const data = await res.json();
      const messages = Array.isArray(data) ? data : data.messages || [];
      onChatHistoryChange(messages);
      setSelectedChatId(chatId);
      setEditingChatId(null);
    } catch (error) {
      console.error("Error fetching chat history:", error);
      onChatHistoryChange([]);
    }
  };

  const handleDeleteChat = async (chatId: number) => {
    if (!selectedAgentId) return;
    
    try {
      const token = await getToken();
      const res = await fetch(
        `http://127.0.0.1:8000/api/conversations/${chatId}?agent_id=${selectedAgentId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      
      if (!res.ok) throw new Error(`Failed to delete chat. Status: ${res.status}`);
      
      // Refresh the chat list
      await fetchChatsForAgent(selectedAgentId);
    } catch (error) {
      console.error("Error deleting chat:", error);
    }
  };

  const handleEditChat = async (chatId: number) => {
    if (!selectedAgentId) return;
    
    try {
      const token = await getToken();
      const res = await fetch(
        `http://127.0.0.1:8000/api/conversations/${chatId}?agent_id=${selectedAgentId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ title: editedTitle }),
        }
      );
      
      if (!res.ok) throw new Error(`Failed to update chat. Status: ${res.status}`);
      
      // Refresh the chat list
      await fetchChatsForAgent(selectedAgentId);
      setEditingChatId(null);
    } catch (error) {
      console.error("Error updating chat:", error);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div>
        <div className="text-gray-500 dark:text-gray-300 mb-2">Agent List:</div>
        <div className="space-y-1">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="flex items-center justify-between py-2 px-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <div
                onClick={async () => {
                  setSelectedAgentId(agent.id);
                  onSelectAgent(agent);
                  await fetchChatsForAgent(agent.id);
                }}
                className={`flex-1 cursor-pointer ${
                  selectedAgentId === agent.id
                    ? "text-gray-700 dark:text-gray-200 font-medium"
                    : "text-gray-700 dark:text-gray-400"
                }`}
              >
                {agent.name}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  router.push(`/platform/chats/CreateChat?agentId=${agent.id}`);
                }}
                className="text-xl text-gray-500 dark:text-gray-300 hover:text-gray-700 dark:hover:text-white bg-transparent border border-gray-300 dark:border-gray-600 rounded px-2 py-1"
              >
                +
              </button>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="text-gray-500 dark:text-gray-300 mb-2">Chat List:</div>
        <div className="max-h-64 overflow-y-auto space-y-2 pr-2">
          {chatList.length === 0 && selectedAgentId !== null ? (
            <div className="text-sm text-gray-400">No chats found for this agent.</div>
          ) : (
            chatList.map((chat) => (
              <div
                key={chat.id}
                className={`px-4 py-2 border rounded ${
                  selectedChatId === chat.id
                    ? "bg-blue-100 dark:bg-blue-900"
                    : "bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
              >
                {editingChatId === chat.id ? (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                      placeholder="Chat title"
                    />
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleEditChat(chat.id)}
                        className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingChatId(null)}
                        className="px-3 py-1 bg-gray-500 text-white rounded hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div 
                      className="font-medium text-gray-800 dark:text-gray-100 cursor-pointer"
                      onClick={() => selectedAgentId && fetchChatHistory(chat.id, selectedAgentId)}
                    >
                      {chat.title}
                    </div>
                    <div className="flex justify-between items-center mt-1">
                      <div className="text-xs text-gray-500">
                        {new Date(chat.created_at).toLocaleString()}
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingChatId(chat.id);
                            setEditedTitle(chat.title);
                          }}
                          className="text-xs text-blue-500 hover:text-blue-700"
                        >
                          Edit
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm("Are you sure you want to delete this chat?")) {
                              handleDeleteChat(chat.id);
                            }
                          }}
                          className="text-xs text-red-500 hover:text-red-700"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatList;