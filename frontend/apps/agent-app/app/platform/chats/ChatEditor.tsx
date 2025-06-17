"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { useAuth } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";
import MessageInput from "./MessageInput";

interface Message {
  id: number;
  sender: string;
  content: string;
  timestamp: string;
  conversation_id?: string;
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
  onMessageUpdate,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [userChats, setUserChats] = useState<
    { id: string; title: string; updated_at: string }[]
  >([]);
  const [loadingChats, setLoadingChats] = useState(false);
  const [editingMessageId, setEditingMessageId] = useState<number | null>(null);
  const [editedContent, setEditedContent] = useState<string>("");
  const [newMessage, setNewMessage] = useState<string>("");

  const { getToken } = useAuth();
  const searchParams = useSearchParams();
  const ws = useRef<WebSocket | null>(null);
  const messageContainerRef = useRef<HTMLDivElement | null>(null);

  const chatId = useMemo(() => {
    return (
      searchParams.get("chat_id") ||
      chatHistory?.[0]?.conversation_id ||
      messages?.[0]?.conversation_id ||
      null
    );
  }, [searchParams, chatHistory, messages]);

  // Clear messages when agent changes but no chat is selected
  useEffect(() => {
    if (!chatId) {
      setMessages([]);
      onMessageUpdate?.([]);
    }
  }, [agent, chatId, onMessageUpdate]);

  // Fetch chat history when chatId changes
  useEffect(() => {
    if (chatHistory.length > 0) {
      setMessages(chatHistory);
      return;
    }

    const fetchHistory = async () => {
      if (!chatId) return;
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
        if (!response.ok) throw new Error("Failed to fetch chat history");

        const data = await response.json();
        const loadedMessages = Array.isArray(data.content)
          ? data.content.map((msg: any) => ({
              id: msg.sequence_id,
              sender: msg.sender,
              content: msg.content,
              timestamp: msg.timestamp,
            }))
          : [];

        setMessages(loadedMessages);
        onMessageUpdate?.(loadedMessages);
      } catch (error) {
        console.error("Error fetching chat history:", error);
      }
    };

    fetchHistory();
  }, [chatId, chatHistory, getToken, onMessageUpdate]);

  // Fetch chats list (either all or agent-specific)
  useEffect(() => {
    const fetchChats = async () => {
      setLoadingChats(true);
      try {
        const token = await getToken();
        let url = "http://127.0.0.1:8000/api/user/conversations";
        
        if (agent?.id) {
          url = `http://127.0.0.1:8000/api/conversations?agent_id=${agent.id}`;
        }

        const response = await fetch(url, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        
        if (!response.ok) throw new Error("Failed to fetch conversations");
        const data = await response.json();
        setUserChats(data || []);
      } catch (error) {
        console.error("Error fetching chats:", error);
      } finally {
        setLoadingChats(false);
      }
    };

    if (!chatId) {
      fetchChats();
    }
  }, [chatId, getToken, agent?.id]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!chatId) return;

    const connectWebSocket = async () => {
      try {
        const token = await getToken();
        const wsUrl = `ws://127.0.0.1:8000/api/ws/conversation/${chatId}?token=${token}`;
        const socket = new WebSocket(wsUrl);
        ws.current = socket;

        socket.onopen = () => console.log("✅ WebSocket connected");

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === "history" && Array.isArray(data.content)) {
              const historyMessages = data.content.map((msg: any) => ({
                id: msg.sequence_id,
                sender: msg.sender,
                content: msg.content,
                timestamp: msg.timestamp,
              }));
              setMessages(historyMessages);
              onMessageUpdate?.(historyMessages);
            } else if (data.type === "message" && typeof data.content === "string") {
              const newMsg: Message = {
                id: data.sequence_id,
                sender: data.sender,
                content: data.content,
                timestamp: data.timestamp,
                conversation_id: chatId,
              };
              setMessages((prev) => {
                if (prev.find((m) => m.id === newMsg.id)) return prev;
                const updated = [...prev, newMsg];
                onMessageUpdate?.(updated);
                return updated;
              });
            }
          } catch (err) {
            console.error("Failed to parse WS message:", err, event.data);
          }
        };

        socket.onerror = (error) => console.error("WebSocket error:", error);
        socket.onclose = (event) => console.log("❌ WebSocket closed:", event.reason);
      } catch (err) {
        console.error("WebSocket setup failed:", err);
      }
    };

    connectWebSocket();
    return () => {
      ws.current?.close();
      ws.current = null;
    };
  }, [chatId, getToken, onMessageUpdate]);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    if (messageContainerRef.current) {
      messageContainerRef.current.scrollTop = messageContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = () => {
    if (!newMessage.trim() || !ws.current || ws.current.readyState !== WebSocket.OPEN || !chatId) {
      return;
    }

    const tempMessage: Message = {
      id: Date.now(),
      sender: "user",
      content: newMessage.trim(),
      timestamp: new Date().toISOString(),
      conversation_id: chatId,
    };

    const payload = {
      type: "send_message",
      chat_id: chatId,
      content: tempMessage.content,
      sender: "user",
      timestamp: tempMessage.timestamp,
    };

    try {
      ws.current.send(JSON.stringify(payload));
    } catch (err) {
      console.error("WebSocket send error:", err);
    }

    setNewMessage("");
    setMessages((prev) => {
      const updated = [...prev, tempMessage];
      onMessageUpdate?.(updated);
      return updated;
    });
  };

  const handleDeleteMessage = async (messageId: number) => {
    if (!chatId) return;
    try {
      const token = await getToken();
      const res = await fetch(
        `http://127.0.0.1:8000/api/messages/${messageId}?chat_id=${chatId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      if (!res.ok) throw new Error("Delete failed");
      const updated = messages.filter((msg) => msg.id !== messageId);
      setMessages(updated);
      onMessageUpdate?.(updated);
    } catch (err) {
      console.error("Delete error:", err);
    }
  };

  const handleEditMessage = async (messageId: number) => {
    if (!editedContent.trim() || !chatId) return;
    try {
      const token = await getToken();
      const res = await fetch(
        `http://127.0.0.1:8000/api/messages/${messageId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ content: editedContent, chat_id: chatId }),
        }
      );
      if (!res.ok) throw new Error("Edit failed");
      const updated = messages.map((msg) =>
        msg.id === messageId ? { ...msg, content: editedContent } : msg
      );
      setMessages(updated);
      setEditingMessageId(null);
      onMessageUpdate?.(updated);
    } catch (err) {
      console.error("Edit error:", err);
    }
  };

  const handleChatSelect = (chatId: string) => {
    const url = new URL(window.location.href);
    url.searchParams.set("chat_id", chatId);
    window.history.pushState({}, "", url.toString());
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const handleBackClick = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete("chat_id");
    window.history.pushState({}, "", url.toString());
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  return (
    <div className="w-full h-full flex flex-col bg-gray-200 dark:bg-gray-800 p-4 rounded-lg">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          {agent?.name || "Chat"} History
        </h2>
        {chatId && (
          <div className="flex justify-between items-center p-4">
            <button
              onClick={handleBackClick}
              className="px-4 py-2 text-white bg-gray-600 rounded-lg hover:bg-gray-700 transition-colors"
            >
              &larr; Back
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-col flex-1 overflow-hidden">
        <div
          className="h-[500px] overflow-y-auto space-y-4 pr-2 mb-4"
          ref={messageContainerRef}
        >
          {!chatId ? (
            loadingChats ? (
              <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                Loading chats...
              </div>
            ) : userChats.length > 0 ? (
              <div className="space-y-2">
                {userChats.map((chat) => (
                  <div
                    key={chat.id}
                    onClick={() => handleChatSelect(chat.id)}
                    className="p-3 bg-gray-100 dark:bg-gray-700 rounded cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600"
                  >
                    <div className="font-semibold">{chat.title || "Untitled Chat"}</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      Last updated: {new Date(chat.updated_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                {agent
                  ? "No chats available for this agent. Start a new conversation!"
                  : "No chats available. Start a new conversation!"}
              </div>
            )
          ) : messages.length === 0 ? (
            <div className="text-center text-gray-500 dark:text-gray-400 py-8">
              No messages yet. Start a conversation!
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`p-4 rounded-lg relative max-w-[80%] ${
                  message.sender === "user"
                    ? "bg-green-100 dark:bg-green-900 ml-auto"
                    : "bg-gray-100 dark:bg-gray-700 mr-auto"
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
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    <div className="flex justify-between mt-2 text-xs text-gray-600 dark:text-gray-400">
                      <span>{new Date(message.timestamp).toLocaleString()}</span>
                      {/* <div className="space-x-2">
                        {message.sender === "user" && (
                          <>
                            <button
                              onClick={() => {
                                setEditingMessageId(message.id);
                                setEditedContent(message.content);
                              }}
                              className="text-blue-600 hover:underline"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteMessage(message.id)}
                              className="text-red-600 hover:underline"
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </div> */}
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>

        {chatId && (
          <MessageInput
            newMessage={newMessage}
            setNewMessage={setNewMessage}
            sendMessage={sendMessage}
          />
        )}
      </div>
    </div>
  );
};

export default ChatEditor;