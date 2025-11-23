import './style';
import { useEffect, useState } from 'preact/hooks';
import { RelayControls } from './sections/RelayControls';
import { DialogPortalRoot } from './components/Dialog';
import { GlobalInfo } from './sections/GlobalInfo';
import { SensorInfo } from './sections/SensorInfo';
import { WifiForm } from './sections/WifiForm';
import { RestartButton } from './sections/RestartButton';
import { Settings } from './sections/Settings';

export default function App() {
  const name = getName();

  // set tab name:
  useEffect(() => {
    document.title = `${name}`;
  }, [name]);

  return (
    <>
      <div className="app-root">
        <h1>{name}</h1>
        <hr />
        <RelayControls />
        <hr />
        <GlobalInfo />
        <hr />
        <SensorInfo />
        <hr />
        <Settings />
        <hr />
        <WifiForm />
        <hr />
        <RestartButton />
      </div>

      <DialogPortalRoot />
    </>
  );
}
/**
 * Get the domain name of the current page.
 */
const getName = () => {
  // get domain name: eg. http://sunroom2.local -> sunroom2

  const rawDomain = window.location.hostname.split('.')?.[0];

  if (!rawDomain) {
    return 'Unknown';
  }

  // capitalize first letter
  return rawDomain.charAt(0)?.toUpperCase() + rawDomain.slice(1);
};
