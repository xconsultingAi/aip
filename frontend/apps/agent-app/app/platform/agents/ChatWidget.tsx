"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

const ChatWidget = () => {
  const searchParams = useSearchParams();
  const agentId = searchParams.get("agentId") || "default";
  const greeting = searchParams.get("greeting") || "Hello! How can I help?";
  const themeColor = searchParams.get("color") || "#22c55e";

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([{ sender: "agent", text: greeting }]);
  const [input, setInput] = useState("");

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(`ws://localhost:8000/ws/agents/${agentId}`);
    wsRef.current = socket;

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev) => [...prev, { sender: "agent", text: data.message }]);
    };

    socket.onopen = () => console.log("WebSocket connected");
    socket.onclose = () => console.log("WebSocket closed");

    return () => socket.close();
  }, [agentId]);

  const sendMessage = () => {
    if (!input.trim()) return;
    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);

    wsRef.current?.send(JSON.stringify({ message: input }));
    setInput("");
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 font-sans">
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          style={{ backgroundColor: themeColor }}
          className="rounded-full w-14 h-14 flex items-center justify-center text-white shadow-lg"
        >
          💬
        </button>
      ) : (
        <div className="w-80 bg-white shadow-lg rounded-lg flex flex-col overflow-hidden border border-gray-300">
          <div
            className="p-3 text-white font-bold flex justify-between items-center"
            style={{ backgroundColor: themeColor }}
          >
            <span>Chat</span>
            <button onClick={() => setIsOpen(false)} className="text-white">×</button>
          </div>

          <div className="flex-1 p-3 overflow-y-auto space-y-2 bg-gray-50 max-h-96">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`p-2 rounded-md max-w-xs ${
                  msg.sender === "user"
                    ? "bg-green-100 ml-auto text-right"
                    : "bg-gray-200 mr-auto text-left"
                }`}
              >
                {msg.text}
              </div>
            ))}
          </div>

          <div className="p-2 border-t flex items-center space-x-2 bg-white">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              className="flex-1 px-3 py-2 border rounded"
              placeholder="Type your message..."
            />
            <button
              onClick={sendMessage}
              style={{ backgroundColor: themeColor }}
              className="px-3 py-2 text-white rounded"
            >
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatWidget;
