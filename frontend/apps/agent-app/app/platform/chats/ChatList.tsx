"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { Agent } from "../../types/agent";

interface ChatListProps {
  agents: Agent[];
  onSelectAgent: (agent: Agent) => void;
  onChatHistoryChange: (history: any[]) => void;
  selectedAgentId: number | null; // Add this prop
}

const ChatList: React.FC<ChatListProps> = ({
  agents,
  onSelectAgent,
  onChatHistoryChange,
  selectedAgentId, // Receive selected agent from parent
}) => {
  const [agentChats, setAgentChats] = useState<Record<number, any[]>>({});
  const { getToken } = useAuth();
  const router = useRouter();

  const fetchAgentChats = async (agentId: number) => {
    try {
      const token = await getToken();
      const response = await fetch(
        `http://127.0.0.1:8000/api/agent/${agentId}/conversations`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      setAgentChats((prev) => ({ ...prev, [agentId]: data }));
    } catch (err) {
      console.error("Failed to load agent chats", err);
    }
  };

  const handleAgentClick = async (agent: Agent) => {
    onSelectAgent(agent);
    onChatHistoryChange([]);
    
    // Only fetch chats if not already loaded
    if (!agentChats[agent.id]) {
      await fetchAgentChats(agent.id);
    }
  };

  const handleChatSelect = async (chatId: string) => {
    try {
      const token = await getToken();
      const response = await fetch(
        `http://127.0.0.1:8000/api/conversations/${chatId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      const messages = Array.isArray(data.content)
        ? data.content.map((msg: any) => ({
            id: msg.sequence_id,
            sender: msg.sender,
            content: msg.content,
            timestamp: msg.timestamp,
            conversation_id: chatId,
          }))
        : [];
      onChatHistoryChange(messages);

      // Update URL with chat_id param
      const url = new URL(window.location.href);
      url.searchParams.set("chat_id", chatId);
      window.history.pushState({}, "", url.toString());
      window.dispatchEvent(new PopStateEvent("popstate"));
    } catch (err) {
      console.error("Failed to load selected chat", err);
    }
  };

  // Fetch chats for the selected agent when it changes
  useEffect(() => {
    if (selectedAgentId && !agentChats[selectedAgentId]) {
      fetchAgentChats(selectedAgentId);
    }
  }, [selectedAgentId]);

  return (
    <div className="p-4 space-y-4">
      <div>
        <div className="text-gray-500 dark:text-gray-300 mb-2">Agent List:</div>
        <div className="space-y-1">
          {agents.map((agent) => (
            <div key={agent.id}>
              <div className="flex items-center justify-between py-2 px-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                <div
                  onClick={() => handleAgentClick(agent)}
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
                    router.push(
                      `/platform/chats/CreateChat?agentId=${agent.id}`
                    );
                  }}
                  className="text-xl text-gray-500 dark:text-gray-300 hover:text-gray-700 dark:hover:text-white bg-transparent border border-gray-300 dark:border-gray-600 rounded px-2 py-1"
                >
                  +
                </button>
              </div>

              {/* Show chats if this agent is selected */}
              {selectedAgentId === agent.id && (
                <div className="ml-4 mt-2 space-y-1">
                  {agentChats[agent.id]?.length > 0 ? (
                    agentChats[agent.id].map((chat) => (
                      <div
                        key={chat.id}
                        onClick={() => handleChatSelect(chat.id)}
                        className="cursor-pointer p-2 rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-sm"
                      >
                        {chat.title || "Untitled Chat"}
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {agentChats[agent.id] ? "No chats for this agent." : "Loading chats..."}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ChatList;