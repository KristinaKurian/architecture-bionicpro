import React from 'react';
import ReportPage from './components/ReportPage';

// No keycloak-js in the browser: all IdP tokens stay behind the BFF.
const App: React.FC = () => <ReportPage />;
export default App;
