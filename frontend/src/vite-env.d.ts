/// <reference types="vite/client" />

// Google Identity Services (GIS) SDK - loaded via CDN in index.html
interface Window {
  google?: {
    accounts: {
      id: {
        initialize: (config: {
          client_id: string;
          callback: (response: { credential: string }) => void;
        }) => void;
        prompt: () => void;
      };
    };
  };
}
