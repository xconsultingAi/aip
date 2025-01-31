"use client"
import { useParams } from "next/navigation";
import EmptyState from "../../../components/custom/empty-state";
import { UserGroupIcon } from "@heroicons/react/24/solid";

const SectionPage = () => {
  const { section } = useParams(); 
  
  const handlePrimaryAction = () => {
    console.log("Create Assistant clicked");
  };

  const handleSecondaryAction = () => {
    console.log("History clicked");
  };
  
  

  return (
    <div className="p-6 h-full">
    <EmptyState
      icon={<UserGroupIcon className="w-12 h-12 text-gray-300" />}
      title={section?.toString() || "Default Title"}
      description= "Chats show your conversation history..."
      primaryAction={{
        label: "Create New Chat",
        onClick: handlePrimaryAction,
      }}
      secondaryAction={{
        label: "History",
        onClick: handleSecondaryAction,
      }}
    />
  </div>
  );
};


export default SectionPage;

