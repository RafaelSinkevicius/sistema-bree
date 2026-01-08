import React from 'react';

// Componente simples de feedback
export const InfoBox = ({ message }) => (
    <div className="guidance-box">
        <div className="guidance-title">DICA:</div>
        <div style={{ fontWeight: 600 }}>{message}</div>
    </div>
);

// Botão padrão do sistema
export const Button = ({ children, variant = 'primary', ...props }) => (
    <button className={`btn btn-${variant}`} {...props}>
        {children}
    </button>
);

// Cartão padrão com efeito de vidro
export const Card = ({ children, style, ...props }) => (
    <div className="card" style={style} {...props}>{children}</div>
);

// Modal reutilizável
export const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;
    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(4px)'
        }} onClick={onClose}>
            <div style={{
                backgroundColor: 'white',
                padding: '2rem',
                borderRadius: '16px',
                width: '90%',
                maxWidth: '600px',
                maxHeight: '90vh',
                overflowY: 'auto',
                boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)'
            }} onClick={e => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ fontWeight: 800, margin: 0 }}>{title}</h2>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#999' }}>&times;</button>
                </div>
                {children}
            </div>
        </div>
    );
};
