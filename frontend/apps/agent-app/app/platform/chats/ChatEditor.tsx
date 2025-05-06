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
}

const ChatEditor: React.FC<ChatEditorProps> = ({ agent, chatHistory = [] }) => {
  const [history, setHistory] = useState<Message[]>([]);
  const { getToken } = useAuth();
  const searchParams = useSearchParams();
  const chatId = searchParams.get("chatId");
  const agentId = searchParams.get("agentId");

  useEffect(() => {
    if (chatHistory && chatHistory.length > 0) {
      setHistory(chatHistory);
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
        setHistory(Array.isArray(data) ? data : data.messages || []);
      } catch (error) {
        console.error("Error fetching history:", error);
      }
    };

    fetchHistory();
  }, [getToken, chatId, agentId, chatHistory]);

  return (
    <div className="w-full h-full flex flex-col bg-gray-200 dark:bg-gray-800 p-4">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Chat History</h2>

      {history.length === 0 ? (
        <div className="text-center text-gray-500 dark:text-gray-400">No history available</div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-4">
          {history.map((msg) => (
            <div
              key={msg.id}
              className={`p-4 rounded-lg ${
                msg.sender === "user"
                  ? "bg-green-100 dark:bg-green-900 ml-auto max-w-3/4"
                  : "bg-gray-100 dark:bg-gray-700 mr-auto max-w-3/4"
              }`}
            >
              <div className="text-sm font-medium text-gray-800 dark:text-gray-100">
                {msg.sender === "user" ? "You" : agent?.name || "Agent"}
              </div>
              <div className="text-gray-700 dark:text-gray-200 mt-1">{msg.content}</div>
              <div className="text-xs text-gray-500 mt-1">
                {new Date(msg.timestamp).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatEditor;