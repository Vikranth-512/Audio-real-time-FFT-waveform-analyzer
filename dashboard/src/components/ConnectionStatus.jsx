import React from 'react';

const ConnectionStatus = ({ isConnected, status }) => {
    const getStatusColor = () => {
        if (isConnected) return '#4DA3FF';
        if (status.includes('Reconnecting')) return '#FFA500';
        if (status.includes('Error') || status.includes('failed')) return '#ff4444';
        return '#666666';
    };

    return (
        <div className="connection-status">
            <div
                className={`status-indicator ${!isConnected ? 'disconnected' : ''}`}
                style={{ backgroundColor: getStatusColor() }}
            />
        </div>
    );
};

export default ConnectionStatus;
