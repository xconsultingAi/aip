"use client";

// ************************************************************
// MJ: This is a standard Menu Group component that can be used
// in any sidebar or dropdown menu
// ************************************************************

import React, { useState } from "react";
import { ChevronDownIcon, ChevronRightIcon } from "@heroicons/react/24/solid";

interface CollapsibleMenuProps {
  title: string;
  menuItems: React.ReactNode; 
  defaultOpen?: boolean;
}

const MenuGroup: React.FC<CollapsibleMenuProps> = ({
  title,
  menuItems,
  defaultOpen = false,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  return (
    <li>
      <div
        className="flex items-center justify-between p-2 hover:bg-gray-200 dark:hover:bg-gray-800 rounded cursor-pointer"
        onClick={toggleMenu}
      >
        <span className="flex items-center space-x-2">
          <ChevronRightIcon
            className={`w-5 h-5 transition-transform ${
              isOpen ? "rotate-90" : ""
            }`}
          />
          <span>{title}</span>
        </span>
        {isOpen ? (
          <ChevronDownIcon className="w-4 h-4" />
        ) : (
          <ChevronRightIcon className="w-4 h-4" />
        )}
      </div>
      {isOpen && <ul className="ml-6 mt-1 space-y-1">{menuItems}</ul>}
    </li>
  );
};

export default MenuGroup;
