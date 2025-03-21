"use client";
import { useEffect, useState } from "react";

interface ChatHistoryProps {
  onBack: () => void;
}

const ChatHistory = ({ onBack }: ChatHistoryProps) => {
  const [chats, setChats] = useState<{ id: number; title: string }[]>([]);

  useEffect(() => {
    // Mock fetching chat history (Replace this with API call)
    setChats([
      { id: 1, title: "Chat 1" },
      { id: 2, title: "Chat 2" },
      { id: 3, title: "Chat 3" },
    ]);
  }, []);

  return (
    <div className="p-4 border rounded-md w-full max-w-md mx-auto">
      {/* Back Button */}
      <button onClick={onBack} className="bg-gray-500 text-white px-4 py-2 rounded-md mb-4">
        ← Back
      </button>

      <h2 className="text-lg font-bold mb-4">Chat History</h2>

      <div className="grid grid-cols-1 gap-4">
        {chats.length > 0 ? (
          chats.map((chat) => (
            <div
              key={chat.id}
              className="p-4 border rounded-md shadow-sm bg-white hover:bg-gray-100 cursor-pointer"
              onClick={() => console.log(`Open ${chat.title}`)} // Handle chat selection
            >
              <h3 className="font-semibold">{chat.title}</h3>
            </div>
          ))
        ) : (
          <p className="text-gray-500">No chat history available.</p>
        )}
      </div>
    </div>
  );
};

export default ChatHistory;
