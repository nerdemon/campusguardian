import { useState, useEffect, useRef } from 'react';
import { Shield, MessageSquare, Send, MapPin, AlertTriangle, CheckCircle2, Activity, BrainCircuit, Wifi, LogIn, LogOut, Volume2, VolumeX, Download, Moon } from 'lucide-react';

const generateRandomMac = () => {
  return Array.from({length: 6}, () => Math.floor(Math.random()*256).toString(16).padStart(2, '0').toUpperCase()).join(':');
};

export default function App() {
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'System Online. Real-time telemetry linked. Ready for queries.', timestamp: new Date().toLocaleTimeString() }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [rooms, setRooms] = useState([]);
  
  // NEW: Voice & Logging State
  const [isMuted, setIsMuted] = useState(false);
  
  // NEW: Store AI evaluations for specific rooms
  const [aiInsights, setAiInsights] = useState({});
  
  // NEW: Stateful dynamic ledger for MAC addresses
  const activeMacsRef = useRef({});

  useEffect(() => {
    const fetchSensorData = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/sensors/latest');
        const result = await response.json();
        
        if (result.status === 'success' && result.data) {
          const formattedRooms = result.data.map(sensor => {
            const roomId = sensor.room_id || 'Unknown Room';
            const currentOcc = sensor.occupancy;
            
            // Dynamic MAC Logic: Grow or shrink the MAC list based on live occupancy
            if (!activeMacsRef.current[roomId]) activeMacsRef.current[roomId] = [];
            let currentMacs = [...activeMacsRef.current[roomId]];
            
            if (currentOcc > currentMacs.length) {
              // Devices connected (Check-in)
              const diff = currentOcc - currentMacs.length;
              for(let i=0; i<diff; i++) currentMacs.push(generateRandomMac());
            } else if (currentOcc < currentMacs.length) {
              // Devices disconnected (Check-out)
              currentMacs = currentMacs.slice(0, currentOcc);
            }
            activeMacsRef.current[roomId] = currentMacs;

            return {
              id: roomId,
              temp: sensor.temperature,
              occupancy: currentOcc,
              motion: sensor.motion,
              light_level: sensor.light_level,
              macs: currentMacs
            };
          });
          
          setRooms(formattedRooms);
        }
      } catch (error) {
        console.error("Failed to fetch live sensor data:", error);
      }
    };

    fetchSensorData();
    const intervalId = setInterval(fetchSensorData, 5000);
    return () => clearInterval(intervalId);
  }, []);

  // --- NEW: Text-to-Speech (TTS) ---
  const speakText = (text) => {
    if (isMuted || !window.speechSynthesis) return;
    window.speechSynthesis.cancel(); // Stop current speech
    const utterance = new SpeechSynthesisUtterance(text);
    // Try to find a good English voice
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.lang.includes('en-GB') || v.lang.includes('en-US'));
    if (preferredVoice) utterance.voice = preferredVoice;
    
    window.speechSynthesis.speak(utterance);
  };

  // --- NEW: Download Conversation Logs ---
  const downloadLogs = () => {
    const logHeader = "=== CampusGuardian AI Conversation Logs ===\nGenerated: " + new Date().toLocaleString() + "\n\n";
    const logContent = messages.map(m => `[${m.timestamp}] ${m.role.toUpperCase()}:\n${m.text}\n${m.source ? `Source: ${m.source}\n` : ''}`).join('\n');
    
    const blob = new Blob([logHeader + logContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `campus_guardian_logs_${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // --- NEW: Trigger Backend AI Evaluation ---
  const evaluateRoomWithAI = async (roomId) => {
    // Set loading state for this specific room
    setAiInsights(prev => ({ ...prev, [roomId]: { loading: true } }));

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/evaluate/${roomId}`, {
        method: 'POST'
      });
      const result = await response.json();

      if (result.status === 'success') {
        setAiInsights(prev => ({ ...prev, [roomId]: { loading: false, data: result.agent_analysis } }));
      } else {
        setAiInsights(prev => ({ ...prev, [roomId]: { loading: false, error: 'Evaluation failed' } }));
      }
    } catch (error) {
      setAiInsights(prev => ({ ...prev, [roomId]: { loading: false, error: 'Connection error' } }));
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input;
    const userTimestamp = new Date().toLocaleTimeString();
    setMessages((prev) => [...prev, { role: 'user', text: userMessage, timestamp: userTimestamp }]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/knowledge/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage }),
      });

      const data = await response.json();
      const aiTimestamp = new Date().toLocaleTimeString();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to get answer from AI server.');
      }
      
      setMessages((prev) => [...prev, { 
        role: 'ai', 
        text: data.answer || "I received an empty response from the AI model.",
        source: data.source,
        timestamp: aiTimestamp
      }]);
      
      // Speak the response aloud!
      if (data.answer) {
        speakText(data.answer);
      }
      
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'ai', text: `Error: ${error.message}`, timestamp: new Date().toLocaleTimeString() }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 font-sans">
      
      {/* LEFT PANEL: Campus Overview */}
      <div className="w-1/2 p-8 border-r border-slate-800 flex flex-col relative">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-8 h-8 text-emerald-400" />
          <h1 className="text-3xl font-bold text-white tracking-tight">Campus<span className="text-emerald-400">Guardian</span></h1>
        </div>

        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-slate-400 flex items-center gap-2">
            <MapPin className="w-5 h-5" /> Live Sensor Feed
            <span className="relative flex h-3 w-3 ml-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
          </h2>
        </div>
        
        <div className="flex flex-col gap-4 overflow-y-auto pr-2 pb-20">
          {rooms.length === 0 ? (
             <div className="text-slate-500 italic p-4">Waiting for sensor data...</div>
          ) : (
            rooms.map((room, idx) => {
              const insight = aiInsights[room.id];
              const isCritical = insight?.data?.risk_level === 'Critical';
              const isWarning = insight?.data?.risk_level === 'Warning';
              const isPowerSaving = room.light_level === 0 && room.occupancy === 0;

              return (
                <div key={idx} className={`p-5 rounded-xl border transition-all duration-500 ${
                  isCritical ? 'bg-rose-950/40 border-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.2)]' :
                  isWarning ? 'bg-amber-950/20 border-amber-900/50' :
                  isPowerSaving ? 'bg-[#050B14] border-emerald-900/40 shadow-inner' :
                  'bg-slate-900/50 border-slate-800'
                }`}>
                  <div className="flex justify-between items-start mb-3">
                    <h3 className={`text-lg font-medium ${isCritical ? 'text-rose-400 font-bold' : 'text-white'}`}>
                      {room.id}
                    </h3>
                    <button 
                      onClick={() => evaluateRoomWithAI(room.id)}
                      disabled={insight?.loading}
                      className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 rounded-md text-xs font-semibold border border-indigo-500/20 transition-all disabled:opacity-50"
                    >
                      <BrainCircuit className="w-3 h-3" />
                      {insight?.loading ? 'Analyzing...' : 'AI Evaluate'}
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm text-slate-400 mb-3 border-b border-slate-800 pb-3">
                    <div className="flex flex-col gap-3 justify-center">
                      <span className="flex items-center gap-2">🌡️ Temp: {room.temp}°C</span>
                      <span className={`flex items-center gap-2 ${isPowerSaving ? 'text-emerald-500 font-medium' : ''}`}>
                        {isPowerSaving ? <Moon className="w-4 h-4 animate-pulse" /> : '💡'} Light: {room.light_level}%
                        {isPowerSaving && <span className="ml-1 px-2 py-0.5 bg-emerald-900/30 text-emerald-400 text-[10px] rounded-full border border-emerald-500/20 uppercase tracking-wider">Eco-Mode</span>}
                      </span>
                      <span className="flex items-center gap-2">🏃 Motion: {room.motion ? 'Detected' : 'None'}</span>
                    </div>
                    
                    {/* The Autonomous Academic Ledger (Network Proximity) */}
                    <div className="flex flex-col gap-1 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                      <div className="flex items-center justify-between text-emerald-400 font-medium mb-1">
                        <div className="flex items-center gap-2">
                          <Wifi className="w-4 h-4" /> 
                          <span>Network Ledger</span>
                        </div>
                        <span className="bg-emerald-500/20 px-2 py-0.5 rounded text-xs">{room.occupancy} Active</span>
                      </div>
                      
                      {room.occupancy > 0 ? (
                        <div className="text-[11px] text-slate-400 font-mono mt-1 overflow-hidden h-14 space-y-1">
                           {room.macs.slice(0, 3).map((mac, i) => (
                             <div key={mac} className="flex justify-between items-center bg-slate-900/50 px-2 py-0.5 rounded animate-in fade-in slide-in-from-right-4 duration-300">
                               <span>{mac}</span>
                               <span className="text-emerald-500/70 text-[10px] flex items-center gap-1"><LogIn className="w-3 h-3"/> Present</span>
                             </div>
                           ))}
                           {room.occupancy > 3 && <div className="text-slate-500 italic mt-1 text-center text-[10px]">...and {room.occupancy - 3} more connected</div>}
                        </div>
                      ) : (
                        <div className="text-[11px] text-slate-500 mt-2 italic text-center flex flex-col items-center gap-1">
                          <LogOut className="w-4 h-4 text-slate-600 mb-1" />
                          No devices detected on network
                        </div>
                      )}
                    </div>
                  </div>

                  {/* AI Output Box */}
                  {insight?.data && (
                    <div className={`text-sm p-3 rounded border ${
                      isCritical ? 'bg-rose-950/60 border-rose-900 text-rose-200' :
                      isWarning ? 'bg-amber-950/40 border-amber-900/50 text-amber-200' :
                      'bg-emerald-950/20 border-emerald-900/50 text-emerald-300'
                    }`}>
                      <strong className="block mb-1">Risk: {insight.data.risk_level}</strong>
                      <span className="block mb-1 opacity-90">{insight.data.reason}</span>
                      <span className="block font-medium mt-2 pt-2 border-t border-current/20">
                        Action: {insight.data.recommendation}
                      </span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* RIGHT PANEL: AI Chat */}
      <div className="w-1/2 flex flex-col bg-slate-900">
        <div className="p-6 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-semibold text-white">Ask AI Assistant</h2>
          </div>
          
          {/* NEW: Voice & Logging Controls */}
          <div className="flex gap-2">
            <button 
              onClick={() => setIsMuted(!isMuted)}
              className={`p-2 rounded-lg border transition-colors ${isMuted ? 'bg-rose-500/10 border-rose-500/20 text-rose-400 hover:bg-rose-500/20' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'}`}
              title={isMuted ? "Unmute Assistant" : "Mute Assistant"}
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
            <button 
              onClick={downloadLogs}
              className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 hover:bg-indigo-500/20 transition-colors"
              title="Download Conversation Logs"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[80%] p-4 rounded-2xl ${
                msg.role === 'user' ? 'bg-emerald-600 text-white rounded-br-none' : 
                'bg-slate-800 text-slate-200 rounded-bl-none'
              }`}>
                <div className="flex justify-between items-start mb-1 gap-4">
                  <span className="text-[10px] opacity-60 font-mono">{msg.timestamp}</span>
                </div>
                <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                {msg.source && (
                  <p className="text-xs text-emerald-400 mt-2 pt-2 border-t border-slate-700/50">
                    Source: {msg.source}
                  </p>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex items-start">
              <div className="bg-slate-800 text-slate-400 p-4 rounded-2xl rounded-bl-none animate-pulse">
                Analyzing campus data...
              </div>
            </div>
          )}
        </div>

        <div className="p-6 bg-slate-950/50 border-t border-slate-800">
          <form onSubmit={handleSendMessage} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about rules, timetables, or alerts..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-5 py-4 focus:outline-none focus:border-emerald-500 text-white placeholder-slate-500 transition-colors"
            />
            <button 
              type="submit" 
              disabled={loading || !input.trim()}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-700 disabled:text-slate-500 text-slate-950 px-6 rounded-xl font-medium transition-colors flex items-center justify-center"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>

    </div>
  );
}