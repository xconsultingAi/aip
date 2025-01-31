"use client";

import { useState } from "react";

const tabs = ["Model", "Knowledgebase", "Advanced", "Analysis"];

const AgentEditor = () => {
    const [activeTab, setActiveTab] = useState("Model");

    return (
        <div className="w-full h-full flex flex-col bg-gray-200 dark:bg-gray-800 p-4 ">
            {/* MJ: Editor Header */}
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Agent 1</h2>
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
                        className={`px-4 py-2 text-sm font-medium ${activeTab === tab
                                ? "text-green-600 border-b-2 border-green-600"
                                : "text-gray-500 hover:text-gray-700 dark:text-gray-400"
                            }`}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            
            <div className="flex-1 overflow-y-auto p-4 bg-gray-200 dark:bg-gray-800 ">
                {activeTab === "Model" && <ModelTabContent />}
                {activeTab === "Knowledgebase" && <KBTabContent />}

                {activeTab === "Advanced" && <AdvancedTabContent />}
                {activeTab === "Analysis" && <AnalysisTabContent />}
            </div>
        </div>
    );
};

export default AgentEditor;


const ModelTabContent = () => (
    <div className="space-y-4">
        <div>
            <label className="block text-sm font-medium">First Message</label>
            <textarea
                className="w-full p-2 border bg-gray-100 dark:bg-gray-900  border-gray-300 dark:border-gray-700 rounded"
                placeholder="This is a blank template..."
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
            <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                className="w-full"
            />
        </div>
    </div>
);

const KBTabContent = () => <div>Knowledgebase settings go here...</div>;
const AdvancedTabContent = () => <div>Advanced settings go here...</div>;
const AnalysisTabContent = () => <div>Analysis settings go here...</div>;
