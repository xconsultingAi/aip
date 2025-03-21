"use client";

import { useState } from "react";
import AgentList from "./AgentList";
import AgentEditor from "./AgentEditor";
import { Agent } from "../../types/agent";
import { useRouter } from "next/navigation";

interface AgentListWrapperProps {
  agents: Agent[];
}

// HZ: Manage selected agent state
export default function AgentListWrapper({ agents }: AgentListWrapperProps) {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const router = useRouter();

  return (
    <div className="flex h-full bg-gray-200 dark:bg-gray-800">
      <div className="w-1/4 bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-400 rounded-lg">
        {agents.length === 0 ? (
          <div className="p-4">
            <button
              className="mt-4 w-full py-2 px-4 bg-green-600 text-white hover:bg-green-700"
              onClick={() => router.push("/platform/agents/CreateAgent")}
            >
              Create Agent
            </button>
            <p className="mt-4 text-gray-500 dark:text-gray-300 text-center flex h-full items-center justify-center">
              No agents found. Click below to create your first agent.
            </p>
          </div>
        ) : (
          <AgentList agents={agents} onSelectAgent={setSelectedAgent} />
        )}
      </div>

      <div className="w-3/4 bg-gray-100 dark:bg-gray-800">
        <AgentEditor agent={selectedAgent} />
      </div>
    </div>
  );
}
