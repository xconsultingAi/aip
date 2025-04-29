"use client";

import { useState, useEffect } from "react";
import { Agent } from "../../types/agent";
import { useAuth } from "@clerk/nextjs";
const tabs = ["Model", "Knowledgebase", "Advanced", "Analysis"];

interface AgentEditorProps {
  agent: Agent | null;
}

const AgentEditor: React.FC<AgentEditorProps> = ({ agent }) => {
  const [activeTab, setActiveTab] = useState("Model");
  const [agentData, setAgentData] = useState<Agent | null>(agent);
  const { getToken } = useAuth();
  

  //HZ: Model Tab State
  const [modelConfig, setModelConfig] = useState({
    firstMessage: "",
    provider: "OpenAI",
    model: "gpt-3.5-turbo",
    maxLength: 100,
    temperature: 0.7,
  });

  //HZ: Knowledge Base Tab State
  const [selectedKnowledgeBaseIds, setSelectedKnowledgeBaseIds] = useState<number[]>([]);

  //HZ: Update states when agent changes
  useEffect(() => {
    setAgentData(agent);
    if (agent) {
      setModelConfig((prev) => ({
        ...prev,
        firstMessage: agent.description || "",
      }));
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
  
      alert("Configuration saved successfully!");
    } catch (error) {
      console.error("Error saving configuration:", error);
      alert("Error saving configuration.");
    }
  };

  if (!agentData) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-500">
        Select an agent to edit
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-gray-200 dark:bg-gray-800 p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          {agentData.name}
        </h2>
        <button onClick={handlePublish} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
          Publish
        </button>
      </div>

      <div className="flex space-x-4 border-b border-gray-300 dark:border-gray-700  mb-4">
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
        {activeTab === "Advanced" && <AdvancedTabContent />}
        {activeTab === "Analysis" && <AnalysisTabContent />}
      </div>
    </div>
  );
};

export default AgentEditor;

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

  return (
    <div className="space-y-2">
      {knowledgeBase.length === 0 ? (
        <div className="text-gray-500 text-center">
          No knowledge base available
        </div>
      ) : (
        knowledgeBase.map((file) => (
          <button
            key={file.id}
            className={`block w-full p-2 text-left rounded ${
              selectedIds.includes(file.id)
                ? "bg-green-500 text-white"
                : "bg-gray-200 text-gray-700"
            }`}
            onClick={() => toggleSelection(file.id)}
          >
            {file.filename} {/* ✅ Fix: Use `filename` instead of `name` */}
          </button>
        ))
      )}
    </div>
  );
};


const AdvancedTabContent = () => <div>Advanced settings go here...</div>;
const AnalysisTabContent = () => <div>Analysis settings go here...</div>;
