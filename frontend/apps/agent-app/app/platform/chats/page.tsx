"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import EmptyState from "../../../components/custom/empty-state";
import { UserGroupIcon } from "@heroicons/react/24/solid";
import ChatInterface from "./ChatInterface";
import ChatHistory from "./ChatHistory";

const SectionPage = () => {
  const { section } = useParams();
  const [view, setView] = useState<"empty" | "chat" | "history">("empty");

  const handlePrimaryAction = () => {
    console.log("Create New Chat clicked");
    setView("chat"); //HZ: Show ChatInterface when the button is clicked
  };

  const handleSecondaryAction = () => {
    console.log("History clicked");
    setView("history"); 
    //HZ: Add logic for handling the History button click
  };

  const handleBack = () => {
    setView("empty"); //HZ: Go back to the main screen
  };

  return (
    <div className="p-6 h-full">
      {view === "chat" ? (
        <ChatInterface onBack={handleBack} />
      ) : view === "history" ? (
        <ChatHistory onBack={handleBack} />
      ) : (
        <EmptyState
          icon={<UserGroupIcon className="w-12 h-12 text-gray-300" />}
          title={<span className="text-black">{section?.toString() || "Chats"}</span>}
          description="Chats show your conversation history..."
          primaryAction={{
            label: "Create New Chat",
            onClick: handlePrimaryAction,
          }}
          secondaryAction={{
            label: "History",
            onClick: handleSecondaryAction,
          }}
        />
      )}
    </div>
  );
};

export default SectionPage;