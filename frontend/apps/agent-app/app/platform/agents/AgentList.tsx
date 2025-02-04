"use client";

import { useState } from "react";
import { useRouter } from "next/navigation"; //HZ: Import useRouter to enable client-side navigation
import { Agent } from "../../types/agent";

interface AgentListProps {
  agents: Agent[];
}

const AgentList: React.FC<AgentListProps> = ({ agents }) => {
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);

  //HZ: Initialize the useRouter hook to handle navigation programmatically
  const router = useRouter(); //HZ: This hook is used to navigate between pages

  return (
    <div className="p-4 space-y-2">
      {/* Button to navigate to the Create Agent page */}
      <button
        className="w-full py-2 px-4 bg-green-600 text-white hover:bg-green-700"
        //HZ: onClick calls router.push to navigate to /agents/CreateAgent
        onClick={() => router.push("/platform/agents/CreateAgent")} //HZ: Trigger navigation when clicked
      >
        Create Agent
      </button>

      {/* Render list of agents */}
      {agents.map((agent) => (
        <div
          key={agent.id} //HZ: Use agent id as the key for React's list rendering
          className={`py-2 px-4 rounded cursor-pointer ${
            selectedAgentId === agent.id
              ? "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200"
              : "hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-400"
          }`}
          //HZ: When an agent is clicked, set it as the selected agent
          onClick={() => setSelectedAgentId(agent.id)} // Handle selection of agent
        >
          {agent.name} {/* Display the name of the agent */}
        </div>
      ))}
    </div>
  );
};

export default AgentList; // Export the component so it can be used elsewhere
