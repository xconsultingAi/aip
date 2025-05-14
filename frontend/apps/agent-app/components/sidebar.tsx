"use client";

// ************************************************************
// MJ: This is a standard Sidebar for the app
// *******
import React, { useState, useEffect } from "react";
import MenuItem from "./custom/menu-item";
import ToggleTheme from "./custom/theme-toggle";
import {
    HomeIcon,
    UserGroupIcon,
    ChatBubbleLeftIcon,
    BookOpenIcon,
    
} from "@heroicons/react/24/solid";
import { UserButton, useUser } from "@clerk/nextjs";
import MenuGroup from "./custom/menu-group";
import ThemeToggle from "./custom/theme-toggle";


const Sidebar = () => {

    const [platformMenuOpen, setPlatformMenuOpen] = useState(false);
    const { user } = useUser();

    // Load state from localStorage on component mount
    useEffect(() => {
        const savedPlatformState = localStorage.getItem("platformMenuOpen");
        if (savedPlatformState !== null) {
            setPlatformMenuOpen(savedPlatformState === "true");
        }
    }, []);



    return (
        <aside className="w-64 h-screen bg-gray-100 dark:bg-gray-900 text-grey-900 dark:text-gray-400 flex flex-col">
            {/* Logo */}
            <div className="p-4 flex items-center justify-between">
            
                <h1 className="text-xl font-bold text-grey-900 dark:text-white">{process.env.NEXT_PUBLIC_APP_NAME || "AIP"}</h1>
                <ToggleTheme />
            </div>

            <nav className="flex-grow overflow-y-auto">
                <ul className="space-y-1 p-4 text-sm">
                    {/* Overview */}
                    <li>
                        <MenuItem label="Overview" icon={<HomeIcon />} path="/" />
                    </li>

                    {/* Platform Menu */}
                    <MenuGroup
                        title="Platform"
                        menuItems={
                            <>
                                <MenuItem label="Agents" icon={<UserGroupIcon />} path="/platform/agents" />
                                <MenuItem label="Chats" icon={<ChatBubbleLeftIcon />} path="/platform/chats" />
                                <MenuItem label="Knowledgebase" icon={<BookOpenIcon />} path="/platform/knowledgebase" />
                                <MenuItem label="URL Scraping" icon={<BookOpenIcon />} path="/platform/urlscraping" />
                            </>
                        }
                        defaultOpen={true} // Optional, to make this menu open by default
                    />

                    {/* Activity Menu */}
                    <MenuGroup
                        title="Activity"
                        menuItems={
                            <>
                                <MenuItem label="Agent Access Log" icon={<UserGroupIcon />} path="/platform/access" />
                                <MenuItem label="Widget Log" icon={<ChatBubbleLeftIcon />} path="/platform/widget" />
                                
                            </>
                        }
                        defaultOpen={true} // Optional, to make this menu open by default
                    />
                    {/* Settings Menu */}
                    <MenuGroup
                        title="Settings"
                        menuItems={
                            <>
                                <MenuItem label="Organization" icon={<UserGroupIcon />} path="/organization" />
                                {/* <MenuItem label="Widget Log" icon={<ChatBubbleLeftIcon />} path="/platform/widget" /> */}
                                
                            </>
                        }
                        defaultOpen={true} // Optional, to make this menu open by default
                    />

                    {/* Add more collapsible menus */}
                    {/* Example */}
                    {/* <CollapsibleMenu title="Another Menu" menuItems={<MenuItem ... />} /> */}
                </ul>
            </nav>

            {/* Profile */}
            <div className="p-4">
                <div className="flex items-center space-x-2">
                    <UserButton />
                    <div>
                        <p className="text-sm text-gray-700 dark:text-gray-300">{user?.fullName}</p>
                        <p className="text-xs text-gray-600 dark:text-gray-500">{user?.primaryEmailAddress?.emailAddress}</p>
                    </div>
                </div>
                
            </div>
        </aside>
    );
};

export default Sidebar;
