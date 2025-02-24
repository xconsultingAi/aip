"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Agent } from "../../types/agent";

interface AgentListProps {
  agents: Agent[];
  onSelectAgent: (agent: Agent) => void;
}

// HZ: Allow selecting an agent and passing it up
const AgentList: React.FC<AgentListProps> = ({ agents, onSelectAgent }) => {
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const router = useRouter();

  return (
    <div className="p-4 space-y-2">
      <button
        className="w-full py-2 px-4 bg-green-600 text-white hover:bg-green-700"
        onClick={() => router.push("/platform/agents/CreateAgent")}
      >
        Create Agent
      </button>

      {agents.map((agent) => (
        <div
          key={agent.id}
          className={`py-2 px-4 rounded cursor-pointer ${
            selectedAgentId === agent.id
              ? "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200"
              : "hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-400"
          }`}
          onClick={() => {
            setSelectedAgentId(agent.id);
            onSelectAgent(agent); // HZ: Notify parent
          }}
        >
          {agent.name}
        </div>
      ))}
    </div>
  );
};

export default AgentList;
