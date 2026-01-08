import React from 'react';
// Importe seus ícones (ex: lucide-react ou heroicons)
import { LayoutDashboard, LogOut, Settings } from 'lucide-react';
import './styles.css'; // Importe o CSS global

// Exemplo de componente Sidebar
const Sidebar = () => {
    const menuItems = [
        { path: '/dashboard', label: 'Início', icon: LayoutDashboard },
        { path: '/configuracoes', label: 'Configurações', icon: Settings },
    ];

    // Simulação de navegação (Substitua por react-router-dom Link)
    const navigate = (path) => console.log('Navegar para:', path);
    const currentPath = '/dashboard';

    return (
        <div className="sidebar">
            {/* Header da Sidebar */}
            <div style={{ padding: '0 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '12px',
                    background: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '4px',
                    boxShadow: 'var(--shadow-sm)',
                    border: '1px solid #eee'
                }}>
                    {/* Logo */}
                    <span style={{ fontSize: '2rem' }}>🏦</span>
                </div>
                <div>
                    <h1 style={{ color: 'var(--primary)', fontWeight: 900, fontSize: '1.4rem', lineHeight: 1 }}>SeuBanco</h1>
                    <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Painel Administrativo</p>
                </div>
            </div>

            {/* Menu Principal com Scroll */}
            <nav className="sidebar-nav">
                {menuItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = currentPath === item.path;
                    return (
                        <a
                            key={item.path}
                            onClick={() => navigate(item.path)}
                            className={`nav-item ${isActive ? 'active' : ''}`}
                            style={{ cursor: 'pointer' }}
                        >
                            <Icon size={24} />
                            <span>{item.label}</span>
                        </a>
                    );
                })}
            </nav>

            {/* Footer Fixo */}
            <div className="sidebar-footer">
                <button
                    className="nav-item"
                    style={{ border: 'none', background: 'none', width: '100%', cursor: 'pointer', color: 'var(--danger)' }}
                    onClick={() => alert('Saindo...')}
                >
                    <LogOut size={24} />
                    <span>Sair</span>
                </button>
            </div>
        </div>
    );
};

// Layout Principal
export const Layout = ({ children }) => {
    return (
        <div className="app-layout">
            <Sidebar />
            <div className="main-content">
                {children}
            </div>
        </div>
    );
};
