"use client";

import { useState } from "react";
import ChatList from "./ChatList";
import ChatEditor from "./ChatEditor";
import { Agent } from "../../types/agent";
import { useRouter } from "next/navigation";

interface ChatListWrapperProps {
  agents: Agent[];
}

export default function ChatListWrapper({ agents }: ChatListWrapperProps) {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const router = useRouter();

  return (
    <div className="flex h-full bg-gray-200 dark:bg-gray-800">
      <div className="w-1/4 bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-400 rounded-lg">
        {agents.length === 0 ? (
          <div className="p-4">
            <button
              className="mt-4 w-full py-2 px-4 bg-green-600 text-white hover:bg-green-700"
              onClick={() => router.push("/platform/chats/CreateChat")}
            >
              Create Chat
            </button>
            <p className="mt-4 text-gray-500 dark:text-gray-300 text-center flex h-full items-center justify-center">
              No chat found. Click above to create your first chat.
            </p>
          </div>
        ) : (
          <ChatList 
            agents={agents} 
            onSelectAgent={setSelectedAgent}
            onChatHistoryChange={setChatHistory}
          />
        )}
      </div>

      <div className="w-3/4 bg-gray-100 dark:bg-gray-800">
        <ChatEditor agent={selectedAgent} chatHistory={chatHistory} />
      </div>
    </div>
  );
}