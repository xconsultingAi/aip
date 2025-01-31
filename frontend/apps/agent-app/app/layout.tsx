
import { ClerkProvider, SignedIn, SignedOut } from '@clerk/nextjs';
import { currentUser } from '@clerk/nextjs/server';
import Sidebar from "../components/sidebar";
import { Card } from "../components/ui/card";
import Footer from "../components/footer";
import './globals.css';
import Navbar from '@agent-app/components/navbar';

export const metadata = {
  title: 'Agent App',
  description: 'Your awesome app description here',
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {


  return (
    <ClerkProvider>
      <html lang="en">
        <body className="flex flex-col min-h-screen bg-gray-100 dark:bg-gray-900">
          <div className="flex flex-grow">
            <SignedIn>
              <Sidebar />
              <main className="flex-grow p-6">
                <Card className="p-6 h-full bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-300 border-gray-300 dark:border-gray-700">
                  {children}
                </Card>
              </main>
            </SignedIn>
            <SignedOut>
              <main className="flex-grow p-6 flex items-center justify-center">
                {children}
              </main>
            </SignedOut>
          </div>
          {/* Footer */}
          <Footer />
        </body>
      </html>
    </ClerkProvider>
  );
}
