
import './index.css';
import { ChatWindow } from './components/ChatWindow';

export default function App() {
  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ background: 'var(--bg-primary)' }}
    >
      {/* Background gradient blobs */}
      <div
        className="fixed inset-0 pointer-events-none"
        aria-hidden="true"
        style={{ zIndex: 0 }}
      >
        <div
          className="absolute"
          style={{
            top: '-20%', left: '-10%',
            width: '600px', height: '600px',
            background: 'radial-gradient(circle, rgba(59,157,255,0.07) 0%, transparent 70%)',
          }}
        />
        <div
          className="absolute"
          style={{
            bottom: '-20%', right: '-10%',
            width: '500px', height: '500px',
            background: 'radial-gradient(circle, rgba(34,211,238,0.05) 0%, transparent 70%)',
          }}
        />
      </div>

      {/* Main chat panel */}
      <main
        className="relative flex-1 flex flex-col max-w-4xl mx-auto w-full"
        style={{ zIndex: 1 }}
      >
        <div className="flex-1 flex flex-col glass-card m-4 overflow-hidden">
          <ChatWindow />
        </div>
      </main>
    </div>
  );
}
