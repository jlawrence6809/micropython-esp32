import { Section } from '../components/Section';

/**
 * Wifi form is the form for setting the wifi name and password.
 */
export const WifiForm = () => {
  const onSubmit = async (e: Event) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const ssid = (form.querySelector('#ssid') as HTMLInputElement).value;
    const password = (form.querySelector('#password') as HTMLInputElement)
      .value;
    try {
      await fetch('/api/wifi/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid, password }),
      });
      alert('WiFi credentials sent. Device will attempt to connect.');
    } catch (err) {
      alert('Failed to send WiFi credentials');
    }
  };
  // @ts-ignore - onsubmit uses DOM event
  return (
    <Section title="Wifi Settings">
      <form className="WifiForm" onSubmit={onSubmit}>
        <div>
          <label for="ssid">Wifi Name</label>
          <input type="text" id="ssid" name="ssid" />
        </div>
        <div>
          <label for="password">Wifi Password</label>
          <input type="password" id="password" name="password" />
        </div>
        <button type="submit">Submit</button>
      </form>
    </Section>
  );
};
