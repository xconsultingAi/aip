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
    } catch (error) {
      console.error("Error fetching chat history:", error);
      onChatHistoryChange([]);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <button
        className="w-full py-2 px-4 bg-green-600 text-white hover:bg-green-700 rounded"
        onClick={() => router.push("/platform/chats/CreateChat")}
      >
        Create Chat
      </button>

      <div>
        <div className="text-gray-500 dark:text-gray-300 mb-2">Agent List:</div>
        <div className="space-y-1">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className={`py-2 px-4 rounded cursor-pointer ${
                selectedAgentId === agent.id
                  ? "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200"
                  : "hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-400"
              }`}
              onClick={async () => {
                setSelectedAgentId(agent.id);
                onSelectAgent(agent);
                await fetchChatsForAgent(agent.id);
              }}
            >
              {agent.name}
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
                className={`px-4 py-2 border rounded cursor-pointer ${
                  selectedChatId === chat.id
                    ? "bg-blue-100 dark:bg-blue-900"
                    : "bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
                onClick={() => selectedAgentId && fetchChatHistory(chat.id, selectedAgentId)}
              >
                <div className="font-medium text-gray-800 dark:text-gray-100">{chat.title}</div>
                <div className="text-xs text-gray-500">{new Date(chat.created_at).toLocaleString()}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatList;