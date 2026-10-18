import React from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import Keycloak, { KeycloakConfig, KeycloakInitOptions } from 'keycloak-js';
import ReportPage from './components/ReportPage';

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM || '',
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID || '',
};

const keycloak = new Keycloak(keycloakConfig);

// The Keycloak JS adapter generates a new code_verifier for each login attempt,
// sends its SHA-256 challenge during authorization and includes the verifier
// only when exchanging the authorization code for tokens.
const keycloakInitOptions: KeycloakInitOptions = {
  onLoad: 'check-sso',
  flow: 'standard',
  pkceMethod: 'S256',
  checkLoginIframe: false,
};

const App: React.FC = () => (
  <ReactKeycloakProvider
    authClient={keycloak}
    initOptions={keycloakInitOptions}
  >
    <div className="App">
      <ReportPage />
    </div>
  </ReactKeycloakProvider>
);

export default App;
