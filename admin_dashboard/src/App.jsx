import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import DashboardOverview from './components/DashboardOverview';
import SchemeManagement from './components/SchemeManagement';
import UserManagement from './components/UserManagement';
import ApplicationMonitoring from './components/ApplicationMonitoring';
import SubscriptionMonitoring from './components/SubscriptionMonitoring';
import DocumentIntelligence from './components/DocumentIntelligence';
import SystemConfiguration from './components/SystemConfiguration';
import LoginView from './components/LoginView';
import './App.css';

function MainLayout() {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');

  if (!isAuthenticated) {
    return <LoginView />;
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return <DashboardOverview />;
      case 'schemes':
        return <SchemeManagement />;
      case 'users':
        return <UserManagement />;
      case 'applications':
        return <ApplicationMonitoring />;
      case 'subscriptions':
        return <SubscriptionMonitoring />;
      case 'documents':
        return <DocumentIntelligence />;
      case 'settings':
        return <SystemConfiguration />;
      default:
        return <DashboardOverview />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />
      <div className="main-content">
        <Header />
        <main className="dashboard-body">{renderContent()}</main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  );
}
