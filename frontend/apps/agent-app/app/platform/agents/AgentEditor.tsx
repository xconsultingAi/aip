"use client";

import { useState, useEffect } from "react";
import { Agent } from "../../types/agent";

const tabs = ["Model", "Knowledgebase", "Advanced", "Analysis"];

interface AgentEditorProps {
  agent: Agent | null;
}

// HZ: Modified `AgentEditor` to update when a new agent is selected
const AgentEditor: React.FC<AgentEditorProps> = ({ agent }) => {
  const [activeTab, setActiveTab] = useState("Model");
  const [agentData, setAgentData] = useState<Agent | null>(agent);

  // HZ: Ensure the editor updates when a new agent is clicked
  useEffect(() => {
    setAgentData(agent);
  }, [agent]);

  if (!agentData) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-500">
        Select an agent to edit
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-gray-200 dark:bg-gray-800 p-4">
      {/* MJ: Editor Header */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          {agentData.name} {/* HZ: Dynamically updating agent name */}
        </h2>
        <button className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
          Publish
        </button>
      </div>

      {/* MJ: Editor Tabs */}
      <div className="flex space-x-4 border-b border-gray-300 dark:border-gray-700 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === tab
                ? "text-green-600 border-b-2 border-green-600"
                : "text-gray-500 hover:text-gray-700 dark:text-gray-400"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* MJ: Tab Content Rendering */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-200 dark:bg-gray-800">
        {activeTab === "Model" && <ModelTabContent agent={agentData} />}
        {activeTab === "Knowledgebase" && <KBTabContent agent={agentData}/>}
        {activeTab === "Advanced" && <AdvancedTabContent />}
        {activeTab === "Analysis" && <AnalysisTabContent />}
      </div>
    </div>
  );
};

export default AgentEditor;

// HZ: Updated ModelTabContent to use a controlled component for `description`
const ModelTabContent = ({ agent }: { agent: Agent }) => {
  const [firstMessage, setFirstMessage] = useState(agent.description || "");

  // HZ: Update description when agent changes
  useEffect(() => {
    setFirstMessage(agent.description || "");
  }, [agent]);

  return (
    <div className="space-y-2 bg-gray-100 p-6 rounded-lg shadow-lg">
      <div>
        <label className="block text-sm font-medium">First Message</label>
        <textarea
          className="w-full p-2 border bg-gray-100 dark:bg-gray-900 border-gray-300 dark:border-gray-700 rounded"
          placeholder="This is a blank template..."
          value={firstMessage} // HZ: Controlled component (fixes issue)
          onChange={(e) => setFirstMessage(e.target.value)}
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Provider</label>
        <select className="w-full p-2 border border-gray-300 dark:border-gray-700 rounded">
          <option>OpenAI</option>
          <option>Other Provider</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium">Model</label>
        <select className="w-full p-2 border border-gray-300 dark:border-gray-700 rounded">
          <option>gpt-3.5-turbo</option>
          <option>gpt-4</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium">Temperature</label>
        <input type="range" min="0" max="1" step="0.1" className="w-full" />
      </div>
    </div>
  );
};

// MJ: Placeholder components for additional tabs
const KBTabContent = ({ agent }: { agent: Agent }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append("file", selectedFile);

    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      setUploadedFiles((prev) => [...prev, data.file]);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center text-center bg-gray-100 p-6 rounded-lg shadow-lg">
      <h3 className="text-lg font-bold mb-2">Upload Knowledge Base</h3>
      <input type="file" accept=".pdf,.txt" onChange={handleFileChange} className="mb-2" />
      <button
        onClick={handleUpload}
        className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
      >
        Upload
      </button>
      <h4 className="mt-4 text-md font-semibold">Uploaded Files</h4>
      <ul>
        {uploadedFiles.map((file, index) => (
          <li key={index} className="text-sm text-gray-700 dark:text-gray-300">{file}</li>
        ))}
      </ul>
    </div>
  );
};

const AdvancedTabContent = () => <div>Advanced settings go here...</div>;
const AnalysisTabContent = () => <div>Analysis settings go here...</div>;
