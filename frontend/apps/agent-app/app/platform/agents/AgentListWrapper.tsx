"use client";

import { useState } from "react";
import AgentList from "./AgentList";
import AgentEditor from "./AgentEditor";
import { Agent } from "../../types/agent";

interface AgentListWrapperProps {
  agents: Agent[];
}

// HZ: Manage selected agent state
export default function AgentListWrapper({ agents }: AgentListWrapperProps) {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  return (
    <div className="flex h-full bg-gray-200 dark:bg-gray-800">
      <div className="w-1/4 bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-400 rounded-lg">
        <AgentList agents={agents} onSelectAgent={setSelectedAgent} />
      </div>

      <div className="w-3/4 bg-gray-100 dark:bg-gray-800">
        <AgentEditor agent={selectedAgent} />
      </div>
    </div>
  );
}
