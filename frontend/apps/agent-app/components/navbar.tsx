// ************************************************************
// MJ: This is a standard Navbar for the app
// THIS COMPONENT IS NOT USED IN THE CURRENT LAYOUT
// ************************************************************

import React from "react";
import { UserButton, SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";
import { Button } from "./ui/button";
import ThemeToggle from "./custom/theme-toggle";

const Navbar = () => {
  return (
    <header className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-900 shadow-md">
      {/* App Icon and Name */}
      <div className="flex items-center space-x-2">
        <img
          src="/favicon.ico" // Replace with your app icon path
          alt="App Icon"
          className="w-8 h-8"
        />
        <span className="text-lg font-bold">Agent App</span>
      </div>

      {/* User Menu */}
      <div className="flex items-center space-x-4">
      <ThemeToggle />
      <SignedIn>
        {/* Mount the UserButton component */}
        <UserButton />
      </SignedIn>
      <SignedOut>
        {/* Signed out users get sign in button */}
        <SignInButton />
      </SignedOut>
      </div>
    </header>
  );
};

export default Navbar;
