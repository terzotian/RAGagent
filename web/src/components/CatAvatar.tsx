import React from 'react';
import { useRive, Layout, Fit, Alignment } from '@rive-app/react-canvas';

const CatAvatar: React.FC = () => {
  const { RiveComponent } = useRive({
    src: '/cat_avatar.riv',
    autoplay: true,
    layout: new Layout({
      fit: Fit.Cover,
      alignment: Alignment.BottomCenter,
    }),
  });

  return (
    <div
      className="cat-avatar-container"
      style={{ 
        width: '200px', 
        height: '200px', 
        position: 'absolute',
        top: '-199px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 10,
        pointerEvents: 'none' // Ensure clicks pass through to input if needed, though it's above
      }}
    >
      <RiveComponent />
    </div>
  );
};

export default CatAvatar;
