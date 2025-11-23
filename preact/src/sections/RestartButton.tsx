import { useState } from 'preact/hooks';

const RESTART_SECONDS = 5;

/**
 * Restart button is the button for restarting the device.
 */
export const RestartButton = () => {
  const [restartSuccess, setRestartSuccess] = useState(false);

  return (
    <div>
      <button
        onClick={async () => {
          try {
            await fetch('/api/restart', { method: 'POST' });
            setRestartSuccess(true);
            setTimeout(() => {
              setRestartSuccess(false);
            }, RESTART_SECONDS * 1000);
          } catch (error) {
            console.error(error);
            alert('Error restarting');
          }
        }}
      >
        Reset
      </button>
      {restartSuccess && (
        <p>Success, restarting in {RESTART_SECONDS} seconds...</p>
      )}
    </div>
  );
};
