"use client";

// ************************************************************
// MJ: We will use this Empty state component to show a message 
// when there is no data to show
// ************************************************************
interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  primaryAction: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  primaryAction,
  secondaryAction,
}) => {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
      {/* Icon */}
      <div className="bg-gray-700 rounded-full p-4 mb-4">{icon}</div>

      {/* Title */}
      <h2 className="text-xl font-semibold text-white">{title}</h2>

      {/* Description */}
      <p className="mt-2 text-sm text-gray-400">{description}</p>

      {/* Buttons */}
      <div className="mt-6 flex space-x-4">
        <button
          onClick={primaryAction.onClick}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-white"
        >
          {primaryAction.label}
        </button>
        {secondaryAction && (
          <button
            onClick={secondaryAction.onClick}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-white"
          >
            {secondaryAction.label}
          </button>
        )}
      </div>
    </div>
  );
};

export default EmptyState;
