import React, { useState, useEffect } from 'react';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('home'); // 'home', 'matcher', 'providers', 'chat'
  const [skillsInput, setSkillsInput] = useState('Python, Machine Learning, Flask');
  const [budgetInput, setBudgetInput] = useState(3000);
  const [rankedProviders, setRankedProviders] = useState([]);
  const [dsaMeta, setDsaMeta] = useState(null);
  const [loading, setLoading] = useState(false);

  // Fetch initial providers
  useEffect(() => {
    runDSAMatch();
  }, []);

  const runDSAMatch = async () => {
    setLoading(true);
    try {
      const skillsArray = skillsInput.split(',').map(s => s.trim()).filter(Boolean);
      const res = await fetch('http://127.0.0.1:5000/api/matching/find-matches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skills: skillsArray,
          budget: Number(budgetInput),
          strict_budget: false
        })
      });
      const data = await res.json();
      if (data.success) {
        setRankedProviders(data.results);
        setDsaMeta(data.dsa_metadata);
      }
    } catch (err) {
      console.warn("API Error, make sure Flask is running on port 5000:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-root">
      {/* NAVIGATION */}
      <header className="navbar">
        <div className="container nav-inner">
          <a href="#" className="brand" onClick={() => setActiveTab('home')}>
            <div className="brand-icon">E</div>
            <div className="brand-name">edu<span>match</span></div>
          </a>

          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <button
              onClick={() => setActiveTab('home')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, color: activeTab === 'home' ? '#7657FF' : '#737D90' }}
            >Home</button>
            <button
              onClick={() => setActiveTab('matcher')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, color: activeTab === 'matcher' ? '#7657FF' : '#737D90' }}
            >DSA Match Engine</button>
            <button
              onClick={() => setActiveTab('providers')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, color: activeTab === 'providers' ? '#7657FF' : '#737D90' }}
            >All Providers</button>
          </div>

          <div className="nav-actions">
            <a href="http://127.0.0.1:5000/student/login.html" className="btn btn-outline">Student Portal</a>
            <a href="http://127.0.0.1:5000/provider/login.html" className="btn btn-primary">Provider Portal</a>
          </div>
        </div>
      </header>

      {/* TAB: HOME */}
      {activeTab === 'home' && (
        <>
          <section className="hero">
            <div className="container">
              <div className="hero-label">
                <span className="hero-dot"></span> Project Collaboration & Matching Platform
              </div>
              <h1>Ideas deserve the <span>right team.</span></h1>
              <p className="hero-description">
                EduMatch connects students with verified project mentors and developers
                powered by our intelligent Data Structures & Algorithms matching engine.
              </p>
              <div style={{ marginTop: '30px', display: 'flex', gap: '15px' }}>
                <button className="btn btn-primary" onClick={() => setActiveTab('matcher')}>
                  Try DSA Matching Engine ⚡
                </button>
                <a href="http://127.0.0.1:5000/student/register.html" className="btn btn-outline" style={{ background: 'transparent', color: '#fff', borderColor: '#4B5563' }}>
                  Register as Student
                </a>
              </div>
            </div>
          </section>

          <main className="container">
            <div className="section-title">
              <h2>Select Your Portal</h2>
              <p style={{ color: '#737D90', marginTop: '8px' }}>Direct access for students, developers, and administrators</p>
            </div>

            <div className="portal-grid">
              <div className="portal-card">
                <div style={{ fontSize: '24px', fontWeight: 800, color: '#7657FF' }}>01</div>
                <h3 style={{ margin: '12px 0 8px' }}>Student Workspace</h3>
                <p style={{ color: '#737D90', fontSize: '14px', minHeight: '60px' }}>
                  Post project requirements, discover top-matched mentors, and collaborate persistently.
                </p>
                <a href="http://127.0.0.1:5000/student/login.html" className="btn btn-outline" style={{ width: '100%', marginTop: '16px' }}>
                  Open Student Portal →
                </a>
              </div>

              <div className="portal-card">
                <div style={{ fontSize: '24px', fontWeight: 800, color: '#24845A' }}>02</div>
                <h3 style={{ margin: '12px 0 8px' }}>Project Provider</h3>
                <p style={{ color: '#737D90', fontSize: '14px', minHeight: '60px' }}>
                  Showcase Python, ML, and Web skills, accept project requests, and manage earnings.
                </p>
                <a href="http://127.0.0.1:5000/provider/login.html" className="btn btn-outline" style={{ width: '100%', marginTop: '16px' }}>
                  Open Provider Portal →
                </a>
              </div>

              <div className="portal-card">
                <div style={{ fontSize: '24px', fontWeight: 800, color: '#B96B29' }}>03</div>
                <h3 style={{ margin: '12px 0 8px' }}>Admin Dashboard</h3>
                <p style={{ color: '#737D90', fontSize: '14px', minHeight: '60px' }}>
                  Monitor platform metrics, manage user roles, and ensure marketplace safety.
                </p>
                <a href="http://127.0.0.1:5000/admin/login.html" className="btn btn-outline" style={{ width: '100%', marginTop: '16px' }}>
                  Open Admin Portal →
                </a>
              </div>
            </div>
          </main>
        </>
      )}

      {/* TAB: DSA MATCHING ENGINE */}
      {(activeTab === 'matcher' || activeTab === 'providers') && (
        <main className="container" style={{ padding: '40px 0' }}>
          <div className="matcher-box">
            <h2 style={{ fontSize: '26px', color: '#111827', marginBottom: '8px' }}>
              ⚡ DSA Matching & Ranking Simulator
            </h2>
            <p style={{ color: '#6B7280', fontSize: '14px', marginBottom: '24px' }}>
              Experience the core Data Structures & Algorithms engine in real-time. Modifying the skills or budget triggers Set-Intersection matching and Merge-Sort ranking.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: '16px', alignItems: 'flex-end' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, marginBottom: '6px' }}>
                  Required Skills (Comma-separated)
                </label>
                <input
                  type="text"
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1px solid #E5E8F0', font: 'inherit' }}
                  placeholder="e.g. Python, Machine Learning, Flask"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, marginBottom: '6px' }}>
                  Maximum Budget (₹ INR)
                </label>
                <input
                  type="number"
                  value={budgetInput}
                  onChange={(e) => setBudgetInput(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1px solid #E5E8F0', font: 'inherit' }}
                />
              </div>

              <button className="btn btn-primary" onClick={runDSAMatch} disabled={loading}>
                {loading ? 'Evaluating...' : 'Run DSA Match'}
              </button>
            </div>

            {dsaMeta && (
              <div style={{ marginTop: '20px', padding: '16px', background: '#F8FAFC', borderRadius: '10px', fontSize: '13px', color: '#475569' }}>
                <strong>Algorithm:</strong> {dsaMeta.algorithm} | <strong>Complexity:</strong> {dsaMeta.time_complexity} | <strong>Formula:</strong> {dsaMeta.scoring_formula}
              </div>
            )}
          </div>

          <h3 style={{ margin: '30px 0 16px', color: '#111827' }}>
            Ranked Recommendations ({rankedProviders.length} Providers Evaluated)
          </h3>

          <div className="providers-list">
            {rankedProviders.map((p, idx) => (
              <div key={p.id || idx} className="provider-card">
                <div className="provider-header">
                  <div>
                    <h3 style={{ color: '#111827', fontSize: '18px' }}>{p.name}</h3>
                    <p style={{ color: '#6B7280', fontSize: '13px' }}>{p.title || p.role}</p>
                  </div>
                  <div className="match-badge">
                    ⚡ {p.match_score || 85}% DSA Match
                  </div>
                </div>

                <p style={{ color: '#4B5563', fontSize: '14px' }}>{p.description}</p>

                <div className="skills-tags">
                  {(p.skills || []).map((s, i) => (
                    <span
                      key={i}
                      className="skill-tag"
                      style={(p.matching_skills || []).includes(s.toLowerCase()) ? { background: '#DCFCE7', color: '#15803D' } : {}}
                    >
                      {s}
                    </span>
                  ))}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', borderTop: '1px solid #E5E8F0', paddingTop: '14px' }}>
                  <div style={{ fontSize: '13px', color: '#6B7280' }}>
                    Starting: <strong style={{ color: '#111827', fontSize: '16px' }}>₹{p.starting_price || p.price}</strong> | Projects: <strong>{p.completed_projects || p.projects || 10}</strong> | Rating: <strong>★ {p.rating}</strong>
                  </div>
                  <a
                    href={`http://127.0.0.1:5000/student/chat.html?provider_id=${p.id}&provider_name=${encodeURIComponent(p.name)}`}
                    className="btn btn-primary"
                    style={{ fontSize: '12px', padding: '8px 14px' }}
                  >
                    Connect & Message
                  </a>
                </div>
              </div>
            ))}
          </div>
        </main>
      )}

      {/* FOOTER */}
      <footer style={{ background: '#111827', color: '#9CA3AF', padding: '30px 0', marginTop: '60px' }}>
        <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>© 2026 EduMatch Platform · BCA Artificial Intelligence & Data Science</div>
          <div>Integrated Python Flask + SQLite Backend with React & Vite Support</div>
        </div>
      </footer>
    </div>
  );
}
