"use client";

import { useState, useEffect } from "react";
import { Agent } from "../../types/agent";
import { useAuth } from "@clerk/nextjs";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";

const tabs = ["Model", "Knowledgebase", "Widget", "Analysis"];

interface AgentEditorProps {
  agent: Agent | null;
}

const AgentEditor: React.FC<AgentEditorProps> = ({ agent }) => {
  const [activeTab, setActiveTab] = useState("Model");
  const [agentData, setAgentData] = useState<Agent | null>(agent);
  const { getToken } = useAuth();
  const router = useRouter();

  // Model Tab State
  const [modelConfig, setModelConfig] = useState({
    firstMessage: "",
    provider: "OpenAI",
    model: "gpt-3.5-turbo",
    maxLength: 100,
    temperature: 0.7,
  });

  // Knowledge Base Tab State
  const [selectedKnowledgeBaseIds, setSelectedKnowledgeBaseIds] = useState<number[]>([]);

  // Widget Tab State
  const [color, setColor] = useState("#22c55e");
  const [greeting, setGreeting] = useState("Hello! How can I help?");
  const [agentName, setAgentName] = useState("");
  const [isPublic, setIsPublic] = useState(true);

  // Initialize all states when agent changes
  useEffect(() => {
    setAgentData(agent);
  
    if (agent) {
      // Model config
      setModelConfig({
        firstMessage: agent.description || "",
        provider: "OpenAI",
        model: agent.config?.model_name || "gpt-3.5-turbo",
        maxLength: agent.config?.max_length ?? 100,
        temperature: agent.config?.temperature ?? 0.7,
      });
      
      // Knowledge base
      setSelectedKnowledgeBaseIds(agent.config?.knowledge_base_ids || []);
      
      // Widget settings
      setColor(agent.theme_color || "#22c55e");
      setGreeting(agent.greeting_message || "Hello! How can I help?");
      setAgentName(agent.name || "");
      setIsPublic(agent.is_public ?? true);
    }
  }, [agent]);

  const handlePublish = async () => {
    if (!agentData) return;

    const payload = {
      model_name: modelConfig.model,
      temperature: modelConfig.temperature,
      max_length: modelConfig.maxLength,
      system_prompt: modelConfig.firstMessage,
      knowledge_base_ids: selectedKnowledgeBaseIds,
      // Widget settings
      greeting_message: greeting,
      theme_color: color,
      is_public: isPublic,
      name: agentName,
      embed_code: `<script src="https://localhost:3000/embed-loader.js" data-agent="${agentData?.id}" data-color="${color}" data-greeting="${greeting}" data-name="${agentName}"></script>`
    };

    try {
      const token = await getToken();
      const response = await fetch(`http://127.0.0.1:8000/api/agents/${agentData?.id}/config`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("Failed to save agent configuration");
      }

      alert("All settings saved successfully!");
      window.location.reload();
    } catch (error) {
      console.error("Error saving configuration:", error);
      alert("Error saving configuration.");
    }
  };

  if (!agentData) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-500 bg-gray-200 dark:bg-gray-800 rounded-lg">
        Select an agent to edit
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-gray-200 dark:bg-gray-800 p-4 ">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          {agentData.name}
        </h2>
        <button onClick={handlePublish} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
          Save Changes
        </button>
      </div>

      <div className="flex space-x-4 border-b border-gray-300 dark:border-gray-700 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === tab ? "text-green-600 border-b-2 border-green-600" : "text-gray-500 hover:text-gray-700 dark:text-gray-400"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 bg-gray-200 dark:bg-gray-800">
        {activeTab === "Model" && <ModelTabContent modelConfig={modelConfig} setModelConfig={setModelConfig} />}
        {activeTab === "Knowledgebase" && <KBTabContent selectedIds={selectedKnowledgeBaseIds} setSelectedIds={setSelectedKnowledgeBaseIds} />}
        {activeTab === "Widget" && (
          <AdvancedTabContent 
            agent={agentData}
            color={color}
            setColor={setColor}
            greeting={greeting}
            setGreeting={setGreeting}
            agentName={agentName}
            setAgentName={setAgentName}
            isPublic={isPublic}
            setIsPublic={setIsPublic}
          />
        )}
        {activeTab === "Analysis" && <AnalysisTabContent />}
      </div>
    </div>
  );
};

//HZ: Model Tab Component
const ModelTabContent = ({ modelConfig, setModelConfig }: { modelConfig: any; setModelConfig: any }) => {
  return (
    <div className="space-y-2 bg-gray-100 dark:bg-gray-900 p-6 rounded-lg shadow-lg">
      <div>
        <label className="block text-sm font-medium">First Message</label>
        <textarea
          className="w-full p-2 border bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-700 rounded"
          placeholder="This is a blank template..."
          value={modelConfig.firstMessage}
          onChange={(e) => setModelConfig((prev: any) => ({ ...prev, firstMessage: e.target.value }))}
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Provider</label>
        <select
          className="w-full p-2 border border-gray-300 dark:border-gray-700 dark:bg-gray-800 rounded"
          value={modelConfig.provider}
          onChange={(e) => setModelConfig((prev: any) => ({ ...prev, provider: e.target.value }))}
        >
          <option>OpenAI</option>
          <option>Other Provider</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium">Model</label>
        <select
          className="w-full p-2 border border-gray-300 dark:border-gray-700 dark:bg-gray-800 rounded"
          value={modelConfig.model}
          onChange={(e) => setModelConfig((prev: any) => ({ ...prev, model: e.target.value }))}
        >
          <option>gpt-3.5-turbo</option>
          <option>gpt-4</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium">Max Length</label>
        <input
          type="number"
          min="10"
          className="w-full p-2 border border-gray-300 dark:border-gray-700 dark:bg-gray-800 rounded"
          value={modelConfig.maxLength}
          onChange={(e) => setModelConfig((prev: any) => ({ ...prev, maxLength: e.target.value }))}
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Temperature</label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          className="w-full"
          value={modelConfig.temperature}
          onChange={(e) => setModelConfig((prev: any) => ({ ...prev, temperature: parseFloat(e.target.value) }))}
        />
      </div>
    </div>
  );
};

//HZ: Knowledge Base Tab Component
const KBTabContent = ({
  selectedIds,
  setSelectedIds,
}: {
  selectedIds: number[];
  setSelectedIds: React.Dispatch<React.SetStateAction<number[]>>;
}) => {
  const [knowledgeBase, setKnowledgeBase] = useState<
    { id: number; filename: string }[]
  >([]);
  const { getToken } = useAuth();
  const router = useRouter();
  useEffect(() => {
    const fetchKnowledgeBase = async () => {
      try {
        const token = await getToken();
        if (!token) {
          console.error("No auth token found.");
          return;
        }

        const response = await fetch(
          "http://127.0.0.1:8000/api/org_knowledge_base",
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Error fetching knowledge base: ${response.status}`);
        }

        const data = await response.json();
        console.log("Knowledge Base Data:", data);

        if (Array.isArray(data)) {
          setKnowledgeBase(data);
        } else if (data?.data && Array.isArray(data.data)) {
          setKnowledgeBase(data.data);
        } else {
          console.error("Unexpected API response format:", data);
          setKnowledgeBase([]);
        }
      } catch (error) {
        console.error("Error fetching knowledge base:", error);
        setKnowledgeBase([]);
      }
    };

    fetchKnowledgeBase();
  }, [getToken]);

  const toggleSelection = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleCreateClick = () => {
    router.push("/platform/knowledgebase/CreateKnowledgebase");
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Knowledge Base</h2>
        <button
          onClick={handleCreateClick}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          + Create
        </button>
      </div>

      {/* File List */}
      {knowledgeBase.length === 0 ? (
        <div className="text-gray-500 text-center">
          No knowledge base available
        </div>
      ) : (
        <div className="space-y-2">
          {knowledgeBase.map((file) => (
            <div
              key={file.id}
              className="flex items-center bg-gray-100 p-2 rounded"
            >
              <input
                type="checkbox"
                checked={selectedIds.includes(file.id)}
                onChange={() => toggleSelection(file.id)}
                className="mr-3"
              />
              <span className="text-sm text-gray-800">{file.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Updated Widget Tab Component
interface AdvancedTabContentProps {
  agent: Agent;
  color: string;
  setColor: React.Dispatch<React.SetStateAction<string>>;
  greeting: string;
  setGreeting: React.Dispatch<React.SetStateAction<string>>;
  agentName: string;
  setAgentName: React.Dispatch<React.SetStateAction<string>>;
  isPublic: boolean;
  setIsPublic: React.Dispatch<React.SetStateAction<boolean>>;
}

const AdvancedTabContent: React.FC<AdvancedTabContentProps> = ({
  agent,
  color,
  setColor,
  greeting,
  setGreeting,
  agentName,
  setAgentName,
  isPublic,
  setIsPublic,
}) => {
  const [showWidget, setShowWidget] = useState(false);
  const [messages, setMessages] = useState<string[]>([]);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const { getToken } = useAuth();

  useEffect(() => {
    if (!agent?.id) return;

    const ws = new WebSocket(`ws://127.0.0.1:8000/api/ws/public/${agent.id}`);
    setSocket(ws);

    ws.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      const iframe = document.querySelector("iframe");
      try {
        const data = JSON.parse(event.data);
        if (data.type === "message") {
          setMessages((prev) => [...prev, data.content]);
          iframe?.contentWindow?.postMessage({ 
            type: "response",
            content: data.content 
          }, "*");
        }
      } catch (err) {
        console.error("Invalid JSON from server:", event.data);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      console.log("WebSocket closed:", event.code, event.reason);
    };

    const handleIframeMessage = (event: MessageEvent) => {
      if (event.data?.type === "message" && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: "message",
          content: event.data.content
        }));
      }
    };

    window.addEventListener("message", handleIframeMessage);

    return () => {
      ws.close();
      window.removeEventListener("message", handleIframeMessage);
    };
  }, [agent?.id]);

  const widgetHtml = `
    <html>
      <head>
        <style>
          .chat-widget {
            background-color: ${color};
            width: 300px;
            height: 400px;
            border-radius: 10px;
            position: fixed;
            bottom: 20px;
            right: 20px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            display: flex;
            flex-direction: column;
            font-family: sans-serif;
          }

          .chat-header {
            background-color: #333;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 10px 10px 0 0;
            font-size: 16px;
          }

          .chat-body {
            flex-grow: 1;
            padding: 10px;
            overflow-y: auto;
            font-size: 14px;
            display: flex;
            flex-direction: column;
            gap: 6px;
          }

          .chat-input {
            display: flex;
            border-top: 1px solid #ccc;
            padding: 10px;
          }

          .chat-input input {
            flex-grow: 1;
            padding: 8px;
            border-radius: 5px;
            border: 1px solid #ccc;
          }

          .chat-input button {
            margin-left: 10px;
            padding: 8px 12px;
            background-color: #333;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
          }

          .message {
            display: flex;
          }

          .message.user {
            justify-content: flex-end;
          }

          .message.agent {
            justify-content: flex-start;
          }

          .message.user p {
            background-color: #dcf8c6;
            color: #000;
            padding: 8px 12px;
            border-radius: 16px 16px 0 16px;
            max-width: 75%;
            word-wrap: break-word;
          }

          .message.agent p {
            background-color: #fff;
            color: #000;
            padding: 8px 12px;
            border-radius: 16px 16px 16px 0;
            max-width: 75%;
            word-wrap: break-word;
            border: 1px solid #ddd;
          }
        </style>
      </head>
      <body>
        <div class="chat-widget">
          <div class="chat-header">${greeting}</div>
          <div class="chat-body">
            <div class="message agent">
              <p>Welcome! You are chatting with ${agentName}.</p>
            </div>
            <div id="messages"></div>
          </div>
          <div class="chat-input">
            <input id="messageInput" type="text" placeholder="Type a message..." />
            <button onclick="sendMessage()">Send</button>
          </div>
        </div>
        <script>
          function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (message) {
              window.parent.postMessage({ 
                type: "message",
                content: message 
              }, "*");
              input.value = '';
              appendMessage(message, "user");
            }
          }

          function appendMessage(content, sender) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = \`message \${sender}\`;
            
            const p = document.createElement('p');
            p.innerText = sender === "user" ? \`You: \${content}\` : \`\${content}\`;
            messageDiv.appendChild(p);
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
          }

          window.addEventListener("message", function(event) {
            if (event.data?.type === "response") {
              appendMessage(event.data.content, "agent");
            }
            if (event.data?.error) {
              appendMessage("❌ " + event.data.error, "agent");
            }
          });
        </script>
      </body>
    </html>
  `;

  const embedCode = `<script src="https://localhost:3000/embed-loader.js" data-agent="${agent?.id}" data-color="${color}" data-greeting="${greeting}" data-name="${agentName}"></script>`;

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold">Customize & Embed Chat Widget</h3>

      <div className="space-y-2">
        <div>
          <label className="block text-sm font-medium">Agent Name</label>
          <input
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Greeting Message</label>
          <input
            value={greeting}
            onChange={(e) => setGreeting(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Theme Color</label>
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="h-10 w-20 border border-gray-300 rounded"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Visibility</label>
          <div className="flex gap-4 items-center">
            <label className="flex items-center gap-1">
              <input
                type="radio"
                name="visibility"
                checked={isPublic}
                onChange={() => setIsPublic(true)}
              />
              Enable
            </label>
            <label className="flex items-center gap-1">
              <input
                type="radio"
                name="visibility"
                checked={!isPublic}
                onChange={() => setIsPublic(false)}
              />
              Disable
            </label>
          </div>
        </div>
      </div>

      <div className="my-4">
        <button
          onClick={() => setShowWidget(!showWidget)}
          className="bg-green-600 text-white px-4 py-2 rounded"
        >
          {showWidget ? "Hide Widget" : "Show Widget"}
        </button>
        <span className="ml-2 text-sm">
          {isConnected ? "🟢 Connected" : "🔴 Disconnected"}
        </span>
      </div>

      {showWidget && (
        <iframe
          srcDoc={widgetHtml}
          style={{
            width: "100%",
            height: "500px",
            border: "1px solid #ccc",
            borderRadius: "12px",
          }}
          title="Chat widget preview"
        />
      )}

      <div>
        <label className="block text-sm font-medium mb-1">Embed Code</label>
        <textarea
          value={embedCode}
          readOnly
          className="w-full p-2 border border-gray-300 rounded font-mono"
          rows={5}
        />
      </div>
    </div>
  );
};

const AnalysisTabContent = () => <div>Analysis settings go here...</div>;

export default AgentEditor;