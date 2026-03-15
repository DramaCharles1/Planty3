import React from 'react';

function CommandHistory({ commands }) {
  if (commands.length === 0) {
    return <div className="empty-state">No commands sent yet.</div>;
  }

  const getStatusBadge = (status) => {
    const statusClasses = {
      acknowledged: 'status-badge success',
      pending: 'status-badge warning',
      failed: 'status-badge error',
    };
    return <span className={statusClasses[status] || 'status-badge'}>{status}</span>;
  };

  return (
    <div className="command-history">
      <table className="command-table">
        <thead>
          <tr>
            <th>Command ID</th>
            <th>Command</th>
            <th>Sent At</th>
            <th>Status</th>
            <th>Acknowledged At</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          {commands.map((cmd) => (
            <tr key={cmd.id}>
              <td className="cmd-id">{cmd.cmd_id}</td>
              <td>{cmd.command}</td>
              <td>{new Date(cmd.sent_at).toLocaleString()}</td>
              <td>{getStatusBadge(cmd.status)}</td>
              <td>{cmd.ack_at ? new Date(cmd.ack_at).toLocaleString() : '—'}</td>
              <td className="error-cell">{cmd.error || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default CommandHistory;
