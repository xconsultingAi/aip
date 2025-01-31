"use client";

import { useState } from "react";
import { Agent } from "../../types/agent";

interface AgentListProps {
  agents: Agent[];
}

const AgentList: React.FC<AgentListProps> = ({ agents }) => {
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);

  return (
    <div className="p-4 space-y-2 ">
      <button className="w-full py-2 px-4 bg-green-600 text-white  hover:bg-green-700">
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
          onClick={() => setSelectedAgentId(agent.id)}
        >
          {agent.name}
        </div>
      ))}
    </div>
  );
};

export default AgentList;
