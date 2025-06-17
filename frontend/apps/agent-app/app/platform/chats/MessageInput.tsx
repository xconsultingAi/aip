"use client";

interface MessageInputProps {
  newMessage: string;
  setNewMessage: (value: string) => void;
  sendMessage: () => void;
}

const MessageInput: React.FC<MessageInputProps> = ({
  newMessage,
  setNewMessage,
  sendMessage,
}) => {
  return (
    <div className="flex space-x-2">
      <input
        type="text"
        className="flex-grow rounded p-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={newMessage}
        onChange={(e) => setNewMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
          }
        }}
        placeholder="Type your message..."
      />
      <button
        onClick={sendMessage}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Send
      </button>
    </div>
  );
};

export default MessageInput;
