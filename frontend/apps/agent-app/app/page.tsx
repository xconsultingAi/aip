import { currentUser, auth } from "@clerk/nextjs/server";
import { Card } from "../components/ui/card";
import Sidebar from "../components/sidebar";

const HomePage = async () => {

  //MJ: ******** API TESTING CODE STARTS ***************
  const user = await currentUser();
  const { userId, getToken } = await auth() 
  const token = await getToken();

  console.log(token)
  const response = await fetch('http://127.0.0.1:8000/api/agents', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  
  const data = await response.json()

  if (!token) {
    throw new Error("Failed to get access token");
  }



  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Welcome!</h2>
      <p className="text-gray-700 dark:text-gray-400 mt-2">
        This is result of Backend API Call.
        {JSON.stringify(data)}
      </p>
    </div>
  );
};

//MJ: ******** API TESTING CODE ENDS ***************

export default HomePage;
