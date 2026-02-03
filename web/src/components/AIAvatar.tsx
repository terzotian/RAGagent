import React from 'react';
import { Image } from 'react-bootstrap';

interface AIAvatarProps {
  loading?: boolean;
}

const AIAvatar: React.FC<AIAvatarProps> = ({ loading = false }) => {
  return (
    <div
      className="avatar ai me-3 shadow-sm d-flex align-items-center justify-content-center overflow-hidden"
      style={{
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        backgroundColor: '#fff',
        position: 'relative'
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          animation: loading ? 'spin 2s linear infinite' : 'none',
          transition: 'all 0.3s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <Image
          src="/ai_logo.png"
          alt="AI Avatar"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
        />
      </div>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default AIAvatar;
