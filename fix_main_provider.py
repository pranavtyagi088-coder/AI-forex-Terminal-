from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
main_tsx = ROOT / "frontend/src/main.tsx"

new_main_content = '''import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 3000,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
'''

main_tsx.write_text(new_main_content, encoding="utf-8")
print("[SUCCESS] frontend/src/main.tsx wrapped with QueryClientProvider!")
