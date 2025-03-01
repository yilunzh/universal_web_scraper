import ChatInterface from '@/components/chat-interface';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between bg-gray-50">
      <div className="w-full h-full flex flex-col">
        <ChatInterface />
      </div>
    </main>
  );
}
