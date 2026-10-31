import React from 'react';

export default function PlaceholderView({ title, phase, description }) {
  return (
    <div className="placeholder-container">
      <div className="placeholder-icon">🚧</div>
      <h3>{title}</h3>
      <p style={{ fontWeight: 600, color: 'var(--primary-color)', marginBottom: '0.5rem' }}>
        Scheduled for {phase}
      </p>
      <p>{description}</p>
    </div>
  );
}

