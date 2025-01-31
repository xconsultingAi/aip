"use client";
// ************************************************************
// MJ: This is a standard Menu Item component that can be used
// in any sidebar 
// ************************************************************

import React, { useState } from "react";
import { usePathname, useRouter } from "next/navigation";

interface MenuItemProps {
  label: string;
  icon: React.ReactNode;
  path: string;
}

const MenuItem: React.FC<MenuItemProps> = ({ label, icon, path }) => {
  const pathname = usePathname();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (pathname !== path) {
      setLoading(true);
      try {
        await router.push(path); 
        //MJ: Simulate the loading state
        await new Promise(resolve => setTimeout(resolve, 300));
      } catch (error) {
        setLoading(false);
      } finally {

       setLoading(false);
       
      }
    }
  };

  const isActive = pathname === path;


  return (
    <div
      className={`flex items-center space-x-2 p-2 rounded cursor-pointer ${isActive ? "bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-white" : "hover:bg-gray-200 dark:hover:bg-gray-800"
        }`}
      onClick={handleClick}
    >
      <div className="w-5 h-5">{icon}</div>
      <span>{label}</span>
      {loading && (
        <svg
          className="w-4 h-4 animate-spin ml-auto text-gray-900 dark:text-white"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v8H4z"
          ></path>
        </svg>
      )}
    </div>
  );
};

export default MenuItem;
