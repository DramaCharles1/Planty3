import React, { useState } from 'react';

function CommandForm({ plantId, onCommandSent, onError }) {
  const [command, setCommand] = useState('water');
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!command.trim()) {
      onError('Please select a command');
      return;
    }

    setSending(true);

    try {
      const { sendCommand } = await import('../api/client');
      const result = await sendCommand(plantId, command);
      onCommandSent(result);
      // Reset form
      setCommand('water');
    } catch (err) {
      console.error('Failed to send command:', err);
      onError(err.response?.data?.error || 'Failed to send command. Please try again.');
    } finally {
      setSending(false);
    }
  };

  return (
    <form className="command-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="command">Send Command:</label>
        <select
          id="command"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          disabled={sending}
        >
          <option value="water">Water</option>
          <option value="calibrate">Calibrate</option>
          <option value="reset">Reset</option>
        </select>
      </div>
      <button type="submit" className="btn-primary" disabled={sending}>
        {sending ? 'Sending...' : 'Send Command'}
      </button>
    </form>
  );
}

export default CommandForm;
