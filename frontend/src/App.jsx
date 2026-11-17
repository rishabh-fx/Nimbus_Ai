
import { useEffect, useState } from "react";
import axios from "axios";
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Database,
  RefreshCw,
  Send,
  Activity,
  TrendingUp,
  Users,
  IndianRupee,
  Menu,
  Bot,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import "./App.css";

const API = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function App() {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [scorecard, setScorecard] = useState(null);
  const [health, setHealth] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [changelog, setChangelog] = useState(null);

  const loadDashboard = async () => {
    setLoading(true);
    setError("");

    try {
      const [healthRes, scoreRes] = await Promise.all([
        axios.get(`${API}/health`),
        axios.get(`${API}/scorecard`),
      ]);

      setHealth(["ok", "healthy"].includes(healthRes.data?.status));
      setScorecard(scoreRes.data?.data ?? scoreRes.data);
    } catch (err) {
      setHealth(false);
      setError(
        err.response?.data?.detail ||
        "Cannot connect to the backend. Start the FastAPI server on port 8000."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const askQuestion = async (event) => {
    event.preventDefault();
    if (!question.trim() || chatLoading) return;

    const userQuestion = question.trim();
    setMessages((old) => [...old, { role: "user", text: userQuestion }]);
    setQuestion("");
    setChatLoading(true);

    try {
      const response = await axios.post(`${API}/ask`, {
        question: userQuestion,
      });

      const result = response.data?.data ?? response.data;
      setMessages((old) => [
        ...old,
        {
          role: "assistant",
          text:
            typeof result === "string"
              ? result
              : result.answer || result.response || JSON.stringify(result, null, 2),
          sources: result.sources || [],
        },
      ]);
    } catch (err) {
      setMessages((old) => [
        ...old,
        {
          role: "assistant",
          text: err.response?.data?.detail || "Unable to get an answer. Please check the backend.",
          sources: [],
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const loadReport = async () => {
    try {
      const response = await axios.post(`${API}/report`);
      setReport(response.data?.data ?? response.data);
    } catch (err) {
      setReport({ error: err.response?.data?.detail || "Report service is unavailable." });
    }
  };

  const loadChangelog = async () => {
    try {
      const response = await axios.get(`${API}/changelog`);
      setChangelog(response.data?.data ?? response.data);
    } catch (err) {
      setChangelog({ error: err.response?.data?.detail || "Changelog service is unavailable." });
    }
  };

  const navItems = [
    { name: "Dashboard", icon: LayoutDashboard },
    { name: "AI Assistant", icon: MessageSquare },
    { name: "Weekly Report", icon: FileText },
    { name: "Data Audit", icon: Database },
  ];

  const data = Array.isArray(scorecard)
    ? scorecard
    : scorecard?.rows || scorecard?.initiatives || scorecard?.data || [];

  const kpis = scorecard?.summary || scorecard?.kpis || scorecard || {};

  const metricCards = [
    { label: "AI Adoption", value: kpis.adoption, icon: Users, suffix: "%" },
    { label: "Weekly Active Users", value: kpis.latest_wau ?? kpis.wau, icon: Activity, suffix: "" },
    { label: "ROI", value: kpis.roi, icon: TrendingUp, suffix: "%" },
    { label: "Monthly Benefit", value: kpis.average_monthly_benefit, icon: IndianRupee, suffix: "" },
  ];

  const displayValue = (value, suffix = "") => {
    if (value === null || value === undefined || typeof value === "object") return "—";
    if (typeof value === "number") return `${Number(value.toFixed(2))}${suffix}`;
    return `${value}${suffix}`;
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><Bot size={25} /></div>
          <div><h2>Nimbus AI</h2><span>VALUE INTELLIGENCE</span></div>
        </div>

        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {navItems.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={`nav-item ${activeTab === name ? "active" : ""}`}
              onClick={() => {
                setActiveTab(name);
                if (name === "Weekly Report" && !report) loadReport();
                if (name === "Data Audit" && !changelog) loadChangelog();
              }}
            >
              <Icon size={19} /> <span>{name}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className={`status-dot ${health ? "online" : ""}`}></span>
            <span>{health ? "Backend connected" : "Backend disconnected"}</span>
          </div>
          <p>Enterprise AI Platform<br />Hackathon Edition</p>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="breadcrumb">NIMBUS AI / WORKSPACE</div>
            <h1>{activeTab}</h1>
          </div>
          <div className="topbar-right">
            <span className="live-indicator"><span></span> LIVE SYSTEM</span>
            <button className="icon-button" onClick={loadDashboard} title="Refresh">
              <RefreshCw size={18} />
            </button>
            <div className="avatar">NA</div>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {activeTab === "Dashboard" && (
          <>
            <section className="welcome-section">
              <div>
                <p className="eyebrow">EXECUTIVE OVERVIEW</p>
                <h2>AI Initiative Performance</h2>
                <p>Monitor adoption, financial impact, and enterprise AI value in one place.</p>
              </div>
              <button className="refresh-button" onClick={loadDashboard}>
                <RefreshCw size={16} /> Refresh data
              </button>
            </section>

            <section className="kpi-grid">
              {metricCards.map(({ label, value, icon: Icon, suffix }) => (
                <div className="kpi-card" key={label}>
                  <div className="kpi-top">
                    <span>{label}</span>
                    <div className="kpi-icon"><Icon size={19} /></div>
                  </div>
                  <h3>{loading ? "..." : displayValue(value, suffix)}</h3>
                  <p>Based on available scorecard data</p>
                </div>
              ))}
            </section>

            <section className="content-grid">
              <div className="panel chart-panel">
                <div className="panel-heading">
                  <div><h3>Initiative Performance</h3><p>Available scorecard records</p></div>
                  <span className="panel-tag">OVERVIEW</span>
                </div>
                {data.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={data}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="initiative" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="adoption" fill="#6558e8" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="empty-state">
                    {loading ? "Loading scorecard..." : "Initiative-level chart data will appear when available."}
                  </div>
                )}
              </div>

              <div className="panel status-panel">
                <div className="panel-heading">
                  <div><h3>System Health</h3><p>Backend connection status</p></div>
                </div>
                <div className="health-row">
                  {health ? <CheckCircle2 color="#16a36a" size={22} /> : <AlertCircle color="#d97706" size={22} />}
                  <div><strong>{health ? "API Operational" : "API Not Connected"}</strong><p>{health ? "FastAPI is responding." : "Check that the backend server is running."}</p></div>
                </div>
                <div className="health-row">
                  <Database color="#6558e8" size={22} />
                  <div><strong>Scorecard Service</strong><p>{scorecard ? "Response received" : "Waiting for scorecard data"}</p></div>
                </div>
                <div className="status-note">Metrics are fetched from the backend. Missing values are shown as unavailable.</div>
              </div>
            </section>
          </>
        )}

        {activeTab === "AI Assistant" && (
          <section className="panel assistant-panel">
            <div className="panel-heading">
              <div><h3><Bot size={21} /> Nimbus AI Assistant</h3><p>Ask questions about enterprise AI initiatives and their value.</p></div>
              <span className="panel-tag">RAG POWERED</span>
            </div>
            <div className="chat-window">
              {messages.length === 0 && (
                <div className="chat-welcome">
                  <div className="chat-bot-icon"><Bot size={30} /></div>
                  <h3>How can I help you today?</h3>
                  <p>Ask about ROI, adoption, initiative risks, or charter documents.</p>
                  <div className="suggestions">
                    {["Which initiatives are at risk?", "Explain the ROI of our AI initiatives.", "What does the charter say about expected benefits?"].map((q) => (
                      <button key={q} onClick={() => setQuestion(q)}>{q}</button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((message, index) => (
                <div className={`message ${message.role}`} key={index}>
                  <div className="message-label">{message.role === "user" ? "YOU" : "NIMBUS AI"}</div>
                  <div className="message-text">{message.text}</div>
                  {message.sources?.length > 0 && (
                    <div className="sources"><strong>Sources</strong>{message.sources.map((source, i) => <span key={i}>{typeof source === "string" ? source : source.filename || source.source || JSON.stringify(source)}</span>)}</div>
                  )}
                </div>
              ))}
              {chatLoading && <div className="message assistant">Nimbus AI is thinking...</div>}
            </div>
            <form className="chat-input" onSubmit={askQuestion}>
              <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask Nimbus AI a question..." />
              <button type="submit" disabled={chatLoading || !question.trim()}><Send size={18} /> Send</button>
            </form>
          </section>
        )}

        {activeTab === "Weekly Report" && (
          <section className="panel report-panel">
            <div className="panel-heading"><div><h3>Weekly Executive Report</h3><p>Initiative risks and value performance summary</p></div><button className="refresh-button" onClick={loadReport}><RefreshCw size={15} /> Generate report</button></div>
            <pre>{report ? (report.markdown || report.error || JSON.stringify(report, null, 2)) : "Click Generate report."}</pre>
          </section>
        )}

        {activeTab === "Data Audit" && (
          <section className="panel report-panel">
            <div className="panel-heading"><div><h3>Data Cleaning & Audit Trail</h3><p>Review data quality changes and corrections</p></div><button className="refresh-button" onClick={loadChangelog}><RefreshCw size={15} /> Refresh</button></div>
            <pre>{changelog ? (changelog.markdown || changelog.error || JSON.stringify(changelog, null, 2)) : "Click Refresh to load the change log."}</pre>
          </section>
        )}

        <footer>© 2026 Nimbus AI <span>Enterprise RAG Value Intelligence Assistant</span></footer>
      </main>
    </div>
  );
}

export default App;
