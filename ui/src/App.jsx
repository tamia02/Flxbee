import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  LayoutDashboard,
  Users,
  Play,
  Video,
  Send,
  Settings,
  Globe,
  ShieldCheck,
  Activity,
  PlusCircle,
  ExternalLink,
  ChevronRight,
  MoreVertical,
  CheckCircle2,
  Clock,
  AlertCircle
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const API_BASE = "http://localhost:8000";

const App = () => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("leads");
  const [systemStatus, setSystemStatus] = useState({ ai: "Online", whatsapp: "Connected", ffmpeg: "Ready" });

  useEffect(() => {
    fetchLeads();
  }, []);

  const fetchLeads = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/leads`);
      setLeads(resp.data);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch leads", err);
    }
  };

  const handleAction = async (index, action) => {
    setLeads(prev => prev.map((l, i) => i === index ? { ...l, status: `In Progress (${action})...` } : l));
    try {
      const endpoint = action === 'build' ? 'generate' : action === 'record' ? 'record' : 'send';
      const resp = await axios.post(`${API_BASE}/${endpoint}/${index}`);
      if (resp.data.status === 'success') {
        fetchLeads();
      } else {
        alert(`Error: ${resp.data.message}`);
      }
    } catch (err) {
      alert(`Action failed: ${err.message}`);
      fetchLeads();
    }
  };

  return (
    <div className="flex h-screen bg-[#0e0e0f] text-[#ffffff] font-inter selection:bg-[#00f0ff] selection:text-[#000000]">
      {/* Sidebar */}
      <div className="w-64 bg-[#131314] border-r border-[#ffffff10] flex flex-col p-6">
        <div className="flex items-center gap-3 mb-10 px-2">
          <div className="w-8 h-8 bg-gradient-to-br from-[#00f0ff] to-[#7000ff] rounded-lg shadow-[0_0_15px_rgba(0,240,255,0.3)]"></div>
          <span className="text-xl font-outfit font-bold tracking-tight">Flxbee</span>
        </div>

        <nav className="flex-1 space-y-2">
          {[
            { id: "leads", icon: LayoutDashboard, label: "Dashboard" },
            { id: "all-leads", icon: Users, label: "Leads" },
            { id: "automation", icon: Activity, label: "Automation" },
            { id: "settings", icon: Settings, label: "Settings" }
          ].map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 ${activeTab === item.id ? 'bg-[#1a191b] border border-[#ffffff10] shadow-sm text-[#00f0ff]' : 'text-[#adaaab] hover:bg-[#1a191b] hover:text-[#ffffff]'}`}
            >
              <item.icon size={20} />
              <span className="font-medium">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="mt-auto p-4 bg-[#1a191b] rounded-2xl border border-[#ffffff05]">
          <div className="text-xs text-[#adaaab] uppercase tracking-widest mb-3 font-bold">System Status</div>
          <div className="space-y-2">
            {Object.entries(systemStatus).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-xs capitalize text-[#adaaab]">{key}</span>
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 bg-[#00f0ff] rounded-full shadow-[0_0_5px_#00f0ff]"></div>
                  <span className="text-xs font-mono">{value}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-10 bg-gradient-to-br from-[#0e0e0f] via-[#0e0e0f] to-[#1a191b]">
        {/* Header */}
        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="text-4xl font-outfit font-bold mb-2 tracking-tight">Automation Hub</h1>
            <p className="text-[#adaaab] text-lg">Orchestrating your sales pipeline in real-time.</p>
          </div>
          <button className="bg-gradient-to-r from-[#00f0ff] to-[#7000ff] text-[#000000] font-bold px-6 py-3 rounded-xl shadow-[0_0_25px_rgba(0,240,255,0.2)] hover:scale-105 active:scale-95 transition-all flex items-center gap-2">
            <PlusCircle size={20} />
            Run Master Automation
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-6 mb-12">
          {[
            { label: "Total Leads", value: leads.length, icon: Users, color: "#00f0ff" },
            { label: "Sites Generated", value: leads.filter(l => l.html_file).length, icon: Globe, color: "#aaffdc" },
            { label: "Videos Recorded", value: "0", icon: Video, color: "#ac89ff" },
            { label: "Outreach Sent", value: "0", icon: Send, color: "#ff716c" }
          ].map((stat, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-[#1a191b] p-6 rounded-3xl border border-[#ffffff05] relative overflow-hidden group hover:border-[#ffffff15] transition-all"
            >
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-all">
                <stat.icon size={64} style={{ color: stat.color }} />
              </div>
              <div className="mb-4 text-[#adaaab] font-medium tracking-wide uppercase text-xs">{stat.label}</div>
              <div className="text-4xl font-outfit font-bold">{stat.value}</div>
              <div className="mt-4 flex items-center gap-1.5 text-xs text-[#00f0ff]">
                <Activity size={12} />
                <span>Live Data</span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Lead Table */}
        <div className="bg-[#1a191b] rounded-3xl border border-[#ffffff05] shadow-2xl overflow-hidden backdrop-blur-3xl">
          <div className="p-8 border-b border-[#ffffff05] flex items-center justify-between bg-[#ffffff02]">
            <h2 className="text-xl font-bold font-outfit">Lead Management</h2>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-[#0e0e0f] rounded-lg border border-[#ffffff05] text-xs">
                <div className="w-1.5 h-1.5 bg-[#00f0ff] rounded-full"></div>
                Active
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[#ffffff05] bg-[#ffffff01]">
                  <th className="px-8 py-5 text-xs uppercase tracking-widest text-[#adaaab] font-bold">Business Name</th>
                  <th className="px-8 py-5 text-xs uppercase tracking-widest text-[#adaaab] font-bold">Phone</th>
                  <th className="px-8 py-5 text-xs uppercase tracking-widest text-[#adaaab] font-bold">Status</th>
                  <th className="px-8 py-5 text-xs uppercase tracking-widest text-[#adaaab] font-bold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ffffff05]">
                {leads.map((lead, idx) => (
                  <motion.tr
                    key={idx}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="hover:bg-[#ffffff02] transition-colors group"
                  >
                    <td className="px-8 py-6 font-medium">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-[#2c2c2d] flex items-center justify-center text-xs font-bold text-[#00f0ff]">
                          {lead.name[0]}
                        </div>
                        {lead.name}
                      </div>
                    </td>
                    <td className="px-8 py-6 text-[#adaaab] font-mono text-sm leading-relaxed tracking-wider">+{lead.phone}</td>
                    <td className="px-8 py-6">
                      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold ${lead.html_file ? 'bg-[#00fdc115] text-[#00fdc1]' : 'bg-[#ffffff05] text-[#adaaab]'}`}>
                        {lead.html_file ? <CheckCircle2 size={14} /> : <Clock size={14} />}
                        {lead.html_file ? "Website Generated" : "Pending"}
                      </div>
                    </td>
                    <td className="px-8 py-6">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleAction(idx, 'build')}
                          className="p-2.5 rounded-lg bg-[#ffffff05] hover:bg-[#00f0ff20] hover:text-[#00f0ff] transition-all cursor-pointer"
                          title="Generate Website"
                        >
                          <Globe size={18} />
                        </button>
                        <button
                          onClick={() => handleAction(idx, 'record')}
                          className="p-2.5 rounded-lg bg-[#ffffff05] hover:bg-[#ac89ff20] hover:text-[#ac89ff] transition-all cursor-pointer"
                          title="Record Video"
                        >
                          <Video size={18} />
                        </button>
                        <button
                          onClick={() => handleAction(idx, 'send')}
                          className="p-2.5 rounded-lg bg-[#ffffff05] hover:bg-[#ff716c20] hover:text-[#ff716c] transition-all cursor-pointer"
                          title="Send WhatsApp"
                        >
                          <Send size={18} />
                        </button>
                        <button className="p-2.5 rounded-lg bg-[#ffffff05] text-[#adaaab] hover:text-white transition-all">
                          <MoreVertical size={18} />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Global Progress Bar */}
        <div className="fixed bottom-0 right-0 left-64 h-1 bg-[#1a191b] overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: "92%" }}
            className="h-full bg-gradient-to-r from-[#00f0ff] to-[#7000ff] shadow-[0_0_10px_#00f0ff]"
          ></motion.div>
        </div>
      </div>
    </div>
  );
};

export default App;
