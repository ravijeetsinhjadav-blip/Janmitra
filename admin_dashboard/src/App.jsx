import React, { useState } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import DashboardOverview from './components/DashboardOverview';
import PlaceholderView from './components/PlaceholderView';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return <DashboardOverview />;
      case 'schemes':
        return (
          <PlaceholderView
            title="Government Schemes Management"
            phase="Phase 2"
            description="Manage central and state government schemes, category tags, required documentation lists, and official application portal URLs."
          />
        );
      case 'documents':
        return (
          <PlaceholderView
            title="Document Intelligence & Verification"
            phase="Phase 3"
            description="Configure OCR document parsing guidelines, field extraction rules, and anomaly detection parameters."
          />
        );
      case 'eligibility':
        return (
          <PlaceholderView
            title="Citizen Eligibility Evaluation Engine"
            phase="Phase 4"
            description="Define demographic, income, and categorical rule sets for scoring citizen eligibility against published schemes."
          />
        );
      case 'readiness':
        return (
          <PlaceholderView
            title="Application Readiness & Checklists"
            phase="Phase 5"
            description="Review generated citizen readiness reports, completion metrics, and official portal redirection statistics."
          />
        );
      case 'settings':
        return (
          <PlaceholderView
            title="System & Environment Configuration"
            phase="Phase 1 (Active)"
            description="Backend API connected to http://127.0.0.1:8000. Environment parameters managed via .env configurations."
          />
        );
      default:
        return <DashboardOverview />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />
      <div className="main-content">
        <Header />
        <main className="dashboard-body">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}
